# Moonlander Music Visualizer for Windows

This guide describes how to run the Moonlander Music Visualizer on Windows.
It is recommended to run this natively on Windows (instead of WSL) to maintain keyboard input functionality while controlling the LEDs.

## Prerequisites

1.  **Moonlander Keyboard**
    *   **Pre-flashed Required:** Your keyboard must already be flashed with the Music Visualizer compatible firmware. (Note: Firmware building is currently not supported natively on Windows via these scripts).
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

3.  **Set Recording Device**
    *   Open "Sound Settings" -> "Recording" tab.
    *   Right-click **"CABLE Output (VB-Audio Virtual Cable)"** and set it as the **"Default Device"**.

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
