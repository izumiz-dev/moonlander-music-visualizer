# Moonlander Music Visualizer

This project transforms your **ZSA Moonlander** keyboard into a high-performance, low-latency music visualizer. It analyzes computer audio in real-time (Bass, Mid, Treble, Beats) and sends the data to the keyboard via Raw HID to drive stunning custom RGB effects.

## Features

-   **3-Band Analysis:** Separates audio into Bass, Mid, and Treble envelopes.
-   **Laser Beams (Treble):** Fast, horizontal white laser beams that shoot across the keyboard when high frequencies hit. (New!)
-   **Perimeter Glow (Treble):** The edges (wings) of the keyboard glow blue/white in sync with treble, acting as a frame.
-   **Shockwave (Kick/Beat):** A radial magenta/white shockwave expands from the center on every beat.
-   **Visualizer Zones:**
    -   Center: Bass (Red/Warm) -> Mid (Green) -> Treble (Blue) radial gradient.
-   **Adaptive Normalization:** Automatically adjusts to volume changes to maximize dynamic range.
-   **High Performance:** 60 FPS target with optimized Python analysis (NumPy) and C firmware rendering.

## Directory Structure

```
.
├── moonlander_musicviz/            # [Host] Python Audio Analyzer & HID Sender
│   ├── audio_analyzer.py           # FFT & Beat Detection Logic
│   └── main.py                     # Application Entry Point
├── firmware/
│   └── moonlander_musicviz_integrated/ # [Firmware] Complete Working Example Keymap
├── portable_musicviz/              # [Library] Portable files for YOUR custom keymap
│   ├── musicviz.h                  # State definition
│   ├── musicviz_core.c             # Raw HID communication logic
│   ├── rgb_matrix_user.inc         # Visualizer Effect Implementation
│   └── rules.inc.mk                # Build rule snippets
└── build_firmware.sh               # Helper script to build the reference firmware
```

---

## 🚀 How to Use (For Users / Porting)

If you have your own custom QMK keymap and want to **add** this visualizer to it:

1.  **Copy Files:** Copy the contents of `portable_musicviz/` into your keymap directory (e.g., `qmk_firmware/keyboards/zsa/moonlander/keymaps/YOUR_NAME/`).
2.  **Edit `rules.mk`:** Add the contents of `rules.inc.mk` to your `rules.mk`.
    ```makefile
    RAW_ENABLE = yes
    RGB_MATRIX_CUSTOM_USER = yes
    SRC += musicviz_core.c
    ```
3.  **Edit `keymap.c`:**
    -   Include the header: `#include "musicviz.h"`
    -   (Optional) If you use `keyboard_post_init_user`, ensure `rgb_matrix_enable()` is called.
4.  **Edit `rgb_matrix_user.inc` (if you have one):**
    -   Include the visualizer effect file: `#include "rgb_matrix_user.inc"` (Rename strictly if needed to avoid conflicts, or merge manually).
    -   *Note:* The provided `rgb_matrix_user.inc` contains the full effect logic wrapped in `RGB_MATRIX_EFFECT(musicviz)`.
5.  **Compile & Flash:** Compile your keymap as usual.

## 🔄 How to Update Your Layout (Oryx)

When you update your keymap layout on Oryx (e.g., change keys, layers):

1.  **Download Source:** Get the source zip from Oryx.
2.  **Place:** Unzip it into `firmware/oryx_source/`.
3.  **Integrate:** Copy the files from `portable_musicviz/` into that new folder.
4.  **Edit:** Apply the 3 lines of changes (`rules.mk`, `keymap.c`, `rgb_matrix_user.inc`) again.
5.  **Build:** Using the integrated script or Standard QMK workflow with the new folder path.

## 🛠️ How to Build (Reference Implementation)

If you just want to try it out using the provided configuration (requires `qmk` installed):

1.  **Setup:** Ensure `qmk_firmware` is cloned at `~/qmk_firmware`.
2.  **Build:** Run the helper script:
    ```bash
    ./build_firmware.sh
    ```
    This will copy the reference implementation to QMK and compile it.
3.  **Flash:** Use [Keymapp](https://blog.zsa.io/keymapp/) or `qmk flash` with the generated `.bin` file.

## 🎧 Information for Host (Python)

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    (Requires `numpy`, `sounddevice`, `hidapi` implementation)

2.  **Run:**
    ```bash
    # Ensure audio loopback (e.g. BlackHole) is set as default input or selected
    python -m moonlander_musicviz.main
    ```

3.  **Troubleshooting:**
    -   If "HID device not found": Ensure no other process (like Keymapp or a zombie python script) has the device open. Use `ps aux | grep python` to check.
    -   Audio input: The script uses the default system input. On Mac, use BlackHole 2ch and set it as the output for your Music app and Input for the script (via Aggregate Device or simple selection).
