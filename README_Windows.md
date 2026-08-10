# Moonlander Music Visualizer for Windows

This guide describes how to run the Moonlander Music Visualizer on Windows.
It is recommended to run this natively on Windows (instead of WSL) to maintain keyboard input functionality while controlling the LEDs.

## Prerequisites

1.  **Moonlander Keyboard**
    *   Your keyboard needs the Music Visualizer firmware. If it is not flashed yet, see [4. Building the Firmware](#4-building-the-firmware) — this is supported natively on Windows via QMK MSYS.
2.  **Windows 10 / 11**
3.  **Python 3.11 or later**
    *   Install from the Microsoft Store or the official website.
4.  **VB-CABLE (Virtual Audio Device)**
    *   Required to capture system audio (e.g., YouTube).
    *   Download and install for free from [VB-AUDIO Software](https://vb-audio.com/Cable/).

---

## 1. Audio Setup (Critical)

Configure Windows to route audio to the Visualizer.

1.  **Install VB-CABLE**
    *   Unzip the downloaded file and run `VBCABLE_Setup_x64.exe` as **Administrator**.
    *   **Restart your PC** after installation.

2.  **Set Playback Device**
    *   Click the speaker icon in the taskbar and switch the playback device to **"CABLE Input (VB-Audio Virtual Cable)"**.
    *   *Note: System audio will now flow into the virtual cable.*

3.  **Set Recording Device** *(optional)*
    *   Open "Sound Settings" -> "Recording" tab.
    *   Right-click **"CABLE Output (VB-Audio Virtual Cable)"** and set it as the **"Default Device"**.
    *   *Not strictly required:* `find_audio_device()` in `main.py` looks the device up **by name**, so it picks up CABLE Output even when something else is your default recording device. Step 2 above is the one that actually matters.

> **How to hear audio through speakers:**
> When CABLE Input is selected, you won't hear sound from your speakers.
> To fix this: Open "Sound Settings" -> "Recording" tab -> Double-click **"CABLE Output"** -> **"Listen"** tab -> Check **"Listen to this device"** and select your speakers/headphones in the "Playback through this device" dropdown.

---

## 2. Project Setup

Use PowerShell to set up the environment.

### Using `mise` (Recommended)
1.  **Install mise** (if not installed):
    ```powershell
    irm https://mise.jdx.dev/install.ps1 | iex
    # Restart PowerShell after installation
    ```
2.  **Install Dependencies**:
    Run the following in the project folder:
    ```powershell
    mise run install
    ```
    *If you encounter permission errors, allow script execution:*
    `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### Using Python manually
1.  **Install Libraries**:
    ```powershell
    python -m pip install -r requirements.txt
    ```

---

## 3. How to Run

### Standard Mode
The keyboard LEDs will react to the system audio.

```powershell
# Using mise
mise run live

# Manual execution
python -m moonlander_musicviz.main
```

*(Note: Screen Sync mode is disabled/unsupported in this configuration)*

---

## 4. Building the Firmware

Only needed if your keyboard does not have the Music Visualizer firmware yet, or if you changed
your Oryx layout. Building runs through **QMK MSYS**, which ships its own bash — the same
`build_firmware.sh` used on macOS works there unchanged.

### 4.1 Install QMK MSYS

Download and run the installer from [msys.qmk.fm](https://msys.qmk.fm/), then open the
**QMK MSYS** terminal and run:

```bash
qmk setup
```

This clones `qmk_firmware` (~2 GB including submodules) into `C:\Users\<you>\qmk_firmware`, which is
exactly where `build_firmware.sh` expects it. Finish with `qmk doctor` and make sure
`arm-none-eabi-gcc` reports a version.

> **If `qmk doctor` says `Failed to compile a simple program with arm-none-eabi-gcc, return code 127`:**
> the bundled toolchains live in `/opt/qmk` but need `libwinpthread-1.dll` from `/mingw64/bin`, which
> the installer leaves off `PATH`. Fix it permanently by creating
> `C:\QMK_MSYS\etc\profile.d\zzz-qmk-mingw-dll-path.sh` containing:
> ```sh
> export PATH="$PATH:/mingw64/bin"
> ```
> Append rather than prepend, so mingw's tools never shadow QMK's own.

> **If `qmk` is not found at all**, the installer's CLI step did not complete. Install it manually:
> ```bash
> UV_TOOL_DIR=/opt/uv/tools UV_TOOL_BIN_DIR=/opt/uv/tools/bin /opt/uv/uv.exe tool install qmk
> ```

### 4.2 Get your Oryx source

On [Oryx](https://configure.zsa.io/moonlander), open your layout and download **Source** (the zip),
not the compiled `.bin`. A `.bin` cannot be used as a base — the visualizer is merged in at the
source level.

Unzip it and place the inner folder (the one containing `rules.mk`) into `firmware/oryx_source/`:

```
firmware/oryx_source/zsa_moonlander_<your-layout>_source/
```

### 4.3 Build and flash

From the **QMK MSYS** terminal (not PowerShell):

```bash
cd /c/Users/<you>/Repositories/moonlander-music-visualizer
./build_firmware.sh
```

The result lands at `C:\Users\<you>\qmk_firmware\zsa_moonlander_my_musicviz_automerge.bin`.
Open [Keymapp](https://blog.zsa.io/keymapp/), choose **Select Firmware**, and point it at that file.

After flashing, cycle the RGB modes until you reach `musicviz` — custom effects are appended to the
**end** of the list, so with the Moonlander's ~45 built-in animations you may need to hold the mode
key for a while. The choice is stored in EEPROM, so you only do this once.

> **Line endings matter.** `.gitattributes` pins `*.sh` and `*.mk` to LF. If you bypass it, Windows
> CRLF makes bash fail with `$'\r': command not found` and silently folds a CR into make variables.

---

## Troubleshooting

### Q. LEDs are not lighting up
*   **Check Keyboard Mode:**
    Cycle through the Moonlander's LED modes (usually using the "Mode Next" key) until you reach the Visualizer mode (often at the end of the list).
*   **Check Brightness:**
    Ensure the RGB brightness is not set to 0. Press the brightness up key.
*   **Check Connection:**
    Verify that the log shows `[HID] Opened: ZSA Technology Labs ...`.

### Q. Not reacting to audio (Dashboard is flat)
*   **Check Input Device:**
    Verify the log shows `[+] Using device: CABLE Output ...`.
*   **Check Windows Settings:**
    Ensure "CABLE Output" is set as the "Default Recording Device" and that the volume meter in Sound Settings is moving when audio plays.

### Q. Error: `ModuleNotFoundError`
*   Missing libraries. Re-run the installation:
    ```powershell
    python -m pip install -r requirements.txt
    ```
*   If `rich` is missing specifically, run: `python -m pip install rich`.

### Q. Why not use WSL?
*   While possible, using USB pass-through with WSL **disables keyboard input on Windows**. This Windows native method allows you to use the keyboard for typing while the LEDs are being controlled.
