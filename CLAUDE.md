# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this project is

A host-side Python app that analyzes system audio (and optionally screen content) and drives the
RGB LEDs of a **ZSA Moonlander** keyboard over **QMK Raw HID**, plus the QMK C firmware effect that
renders the packets. Two halves that must stay in sync:

- `moonlander_musicviz/` — **Host** (Python 3.11): audio FFT, screen capture (`screen_analyzer.py` +
  `screen_backends.py`, threaded, mss/dxcam), circular hue math (`color_utils.py`), palettes, HID
  sender, terminal dashboard, LED simulator.
- `portable_musicviz/` — **Firmware library** (C, QMK custom RGB matrix effect). Source of truth for
  all on-keyboard rendering; distributable/injectable into any Oryx layout.
- `firmware/oryx_source/` — drop zone for the user's Oryx export (gitignored input).
- `firmware/moonlander_musicviz_integrated/` — fallback reference keymap used when no Oryx source exists.
- `build_firmware.sh` — merges Oryx source + `portable_musicviz/` into `~/qmk_firmware` and compiles.

## Commands

Use `mise` tasks (defined in `.mise.toml`); they activate the `.venv` automatically.

```bash
mise run install       # create .venv + pip install -r requirements.txt
mise run list-devices  # list audio inputs, find BlackHole / VB-CABLE
mise run live          # run the visualizer against real hardware
mise run sim           # Digital Twin: render LEDs in the terminal, no keyboard needed
mise run clean         # remove .venv and caches (POSIX rm -rf; not Windows-safe)
```

Manual equivalents:

```bash
python -m moonlander_musicviz.main              # music mode
python -m moonlander_musicviz.main --screen     # screen color sync (Windows and macOS both work)
python -m moonlander_musicviz.main --simulator  # terminal simulator + JSONL debug log
```

Firmware:

```bash
./build_firmware.sh                                  # macOS/Linux only, needs ~/qmk_firmware + qmk CLI
qmk compile -kb zsa/moonlander -km my_musicviz_automerge
```

There is no test suite and no linter configured. Verification is manual (see checklist below).

## The HID protocol is the contract

32-byte packet, written by `moonlander_musicviz/hid_sender.py`, parsed by
`portable_musicviz/musicviz_core.c` (`raw_hid_receive`). **Any change to one side requires the same
change to the other side, and to `musicviz_state_t` in `musicviz.h`.** The firmware silently drops
packets that fail the magic/version check, so a mismatch looks like "LEDs just stopped reacting".

| Byte | Field |
|---|---|
| 0 | magic `0x4D` ('M') |
| 1 | version `0x01` |
| 2 | flags: bit0 enable, bit1 strobe_enable, bit2 safety_limit |
| 3 | master_gain (`10 + rms² * 245`) |
| 4–9 | loudness_rms, loudness_peak, bass, mid, treble, beat |
| 10–13 | hue_bass, hue_mid, hue_treble, saturation |
| 14–17 | fx_speed (unused), shockwave_strength, perimeter_sparkle, beat_refractory_ms (×4 = ms) |
| 18–31 | reserved, zero-filled |

Discovery is by HID **Usage Page `0xFF60` / Usage `0x61`**, not VID/PID. On Windows the write must be
prefixed with a `0x00` report ID (33 bytes total) — already handled in `send_packet`.

## Where logic belongs (Host vs Firmware)

- **Host (Python):** FFT, screen capture, palette selection, beat detection, anything needing buffers
  or system APIs. Send *high-level control parameters*.
- **Firmware (C):** per-LED math, smoothing, geometry, high-frequency rendering.
- MCU is an STM32F303 (72 MHz, single-precision FPU); some units may be F072 (no FPU). The existing
  effect uses `float`/`sqrtf` in the per-LED loop — for **new** effects prefer integer/fixed-point,
  and avoid adding divisions or `sqrt` inside the loop. Pre-compute geometry once (see
  `compute_geometry()` in `rgb_matrix_user.inc`).

## LED geometry / symmetry

72 LEDs. **Indices 0–35 are the left half, 36–71 the right half.** Symmetry is achieved by measuring
each LED's distance from its own half's *inner* edge (`max_left_x` / `min_right_x`), so waves expand
outward identically regardless of how far apart the halves sit. Preserve this convention when adding
effects — do not compute distance from a single global center.

## Screen Color Sync architecture

`--screen` captures the screen and sends its dominant color instead of an audio-derived palette.
Host-only, cross-platform (macOS and Windows), no HID protocol change.

- `moonlander_musicviz/screen_backends.py` defines the `ScreenCaptureBackend` contract
  (`open`/`grab`/`close`) and the platform backends: `MssBackend` (GDI, all platforms) and
  `DxcamBackend` (Windows Desktop Duplication API, auto-selected when available). `sys.platform` is
  checked in exactly one place (`create_backend`) — a new backend is a new class plus one branch there.
- `screen_analyzer.py`'s `ScreenAnalyzer` runs the backend inside its **own daemon thread**, decoupled
  from the 30Hz audio loop in `main.py`. This is load-bearing: a synchronous `mss` grab() costs
  40–150ms depending on monitor size, which would starve `sounddevice`'s ~21ms/block read budget if
  called from the audio loop directly — not just delay the color, but make the audio itself glitchy.
  The capture thread publishes the latest `(hue_bass, hue_mid, hue_treble, saturation)` as a single
  atomic tuple assignment (`ScreenAnalyzer._latest`); `get_palette()` just reads it, non-blocking, no
  lock. That's only safe because the tuple is always replaced whole — never mutate it in place or
  publish its fields separately.
