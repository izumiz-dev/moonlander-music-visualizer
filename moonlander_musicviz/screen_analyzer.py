"""
Screen Color Sync: captures screen content in a background thread and
calculates a dominant-color palette for the music visualizer.

Capture is deliberately off the audio thread's budget. A single mss grab()
costs 40-150ms depending on monitor size, and the caller (main.py) also owns
a sounddevice InputStream with a ~21ms/block read budget -- calling capture
synchronously there starves the audio path, not just delays the color.

Color extraction is two pieces:
  - `extract_screen_color()`: a pure, stateless function that reduces one
    frame to a dominant hue + a confidence score (how much to trust that hue).
  - `HueFilter`: stateful temporal smoothing across frames, biased hard
    toward stability over responsiveness (see its docstring).
"""
import math
import threading
import time

import numpy as np

from . import color_utils
from .screen_backends import create_backend

# --- Extraction tuning constants -------------------------------------------------
_DOWNSAMPLE_TARGET_PX = 260  # long-edge target after downsampling, for cost control
_MIN_VALUE = 24              # pixels darker than this contribute nothing (near-black)
_MIN_CHROMA = 16              # pixels less saturated than this contribute nothing (near-gray)
_HIST_BINS = 32
_LUMA_BINS = 16
_SECOND_PEAK_MIN_BIN_DIST = 5      # ~40 hue-units apart (256/32 * 5 ≈ 40)
_SECOND_PEAK_MIN_MASS_FRAC = 0.25  # must carry >=25% of the primary peak's mass

_window_cache = {}


def _raised_cosine(n):
    """1D Hann-style window: 0 at both edges, 1 at the center. n<=1 -> all-ones."""
    if n <= 1:
        return np.ones(max(n, 1))
    idx = np.arange(n)
    return 0.5 * (1.0 - np.cos(2.0 * np.pi * idx / (n - 1)))


def _center_window(shape):
    """Separable raised-cosine window for `shape` (h, w), cached by shape."""
    cached = _window_cache.get(shape)
    if cached is not None:
        return cached
    h, w = shape
    win = np.outer(_raised_cosine(h), _raised_cosine(w))
    _window_cache[shape] = win
    return win


def _circular_bin_distance(a, b, n_bins):
    d = abs(a - b) % n_bins
    return min(d, n_bins - d)


def _refine_hue(hue, weight, bin_idx, peak_bin, n_bins):
    """
    Chroma-weighted circular mean of the actual pixel hues in `peak_bin` and
    its two circular neighbors, for sub-bin precision beyond the 32-bucket
    histogram's ~8-hue-unit resolution.
    """
    neighbors = {(peak_bin - 1) % n_bins, peak_bin, (peak_bin + 1) % n_bins}
    mask = np.isin(bin_idx, list(neighbors)) & (weight > 0)
    if not np.any(mask):
        return None, 0.0
    w = weight[mask]
    total = float(w.sum())
    if total <= 0.0:
        return None, 0.0
    x, y = color_utils.hue_to_vec(hue[mask])
    mx = float((w * x).sum() / total)
    my = float((w * y).sum() / total)
    return color_utils.vec_to_hue(mx, my), total


