"""
Screen capture backends.

`sys.platform` is inspected in exactly one place in this file (`create_backend`).
Callers only see the `grab() -> ndarray | None` contract below and never import
`mss`/`dxcam` directly, so a new platform backend is a new class here plus one
branch in `create_backend` -- nothing else in the package changes.

A backend instance is thread-confined: `open()`/`grab()`/`close()` must all be
called from the same thread (mss cannot share its device-context handles across
threads on Windows, and GPU capture APIs have similar affinity constraints), so
`ScreenAnalyzer` constructs the backend from inside its own capture thread.
"""
import re
import sys
import time

import numpy as np


class ScreenCaptureBackend:
    """Contract every backend implements. Not instantiated directly."""

    name = "base"
    recommended_fps = 15

    def open(self, display_index):
        """Resolve `display_index` (0 = primary) to a capture region and acquire
        whatever OS handles are needed. Must be called from the capture thread."""
        raise NotImplementedError

    def grab(self):
        """Return the latest frame as an (H, W, 4) BGRA uint8 ndarray, or None if
        the backend has nothing new since the last call (not an error)."""
        raise NotImplementedError

    def close(self):
        raise NotImplementedError


class MssBackend(ScreenCaptureBackend):
    """GDI BitBlt via mss. Works everywhere; floored at ~1 DWM composite frame
    (~16.7ms @60Hz) per grab() regardless of region size."""

    name = "mss"
    recommended_fps = 12

    # Capture a centered box rather than the full display: it drops the
    # taskbar/window-chrome pixels that drag a whole-screen average toward
    # gray, and it caps the per-grab cost on large/4K outputs.
    REGION_FRAC = 0.6

    def __init__(self):
        self.sct = None
        self.region = None

    def open(self, display_index):
        import mss

        if display_index < 0:
            raise ValueError(f"display_index must be >= 0, got {display_index}")

        self.sct = mss.mss()
        monitors = self.sct.monitors[1:]  # monitors[0] is the union of all displays

        # mss exposes no "primary" flag, and its enumeration order is NOT
        # guaranteed to put the primary display first (verified: on this
        # machine monitors[1] was a secondary display while the true
        # primary -- per Windows -- was elsewhere in the list). The one
        # invariant Windows does guarantee is that the primary display's
        # origin is always the desktop's (0, 0), so resolve "primary" from
        # geometry instead of trusting a fixed index. Matches DxcamBackend's
        # primary-first ordering so display_index means the same physical
        # display on both backends.
        primaries = [m for m in monitors if m["left"] == 0 and m["top"] == 0]
        non_primaries = [m for m in monitors if m not in primaries]

        if display_index == 0:
            if not primaries:
                raise ValueError("no monitor found at the desktop origin (0, 0); cannot resolve 'primary'")
            mon = primaries[0]
        else:
            idx = display_index - 1
            if idx >= len(non_primaries):
                raise ValueError(
                    f"display_index {display_index} out of range "
                    f"(found 1 primary + {len(non_primaries)} secondary monitor(s))"
                )
            mon = non_primaries[idx]

        w = max(1, int(mon["width"] * self.REGION_FRAC))
        h = max(1, int(mon["height"] * self.REGION_FRAC))
        self.region = {
            "left": mon["left"] + (mon["width"] - w) // 2,
            "top": mon["top"] + (mon["height"] - h) // 2,
            "width": w,
            "height": h,
        }

    def grab(self):
        img = self.sct.grab(self.region)
        return np.array(img)  # BGRA

    def close(self):
        if self.sct is not None:
            self.sct.close()
            self.sct = None


_OUTPUT_INFO_RE = re.compile(r"Device\[(\d+)\]\s+Output\[(\d+)\]:.*?Primary:(True|False)")


def _parse_output_candidates(output_info_text):
    """Parse `dxcam.output_info()` (a human-readable multi-line string) into
    `(device_idx, output_idx, is_primary)` tuples. This is a cheap,
    no-camera-construction enumeration -- used both by the `"auto"`
    backend-selection check and by `DxcamBackend.open()`'s probing below."""
    candidates = []
    for line in output_info_text.splitlines():
        m = _OUTPUT_INFO_RE.search(line)
        if m:
            candidates.append((int(m.group(1)), int(m.group(2)), m.group(3) == "True"))
    return candidates