- **"Primary display" is not "index 1."** mss's `monitors` list order is enumeration order, not
  primary-first — on real hardware the true Windows-primary display has ended up at a different index
  than `monitors[1]`. Both backends resolve `display_index=0` independently: `MssBackend` via the
  Windows invariant that the primary display's origin is always the desktop's `(0, 0)`;
  `DxcamBackend` via DXGI's own primary flag (`dxcam.output_info()`). If you touch monitor resolution,
  verify both backends still agree on which physical display index `0` means.
- **Saturation constants in `ScreenAnalyzer._extract_palette` are calibrated against real captured
  desktop frames, not synthetic ones.** A visibly colorful real window measured
  `chroma_strength` around 0.02–0.10 — much lower than a solid-color test frame, because the
  extractor's `chroma^1.5 * value * center-window` weighting compounds multiplicatively. Thresholds
  tuned only against synthetic solid frames leave ordinary content pinned near `SAT_FLOOR`, reading as
  washed-out/pastel. LEDs also read visually whiter than the same value looks on a screen (diffusers,
  keycaps), so the ramp is deliberately biased toward saturating quickly. If retuning, capture a real
  frame and check `extract_screen_color(frame)['chroma_strength']` — don't guess from synthetic frames.
- Hue is a value on a 256-point wheel, not a plain scalar — averaging/lerping/clamping it directly is
  wrong across the 0/255 wrap. Everything that touches hue goes through `color_utils.py`'s circular
  helpers (`hue_delta`, `hue_lerp`, `hue_to_vec`/`vec_to_hue`, `circular_smooth`).
- Known, unavoidable limitation: DRM-protected video (Netflix, Prime Video, Disney+) captures as black
  under both GDI and Desktop Duplication — an OS-level content-protection behavior, not a bug here.

## Build-script behaviors worth knowing

`build_firmware.sh` does more than copy files:

- Finds the real source root by locating `rules.mk` inside `firmware/oryx_source/*` (Oryx zips nest).
- Deletes `keymap.json`. Newer Oryx exports use it to declare `"modules": ["zsa/oryx",
  "zsa/defaults"]`, but upstream QMK has no `modules/zsa`, so it must go.
- Patches `rawhid_state.rgb_control` → `0` in `keymap.c` (Oryx's HID handler must not fight ours).
  Written via a temp file, **not** `sed -i`, because in-place sed differs between BSD and GNU.
- Appends `portable_musicviz/rules.inc.mk`, which sets `ORYX_ENABLE=no`, `RAW_ENABLE=yes`,
  `RGB_MATRIX_CUSTOM_USER=yes`, `RGB_MATRIX_CUSTOM_KB=no`. `ORYX_ENABLE=no` is why
  `musicviz_core.c` defines a dummy `webhid_leds` symbol — don't remove it. `RGB_MATRIX_CUSTOM_KB=no`
  cancels Oryx's `yes`, which would require `rgb_matrix_kb.inc` (ZSA fork only).
- Appends `portable_musicviz/config.inc.h` to the keymap's `config.h`, mapping the legacy `RGB_*`
  keycode names Oryx emits onto upstream's current `RM_*` ones. `RGB_SLD` is deliberately absent —
  Oryx declares it itself in `keymap.c`'s `custom_keycodes` enum.
- Output: `~/qmk_firmware/zsa_moonlander_my_musicviz_automerge.bin`.

Both injection steps are guarded by a `grep` so re-running the script is idempotent.

**Windows builds work** via QMK MSYS (which ships bash), using the same script — see
`README_Windows.md`. Two install-time gotchas are documented there: the bundled toolchains need
`/mingw64/bin` on `PATH` for `libwinpthread-1.dll`, and the installer sometimes fails to install the
`qmk` CLI itself.

`.gitattributes` pins `*.sh` and `*.mk` to `eol=lf`. Windows checkouts default to
`core.autocrlf=true`, and CRLF makes bash die with `$'\r': command not found` while make silently
folds the CR into variable values. Keep new shell/make files covered by it.

## Debugging

- `--simulator` renders the LED matrix in the terminal and writes `.log/sim_debug_*.jsonl` — one JSON
  object per frame with audio bands, hues, gains, and average LED brightness. This is the fastest way
  to reason about visual tuning without hardware; read the JSONL rather than guessing.
- No LEDs: the keyboard must be on the `musicviz` RGB mode (cycle "Mode Next"), brightness > 0, and
  the log must show `[HID] Opened: ...`. Custom effects are appended to the end of the mode list, so
  on a Moonlander that is ~45 presses past the built-ins.
- Flat dashboard: audio must actually be routed into the loopback device. `find_audio_device()`
  matches BlackHole / CABLE Output / Stereo Mix **by name**, not by system default, so the default
  recording device is irrelevant — what matters is that playback goes to the cable's input.

## Conventions

- Python: PEP 8, `PascalCase` classes, `snake_case` functions/files, docstrings on classes and public
  methods, all host logic inside the `moonlander_musicviz` package. Type hints optional.
- C: follow the surrounding QMK style in `rgb_matrix_user.inc`; keep the section comment banners.
- Docs are bilingual: `README.md` / `README.ja.md` and `README_Windows.md` / `README_Windows.ja.md`.
  Update both languages when changing user-facing docs.

## Before calling a task done

1. `mise run install` still succeeds if dependencies changed.
2. `mise run list-devices` detects the loopback device.
3. `mise run live` (or `mise run sim` without hardware) runs without errors and the dashboard reacts.
4. If the firmware changed: it compiles, and the 32-byte protocol still matches on both sides.