def extract_screen_color(frame_bgra):
    """
    Reduce one captured frame to a dominant hue + confidence, pure/stateless.

    Accepts (H, W, 4) or (H, W, 3) uint8 BGR(A) (a 4th alpha channel, if
    present, is ignored). Instead of a whole-frame mean (near-gray, hue angle
    is meaningless noise), this bins pixel hues into a 32-bucket circular
    histogram weighted by how saturated/bright/centered each pixel is, then
    takes the weighted peak.

    Returns a dict:
      hue              -- int 0-255, the dominant hue
      hue2             -- int 0-255 or None, a second dominant hue at least
                           ~40 hue-units from `hue` with >=25% of its mass
      confidence       -- float 0-1, how much to trust `hue`
      chroma_strength  -- float 0-1ish, overall "how colorful is this frame"
      chroma_hist       -- (32,) float ndarray, L1-normalized (probability dist)
      luma_hist         -- (16,) float ndarray, L1-normalized (probability dist)
    """
    img = np.asarray(frame_bgra)[:, :, :3]
    h, w = img.shape[:2]
    long_edge = max(h, w)
    stride = max(1, long_edge // _DOWNSAMPLE_TARGET_PX)
    img = img[::stride, ::stride, :]
    dh, dw = img.shape[:2]

    # uint8 wraparound on cmax-cmin is a silent bug -- go to int16 first.
    b = img[:, :, 0].astype(np.int16)
    g = img[:, :, 1].astype(np.int16)
    r = img[:, :, 2].astype(np.int16)

    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    chroma = cmax - cmin
    value = cmax

    # Hue on the QMK 0-255 wheel (6 sectors of 256/6 ~= 42.67, i.e. region =
    # hue // 43), vectorized. Division-by-zero on chroma==0 pixels is masked
    # out below via `w` anyway, so a dummy safe divisor is fine here.
    safe_chroma = np.where(chroma == 0, 1, chroma).astype(np.float32)
    rf = r.astype(np.float32)
    gf = g.astype(np.float32)
    bf = b.astype(np.float32)
    sector = 256.0 / 6.0
    rc = ((gf - bf) / safe_chroma) % 6.0
    gc = ((bf - rf) / safe_chroma) + 2.0
    bc = ((rf - gf) / safe_chroma) + 4.0
    hue_f = np.where(cmax == r, rc, np.where(cmax == g, gc, bc)) * sector
    hue = np.mod(hue_f, 256.0).astype(np.int32)

    center_window = _center_window((dh, dw))
    chroma_f = chroma.astype(np.float32) / 255.0
    value_f = value.astype(np.float32) / 255.0
    weight = np.power(np.clip(chroma_f, 0.0, 1.0), 1.5) * value_f * center_window
    dead = (cmax < _MIN_VALUE) | (chroma < _MIN_CHROMA)
    weight = np.where(dead, 0.0, weight)

    bin_idx = (hue >> 3).astype(np.int64)  # 256/32 = 8 -> hue // 8
    hist = np.bincount(bin_idx.ravel(), weights=weight.ravel(), minlength=_HIST_BINS)
    hist = hist[:_HIST_BINS]
    smoothed = color_utils.circular_smooth(hist)

    total_weight = float(weight.sum())
    total_pixels = weight.size
    chroma_strength = total_weight / total_pixels if total_pixels else 0.0
    hist_mass = float(smoothed.sum())

    peak_bin = int(np.argmax(smoothed))
    hue_flat = hue.ravel()
    weight_flat = weight.ravel()
    bin_flat = bin_idx.ravel()

    refined_hue, peak_mass = _refine_hue(hue_flat, weight_flat, bin_flat, peak_bin, _HIST_BINS)
    if refined_hue is None:
        refined_hue = int(peak_bin * 8)  # degenerate: no live pixels, fall back to bin center

    peak_share = (peak_mass / hist_mass) if hist_mass > 0 else 0.0
    confidence = color_utils.clip01(chroma_strength / 0.18) * color_utils.clip01(
        (peak_share - 0.25) / 0.45
    )

    # Second-dominant hue: best bin at least _SECOND_PEAK_MIN_BIN_DIST away
    # from the primary with enough mass to be a real second color, not noise.
    hue2 = None
    candidate_bins = [
        i for i in range(_HIST_BINS)
        if _circular_bin_distance(i, peak_bin, _HIST_BINS) >= _SECOND_PEAK_MIN_BIN_DIST
    ]
    if candidate_bins:
        second_bin = max(candidate_bins, key=lambda i: smoothed[i])
        primary_mass = smoothed[peak_bin]
        if primary_mass > 0 and smoothed[second_bin] >= _SECOND_PEAK_MIN_MASS_FRAC * primary_mass:
            refined2, _ = _refine_hue(hue_flat, weight_flat, bin_flat, second_bin, _HIST_BINS)
            hue2 = refined2

    # Coarse luma histogram (independent of hue/chroma) for cut detection.
    luma = (0.299 * rf + 0.587 * gf + 0.114 * bf)
    luma_bin = np.clip((luma / 16.0).astype(np.int64), 0, _LUMA_BINS - 1)
    luma_hist = np.bincount(luma_bin.ravel(), minlength=_LUMA_BINS)[:_LUMA_BINS].astype(np.float64)

    chroma_hist_sum = float(hist.sum())
    chroma_hist_norm = hist / chroma_hist_sum if chroma_hist_sum > 0 else np.zeros(_HIST_BINS)
    luma_hist_sum = float(luma_hist.sum())
    luma_hist_norm = luma_hist / luma_hist_sum if luma_hist_sum > 0 else np.zeros(_LUMA_BINS)

    return {
        "hue": int(refined_hue) % 256,
        "hue2": (int(hue2) % 256) if hue2 is not None else None,
        "confidence": confidence,
        "chroma_strength": chroma_strength,
        "chroma_hist": chroma_hist_norm,
        "luma_hist": luma_hist_norm,
    }


class HueFilter:
    """
    Temporal smoothing of a stream of `extract_screen_color()` outputs into a
    single stable hue, tuned hard toward STABILITY over responsiveness: this
    feeds peripheral-vision hardware where flicker is highly noticeable and a
    little lag is not, and brightness/rhythm are already carried by the audio
    path at 30Hz -- hue only needs to be *correct*, not *fast*.

    A single EMA can't both kill flicker on near-gray frames and snap fast on
    a real scene cut, so state is layered:

      - State is a 2D vector `confidence * hue_to_vec(hue)`, not a scalar hue,
        updated via EMA in vector space. This gets three properties for free:
        a near-gray frame (confidence ~0) can only shrink the vector, never
        rotate it, so flicker on gray frames is structurally impossible, not
        just damped; shrinking-toward-origin holds the angle while the
        magnitude decays, i.e. "hold hue, fade saturation" on a neutral
        screen; and confident frames pull harder than weak ones automatically.
      - The EMA rate adapts between a slow baseline and a fast one based on
        how large + confident the jump is (smoothstep, not a hard threshold,
        so there's no visible stepping).
      - A histogram-distance cut detector snaps the state directly on a hard
        scene change (if the new frame is confident) or collapses it fast
        while preserving angle (if the new frame is dark/neutral -- snapping
        to a meaningless hue would be worse than just fading out).
      - A slew-rate safety net clamps the emitted hue's per-update change as a
        last-resort backstop, so even if extraction/filtering misbehaves the
        worst case is a slow drift, never a strobe.
    """

    TAU_SLOW = 0.4   # seconds, baseline EMA time constant
    TAU_FAST = 0.08  # seconds, EMA time constant on a large confident jump
    JUMP_SMOOTHSTEP_LO = 0.15
    JUMP_SMOOTHSTEP_HI = 0.5
    MIN_MAGNITUDE = 0.02      # below this, |state| is too small to trust atan2
    CUT_HIST_THRESHOLD = 0.55
    CUT_COOLDOWN_S = 0.2
    CUT_CONFIDENT_THRESHOLD = 0.35
    CUT_COLLAPSE_FACTOR = 0.15  # how much magnitude survives a low-confidence cut
    SLEW_MAX_PER_30HZ_FRAME = 3.0  # hue-units; scaled by dt relative to 1/30s

    def __init__(self):
        self._state_x = 0.0
        self._state_y = 0.0
        self._last_emitted_hue = 0
        self._prev_chroma_hist = None
        self._prev_luma_hist = None
        self._cooldown_remaining = 0.0

    def _current_state_hue(self):
        mag = math.hypot(self._state_x, self._state_y)
        if mag < self.MIN_MAGNITUDE:
            return self._last_emitted_hue
        return color_utils.vec_to_hue(self._state_x, self._state_y)

    def update(self, extraction, dt):
        """
        Advance the filter by one frame. `dt` must be measured by the caller
        via time.monotonic() (capture cadence varies by backend) and is
        clamped here to avoid a huge jump after a stall.

        Returns (hue, confidence) -- confidence passed through unchanged from
        the extraction, for the caller to derive saturation/spread from.
        """
        dt = max(0.0, min(dt, 0.1))
        hue = extraction["hue"]
        confidence = extraction["confidence"]
        chroma_hist = extraction["chroma_hist"]
        luma_hist = extraction["luma_hist"]

        self._cooldown_remaining = max(0.0, self._cooldown_remaining - dt)

        is_cut = False
        if self._prev_chroma_hist is not None and self._cooldown_remaining <= 0.0:
            chroma_dist = float(np.abs(chroma_hist - self._prev_chroma_hist).sum())
            luma_dist = float(np.abs(luma_hist - self._prev_luma_hist).sum())
            hist_dist = 0.5 * (chroma_dist + luma_dist)
            if hist_dist > self.CUT_HIST_THRESHOLD:
                is_cut = True
        self._prev_chroma_hist = chroma_hist
        self._prev_luma_hist = luma_hist

        target_x, target_y = color_utils.hue_to_vec(hue)
        target_x *= confidence
        target_y *= confidence

        if is_cut:
            if confidence > self.CUT_CONFIDENT_THRESHOLD:
                self._state_x, self._state_y = target_x, target_y
            else:
                # Cutting to a dark/neutral scene: collapse magnitude fast
                # but keep the angle -- don't snap to a meaningless hue.
                self._state_x *= self.CUT_COLLAPSE_FACTOR
                self._state_y *= self.CUT_COLLAPSE_FACTOR
            self._cooldown_remaining = self.CUT_COOLDOWN_S
        else:
            current_hue = self._current_state_hue()
            jump = abs(color_utils.hue_delta(hue, current_hue)) / 128.0
            t = color_utils.smoothstep(
                jump * confidence, self.JUMP_SMOOTHSTEP_LO, self.JUMP_SMOOTHSTEP_HI
            )
            tau = color_utils.lerp(self.TAU_SLOW, self.TAU_FAST, t)
            k = 1.0 - math.exp(-dt / tau)
            self._state_x += k * (target_x - self._state_x)
            self._state_y += k * (target_y - self._state_y)

        mag = math.hypot(self._state_x, self._state_y)
        if mag < self.MIN_MAGNITUDE:
            emitted_hue = self._last_emitted_hue
        else:
            candidate = color_utils.vec_to_hue(self._state_x, self._state_y)
            if is_cut:
                emitted_hue = candidate
            else:
                # Slew-rate safety net: worst case is a slow drift, never a
                # strobe, even if extraction/filtering misbehaves upstream.
                max_step = self.SLEW_MAX_PER_30HZ_FRAME * max(dt * 30.0, 1e-6)
                delta = color_utils.hue_delta(self._last_emitted_hue, candidate)
                if abs(delta) > max_step:
                    step = max_step if delta > 0 else -max_step
                    emitted_hue = int(round(self._last_emitted_hue + step)) % 256
                else:
                    emitted_hue = candidate

        self._last_emitted_hue = emitted_hue
        return emitted_hue, confidence


class ScreenAnalyzer:
    """
    Runs one backend (see screen_backends.py) in a dedicated daemon thread and
    exposes the latest extracted palette via a non-blocking get_palette().
    """

    def __init__(self, display_index=0, backend_name="auto", target_fps=None):
        self._display_index = display_index
        self._backend_name = backend_name
        self._target_fps = target_fps

        self._backend = None
        self.status_label = "Screen Sync (starting)"
        self._last_error = None

        # Latest-value handoff between the capture thread and the caller.
        # Publish is a single assignment of an already-built, immutable tuple;
        # under the GIL a reader can only observe a fully-old or fully-new
        # tuple, so no lock is needed. This invariant only holds as long as we
        # never mutate the published object in place and never publish its
        # fields one at a time -- always build a new tuple and assign it whole.
        self._latest = (160, 40, 220, 255)
        self._latest_ts = 0.0

        # Temporal hue smoothing + its bookkeeping. Persist across the
        # analyzer's whole lifetime (not per-frame) so the filter's state
        # vector and cut-detector history carry over between grabs.
        self._hue_filter = HueFilter()
        self._last_t = None
        self._smoothed_chroma_strength = 0.0
        self._smoothed_hue2_delta = None

        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        """Spawn the capture thread. Safe to call once; subsequent calls are a no-op."""
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="screen-capture", daemon=True)
        self._thread.start()

    def stop(self, timeout=1.0):
        """Signal the capture thread to exit and wait for it (bounded by timeout)."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    def get_palette(self):
        """
        Non-blocking read of the most recently captured color.
        Returns (hue_bass, hue_mid, hue_treble, saturation), all 0-255 ints.
        """
        return self._latest

    @property
    def health(self):
        stale_s = (time.monotonic() - self._latest_ts) if self._latest_ts else None
        return {
            "backend": self._backend.name if self._backend else None,
            "stale_s": stale_s,
            "last_error": self._last_error,
        }

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.stop()

    def _run(self):
        # The backend is created and destroyed inside this thread: capture
        # backends are thread-confined (mss cannot share its device-context
        # handles across threads on Windows).
        try:
            self._backend = create_backend(self._backend_name)
            self._backend.open(self._display_index)
        except Exception as e:
            self._last_error = str(e)
            self.status_label = "Screen Sync (failed)"
            return

        self.status_label = f"Screen Sync ({self._backend.name})"
        fps = self._target_fps or self._backend.recommended_fps
        period = 1.0 / fps

        while not self._stop_event.is_set():
            t0 = time.monotonic()
            try:
                frame = self._backend.grab()
                if frame is not None:
                    self._latest = self._extract_palette(frame)
                    self._latest_ts = time.monotonic()
                    self._last_error = None
                    if not self.status_label.startswith("Screen Sync ("):
                        self.status_label = f"Screen Sync ({self._backend.name})"
            except Exception as e:
                # Never print() from this thread: rich.Live(screen=True) owns
                # the terminal's alternate screen buffer in the main thread,
                # and writing here would corrupt it. Surface state instead.
                self._last_error = str(e)
                self.status_label = f"Screen Sync ({self._backend.name}!)"

            elapsed = time.monotonic() - t0
            self._stop_event.wait(max(0.0, period - elapsed))

        self._backend.close()

    # Saturation ramp: never hit 0 (reads as "broken" against full audio-driven
    # brightness), floor at a deliberately-neutral-looking value instead.
    # LEDs (through diffusers/keycaps) read as visually whiter than the same
    # sRGB value on a screen, so SAT_MAX uses the full byte range and the
    # ramp is deliberately steep -- see the smoothstep bounds below.
    SAT_FLOOR = 70
    SAT_MAX = 255
    SAT_SMOOTH_TAU = 0.5  # seconds
    HUE2_SMOOTH_TAU = 0.3  # seconds
    HUE2_MAX_DELTA = 96   # hue-units; keeps h_treble out of the white-out zone

    def _extract_palette(self, frame_bgra):
        """
        Reduce a captured BGRA frame to (hue_bass, hue_mid, hue_treble, saturation).

        Pipeline: extract_screen_color() (stateless, per-frame) feeds
        self._hue_filter (stateful, temporally smoothed) to get a stable
        h_mid + confidence, then saturation and the bass/treble hue offsets
        are derived from confidence/chroma_strength so uncertain frames read
        as a wide, gentle gradient and confident frames read as one strong
        color. The three hues stay analogous (never complementary) because
        the firmware additively composites their waves -- complementary hues
        would sum to white in overlaps.
        """
        now = time.monotonic()
        dt = (now - self._last_t) if self._last_t is not None else (1.0 / 30.0)
        self._last_t = now

        extraction = extract_screen_color(frame_bgra)
        hue, confidence = self._hue_filter.update(extraction, dt)

        k_sat = 1.0 - math.exp(-dt / self.SAT_SMOOTH_TAU)
        self._smoothed_chroma_strength += k_sat * (
            extraction["chroma_strength"] - self._smoothed_chroma_strength
        )
        # These bounds are calibrated against real captured desktop frames,
        # not the solid-color synthetic frames used during development: a
        # typical, visibly-colorful desktop window measured chroma_strength
        # around 0.02-0.10 (chroma^1.5 * value * the center-weighting window
        # compound to a much smaller number than the frame's raw average
        # chroma, e.g. 0.10 strength from a frame whose raw mean chroma was
        # 0.57). The upper bound is deliberately tight (most ordinary content
        # should already reach SAT_MAX) because LEDs read as visually whiter
        # than the same value would look on a screen -- anything less than
        # "clearly saturated" tends to look plain white on the hardware.
        sat_t = color_utils.smoothstep(self._smoothed_chroma_strength, 0.008, 0.025)
        saturation = int(round(color_utils.lerp(self.SAT_FLOOR, self.SAT_MAX, sat_t)))

        spread = color_utils.lerp(32, 14, confidence)
        h_bass = int(round((hue - spread) % 256))

        hue2 = extraction.get("hue2")
        if hue2 is not None:
            raw_delta = color_utils.hue_delta(hue, hue2)
            raw_delta = max(-self.HUE2_MAX_DELTA, min(self.HUE2_MAX_DELTA, raw_delta))
            if self._smoothed_hue2_delta is None:
                self._smoothed_hue2_delta = float(raw_delta)
            else:
                k_hue2 = 1.0 - math.exp(-dt / self.HUE2_SMOOTH_TAU)
                self._smoothed_hue2_delta += k_hue2 * (raw_delta - self._smoothed_hue2_delta)
            h_treble = int(round((hue + self._smoothed_hue2_delta) % 256))
        else:
            self._smoothed_hue2_delta = None
            h_treble = int(round((hue + spread) % 256))

        return h_bass, int(hue), h_treble, saturation
