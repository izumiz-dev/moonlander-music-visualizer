# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this project is

A host-side Python app that analyzes system audio (and optionally screen content) and drives the
RGB LEDs of a **ZSA Moonlander** keyboard over **QMK Raw HID**, plus the QMK C firmware effect that
renders the packets. Two halves that must stay in sync:

- `moonlander_musicviz/` — **Host** (Python 3.11): audio FFT, screen capture, palettes, HID sender,
  terminal dashboard, LED simulator.
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
python -m moonlander_musicviz.main --screen     # screen color sync (macOS path; unsupported on the Windows setup)
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

Follow `.agent/workflows/led_logic_policy.md`. Short version:

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

## Build-script behaviors worth knowing

`build_firmware.sh` does more than copy files:

- Finds the real source root by locating `rules.mk` inside `firmware/oryx_source/*` (Oryx zips nest).
- Deletes `keymap.json` so `keymap.c` is compiled.
- Patches `rawhid_state.rgb_control` → `0` in `keymap.c` (Oryx's HID handler must not fight ours).
  Uses BSD `sed -i ''`, so it is **macOS-flavored**.
- Appends `portable_musicviz/rules.inc.mk`, which sets `ORYX_ENABLE=no`, `RAW_ENABLE=yes`,
  `RGB_MATRIX_CUSTOM_USER=yes`. `ORYX_ENABLE=no` is why `musicviz_core.c` defines a dummy
  `webhid_leds` symbol — don't remove it.
- Output: `~/qmk_firmware/zsa_moonlander_my_musicviz_automerge.bin`.

Windows has no firmware build path; that platform assumes an already-flashed keyboard.

## Debugging

- `--simulator` renders the LED matrix in the terminal and writes `.log/sim_debug_*.jsonl` — one JSON
  object per frame with audio bands, hues, gains, and average LED brightness. This is the fastest way
  to reason about visual tuning without hardware; read the JSONL rather than guessing.
- No LEDs: the keyboard must be on the `musicviz` RGB mode (cycle "Mode Next"), brightness > 0, and
  the log must show `[HID] Opened: ...`.
- Flat dashboard: the loopback device (BlackHole 2ch / CABLE Output / Stereo Mix) must be the default
  recording device. `find_audio_device()` matches those names in priority order.

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