def _candidate_order(dxcam, display_index):
    """Build an ordered list of `(device_idx, output_idx)` combos to try for
    `display_index` (0-based, 0 = primary display), primary-first for index 0.

    Desktop Duplication enumerates outputs per-adapter. On multi-GPU systems
    (e.g. a hybrid iGPU/dGPU laptop) the same physical monitor can be
    enumerated as an output on more than one adapter, with only one of them
    actually able to produce real (non-black) pixel data -- the other
    returns a black/empty capture because that adapter doesn't own the
    frame buffer. So rather than trusting the first match, this returns
    every plausible combo in priority order and `DxcamBackend.open()` probes
    each until one actually works.
    """
    if display_index < 0:
        raise ValueError(f"display_index must be >= 0, got {display_index}")

    candidates = _parse_output_candidates(dxcam.output_info())
    primaries = [(d, o) for d, o, p in candidates if p]
    non_primaries = [(d, o) for d, o, p in candidates if not p]

    if display_index == 0:
        ordered = primaries + non_primaries
    else:
        idx = display_index - 1
        if idx >= len(non_primaries):
            raise ValueError(
                f"display_index {display_index} out of range "
                f"(found 1 primary + {len(non_primaries)} secondary output(s))"
            )
        target = non_primaries[idx]
        ordered = [target] + [c for c in (non_primaries + primaries) if c != target]

    seen = set()
    result = []
    for c in ordered:
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result


def _is_near_black(frame_bgra, mean_threshold):
    sample = frame_bgra[::20, ::20, :3]
    return float(sample.mean()) < mean_threshold


def _dxcam_usable():
    """Cheap, display-index-independent check used only by `"auto"`: can
    dxcam be imported, and does it see at least one DXGI output at all? The
    real per-display-index probing (including the hybrid-GPU adapter/output
    search) happens later, inside `DxcamBackend.open()`."""
    try:
        import dxcam
    except Exception:
        return False
    try:
        return bool(_parse_output_candidates(dxcam.output_info()))
    except Exception:
        return False


