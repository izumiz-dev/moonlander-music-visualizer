# Moonlander Music Visualizer

This project transforms your **ZSA Moonlander** keyboard into a high-performance, low-latency music and screen visualizer. It analyzes computer audio (Bass, Mid, Treble) and screen content in real-time to drive stunning custom RGB effects.

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
│   ├── screen_analyzer.py          # Screen Capture & Color Extraction
│   ├── hid_sender.py               # Raw HID Communication
│   └── main.py                     # CLI Entry Point
├── firmware/
│   └── oryx_source/                # [Input] Place your Oryx source zip contents here
├── portable_musicviz/              # [Library] The Visualizer Logic (C Code)
│   ├── musicviz.h                  # State definition
│   ├── rgb_matrix_user.inc         # Visualizer Effect Implementation
│   └── rules.inc.mk                # Build rules
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

**Run:**

*   **Music Mode (Default):**
    Analyzes audio and uses preset color palettes.
    ```bash
    python -m moonlander_musicviz.main
    ```

*   **Screen Sync Mode:**
    Analyzes audio for rhythm *AND* captures screen colors for the palette.
    ```bash
    python -m moonlander_musicviz.main --screen
    ```

### 2. Firmware Side (Moonlander)

This project is designed to "inject" the visualizer into your existing Oryx layout.

1.  **Export Source:** Download your layout source code from [Oryx](https://configure.zsa.io).
2.  **Place:** Unzip the folder into `firmware/oryx_source/`.
3.  **Build:** Run the build script. It automatically finds your source, injects the visualizer code, and compiles.
    ```bash
    ./build_firmware.sh
    ```
4.  **Flash:** Use [Keymapp](https://blog.zsa.io/keymapp/) or `qmk flash` with the generated `.bin` file in `~/qmk_firmware/`.

## ⚙️ Technical Details

-   **Symmetry Logic:** The firmware automatically calculates the "inner edges" of both keyboard halves to ensure the light waves expand perfectly symmetrically from the center, regardless of how far apart you place the units.
-   **Vivid Colors:** In Screen Sync mode, the analyzer boosts the saturation of captured colors, ensuring the keyboard always lights up with vivid, distinct colors even during dark or pale scenes.

## ⚠️ Notes

-   **Audio Setup:** Ensure "BlackHole 2ch" is set as your system output (or part of a Multi-Output Device) so the visualizer can "hear" the system audio.
-   **Performance:** Screen capture is optimized (downsampled) to maintain ~30fps with minimal CPU usage.