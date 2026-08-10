# Moonlander Music Visualizer

[日本語 (Japanese)](README.ja.md)

This project transforms your **ZSA Moonlander** keyboard into a high-performance, low-latency music and screen visualizer. It analyzes computer audio (Bass, Mid, Treble) and screen content in real-time to drive stunning custom RGB effects.

## Demo

[![Moonlander Music Visualizer Demo](https://img.youtube.com/vi/_oECPrUgOGk/0.jpg)](https://www.youtube.com/watch?v=_oECPrUgOGk)

## Features

-   **Screen Color Sync (New!):** Captures your main display's dominant colors in real-time and syncs the keyboard backlight to match the mood of movies or MVs.
-   **Symmetric Radial Waves:** Colors expand symmetrically from the center of the split keyboard (USB connection side) outwards, creating a seamless, unified look even when the halves are separated.
-   **3-Band Audio Analysis:** Accurately separates audio into Bass, Mid, and Treble envelopes to modulate brightness and wave spread.
-   **Adaptive Brightness:** Audio loudness modulates the overall master brightness for dynamic contrast.
-   **High Performance:** Optimized Python backend (NumPy, MSS) and efficient QMK C firmware rendering.

## Directory Structure

```
.
├── moonlander_musicviz/            # [Host] Python App
│   ├── audio_analyzer.py           # FFT Logic
│   ├── screen_analyzer.py          # Screen Capture Orchestration & Color Extraction
│   ├── screen_backends.py          # Screen capture backends (mss, dxcam on Windows)
│   ├── color_utils.py              # Circular hue math (averaging/smoothing on a 0-255 wheel)
│   ├── hid_sender.py               # Raw HID Communication
│   └── main.py                     # CLI Entry Point
├── firmware/
│   └── oryx_source/                # [Input] Place your Oryx source zip contents here
├── portable_musicviz/              # [Library] The Visualizer Logic (C Code)
│   ├── musicviz.h                  # State definition
│   ├── rgb_matrix_user.inc         # Visualizer Effect Implementation
│   ├── rules.inc.mk                # Build rules (appended to the keymap's rules.mk)
│   └── config.inc.h                # Keycode compat shims (appended to the keymap's config.h)
└── build_firmware.sh               # Auto-build script (Merges Oryx source + Musicviz)
```

## 🚀 Installation & Usage

### 1. Host Side (Python)

**Requirements:**
-   Python 3.11+
-   [BlackHole 2ch](https://github.com/ExistentialAudio/BlackHole) (for audio loopback on macOS)

**Setup:**
```bash
# Install Python dependencies
pip install -r requirements.txt
```

**Run via Mise (Recommended):**

*   **Music Mode (Live):**
    ```bash
    mise run live
    ```

*   **Digital Twin Simulator:** 
    Simulate LED effects in the terminal without hardware.
    ```bash
    mise run sim
    ```

**Manual Run:**

*   **Music Mode (Default):**
    ```bash
    python -m moonlander_musicviz.main
    ```

*   **Screen Sync Mode:**
    ```bash
    python -m moonlander_musicviz.main --screen
    ```
    Add `--screen-monitor` (default `primary`) to pick a display, or `--screen-fps` to override the
    capture rate. On Windows this uses the Desktop Duplication API for capture; see
    [README_Windows.md](README_Windows.md#screen-color-sync) for details and the (unavoidable, OS-level)
    limitation with DRM-protected video.

### 2. Firmware Side (Moonlander)

This project is designed to "inject" the visualizer into your existing Oryx layout.

Requires a `qmk setup` environment (`~/qmk_firmware` + the `qmk` CLI). On Windows, use QMK MSYS —
see [README_Windows.md](README_Windows.md#4-building-the-firmware).

1.  **Export Source:** Download your layout's **Source** (zip) from [Oryx](https://configure.zsa.io).
    A compiled `.bin` cannot be used as a base — the visualizer is merged in at the source level.
2.  **Place:** Unzip the folder into `firmware/oryx_source/`.
3.  **Build:** Run the build script. It automatically finds your source, injects the visualizer code, and compiles.
    ```bash
    ./build_firmware.sh
    ```
4.  **Flash:** Use [Keymapp](https://blog.zsa.io/keymapp/) (**Select Firmware**) or `qmk flash` with the generated `.bin` file in `~/qmk_firmware/`.
5.  **Select the effect:** Cycle the RGB modes to `musicviz`. Custom effects are appended to the **end**
    of the list, so expect to pass ~45 built-in animations. The choice persists in EEPROM.

### Building an Oryx export against upstream QMK

Oryx generates code for ZSA's QMK fork, so a stock export does not compile against upstream QMK as-is.
`build_firmware.sh` reconciles this automatically — worth knowing if you ever build by hand:

-   `ORYX_ENABLE = no` — the visualizer owns Raw HID, so Oryx's handler must not fight it.
    References to `rawhid_state.rgb_control` in `keymap.c` are rewritten to `0`, and
    `musicviz_core.c` defines a dummy `webhid_leds` to satisfy the linker.
-   `RGB_MATRIX_CUSTOM_KB = no` — Oryx sets this to `yes`, which pulls in
    `keyboards/zsa/moonlander/rgb_matrix_kb.inc`. That file exists only in ZSA's fork.
-   `keymap.json` is deleted — newer exports declare `"modules": ["zsa/oryx", "zsa/defaults"]`,
    and `modules/zsa` does not exist upstream.
-   `config.inc.h` maps the legacy `RGB_*` keycode names Oryx emits onto the current `RM_*` ones
    (`RGB_TOG` → `RM_TOGG`, `RGB_MODE_FORWARD` → `RM_NEXT`, and so on).

**Trade-off:** because `ORYX_ENABLE = no` is required, Keymapp's live features (live training,
heatmap) and Oryx's live RGB preview stop working. Your keys, layers, macros and per-layer colors are
unaffected, and Keymapp can still flash the firmware.

## ⚙️ Technical Details

-   **Symmetry Logic:** The firmware automatically calculates the "inner edges" of both keyboard halves to ensure the light waves expand perfectly symmetrically from the center, regardless of how far apart you place the units.
-   **Vivid Colors:** In Screen Sync mode, the analyzer boosts the saturation of captured colors, ensuring the keyboard always lights up with vivid, distinct colors even during dark or pale scenes.

## ⚠️ Notes

-   **Performance:** Screen capture runs on its own thread, decoupled from the audio loop, so it never
    stalls the audio path. On Windows it captures via the Desktop Duplication API (~60fps, near-zero
    CPU); the `mss` fallback used elsewhere is floored around one display-compositor frame per
    capture (~12fps).

<details>
<summary><b>🎧 Audio Setup Details (macOS Stability)</b></summary>

To prevent audio stuttering or "pops" when using BlackHole with a Multi-Output Device, follow these precise steps in **Audio MIDI Setup**:

1.  **Create Multi-Output Device:** Click the `+` icon and select `Create Multi-Output Device`.
2.  **Master Device:** Set the **Master Device** (or Clock Source) to your **physical hardware** (e.g., *External Headphones*, *MacBook Pro Speakers*, or *DAC*). Never set BlackHole as the master.
3.  **Drift Correction:** Enable **Drift Correction** for **BlackHole 2ch** only. Keep it disabled for your master physical device.
4.  **Sample Rate:** Ensure all sub-devices within the Multi-Output Device are set to the same sample rate (e.g., **48,000 Hz**).
5.  **Device Order:** In the list of sub-devices, ensure your physical device is checked *first* so it appears at the top of the internal OS list.

This configuration ensures that the virtual driver (BlackHole) stays perfectly synced with your hardware's clock, providing a lag-free and glitch-free experience.
</details>