class DxcamBackend(ScreenCaptureBackend):
    """Windows Desktop Duplication API via dxcam. Much lower per-grab
    overhead than GDI (mss): grab() polls a duplication surface directly
    instead of doing a BitBlt, so recommended_fps can track the display
    refresh rate instead of being floored by DWM composition.

    `output_color="BGRA"` is required: it's the only color mode dxcam can
    serve without importing cv2 (dxcam's default color-conversion path
    imports cv2 and would crash if opencv isn't installed -- and it isn't,
    deliberately, since this project has no other use for it).

    Known, unavoidable limitation worth stating rather than working around:
    DRM-protected video (Netflix, Prime Video, Disney+ in a browser)
    captures as black under Desktop Duplication, same as under GDI -- this
    is an OS-level content-protection feature, not a bug here. This backend
    does not attempt to detect or route around it in grab(); the downstream
    color extractor is expected to treat a near-uniformly-black frame as
    low-confidence.
    """

    name = "dxcam"
    recommended_fps = 60

    # Capture a centered box rather than the full display, matching
    # MssBackend (see its REGION_FRAC comment).
    REGION_FRAC = 0.6

    # Bounded probing (open()) and recovery (grab()) knobs.
    _PROBE_GRAB_ATTEMPTS = 10
    _PROBE_GRAB_BUDGET_S = 0.2
    _PROBE_BLACK_MEAN_THRESHOLD = 6.0
    _RECOVERY_MAX_ATTEMPTS = 5
    _RECOVERY_BASE_DELAY_S = 0.1
    _RECOVERY_MAX_DELAY_S = 2.0

    def __init__(self):
        self._dxcam = None  # the imported `dxcam` module, set in open()
        self.camera = None
        self.region = None
        self._device_idx = None
        self._output_idx = None

    def open(self, display_index):
        import dxcam

        self._dxcam = dxcam
        candidates = _candidate_order(dxcam, display_index)
        if not candidates:
            raise ValueError(
                f"display_index {display_index}: no usable DXGI output found "
                f"(dxcam enumerated no adapters/outputs)"
            )

        tried = []
        for device_idx, output_idx in candidates:
            camera = self._try_candidate(device_idx, output_idx)
            if camera is not None:
                self.camera = camera
                self._device_idx = device_idx
                self._output_idx = output_idx
                self._set_region(camera)
                return
            tried.append((device_idx, output_idx))

        raise RuntimeError(
            f"display_index {display_index}: none of the candidate DXGI "
            f"outputs {tried} produced a usable (non-black) frame within "
            f"budget. This can happen on hybrid-GPU laptops where the "
            f"adapter doesn't own the desktop, or transiently during a "
            f"display mode change."
        )

    def _try_candidate(self, device_idx, output_idx):
        """Construct a camera for one (device_idx, output_idx) and confirm
        it actually produces a real frame, within a short budget. Returns
        the camera on success, or None (releasing it first) on failure --
        never raises, so open()'s probing loop can just move to the next
        candidate."""
        dxcam = self._dxcam
        try:
            camera = dxcam.create(device_idx=device_idx, output_idx=output_idx, output_color="BGRA")
        except Exception:
            return None
        if camera is None:
            return None

        frame = None
        deadline = time.monotonic() + self._PROBE_GRAB_BUDGET_S
        for _ in range(self._PROBE_GRAB_ATTEMPTS):
            try:
                frame = camera.grab()
            except Exception:
                frame = None
            if frame is not None:
                break
            if time.monotonic() >= deadline:
                break
            time.sleep(0.02)

        if frame is None or _is_near_black(frame, self._PROBE_BLACK_MEAN_THRESHOLD):
            try:
                camera.release()
            except Exception:
                pass
            return None
        return camera

    def _set_region(self, camera):
        w = max(1, int(camera.width * self.REGION_FRAC))
        h = max(1, int(camera.height * self.REGION_FRAC))
        left = (camera.width - w) // 2
        top = (camera.height - h) // 2
        self.region = (left, top, left + w, top + h)

    def grab(self):
        try:
            return self.camera.grab(region=self.region)
        except Exception:
            # dxcam's DXGI backend already retries transient DXGI errors
            # (DXGI_ERROR_ACCESS_LOST, DEVICE_REMOVED, session disconnect,
            # etc -- the things that fire on resolution changes, monitor
            # hot-plug, GPU driver TDR, a UAC secure-desktop prompt, Win+L
            # lock/unlock, or a fullscreen-exclusive app taking over)
            # internally, with its own progressive backoff, before ever
            # raising -- see
            # dxcam.core.display_recovery.DisplayRecoveryHandler.handle().
            # So by the time an exception reaches here, the library has
            # already given up (a non-transient DXGI/COM error) or
            # something else broke. Rebuild the camera for the same
            # (device_idx, output_idx) that worked in open(), and give up
            # loudly rather than spin forever -- the caller (ScreenAnalyzer)
            # holds the last-known-good color and retries next cycle.
            self._recover()
            return None

    def _recover(self):
        dxcam = self._dxcam
        try:
            if self.camera is not None:
                self.camera.release()
        except Exception:
            pass
        self.camera = None

        delay = self._RECOVERY_BASE_DELAY_S
        last_exc = None
        for _ in range(self._RECOVERY_MAX_ATTEMPTS):
            time.sleep(delay)
            delay = min(delay * 2, self._RECOVERY_MAX_DELAY_S)
            try:
                camera = dxcam.create(
                    device_idx=self._device_idx,
                    output_idx=self._output_idx,
                    output_color="BGRA",
                )
            except Exception as e:
                last_exc = e
                continue
            if camera is None:
                last_exc = RuntimeError("dxcam.create() returned None during recovery")
                continue
            self.camera = camera
            self._set_region(camera)
            return

        raise RuntimeError(
            f"dxcam: lost the capture device for device_idx={self._device_idx} "
            f"output_idx={self._output_idx} and could not recover after "
            f"{self._RECOVERY_MAX_ATTEMPTS} attempts"
        ) from last_exc

    def close(self):
        if self.camera is not None:
            try:
                self.camera.release()
            except Exception:
                pass
            self.camera = None


def create_backend(name="auto"):
    """Resolve a backend by explicit name, or pick one for the current platform."""
    if name == "mss":
        return MssBackend()
    if name == "dxcam":
        # Explicit request: let failures surface as-is (e.g. dxcam not
        # installed raises ImportError from open()) rather than silently
        # falling back -- the difference between "auto, please fall back"
        # and "I explicitly asked for dxcam" matters for debugging.
        return DxcamBackend()
    if name == "auto":
        if sys.platform == "win32" and _dxcam_usable():
            return DxcamBackend()
        return MssBackend()
    raise ValueError(f"Unknown screen capture backend: {name!r}")
