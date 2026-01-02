# GEMINI Project Context

This file contains the "brain dump" of the project context, synthesized from Serena memories and current project structure.
Use this file to understand the project's purpose, architecture, and operational workflows.

## 1. Project Overview

### Purpose
High-performance Music Visualizer for the ZSA Moonlander keyboard.
Synchronizes RGB LEDs with macOS system audio in real-time (60 FPS target).

### Key Features
-   **Audio Analysis:** 3-Band (Bass/Mid/Treble) + Beat Detection + Transient Analysis.
-   **Visual Effects:**
    -   **Laser Beams:** Horizontal white beams on Treble events.
    -   **Perimeter Glow:** Blue/Cyan glow on keyboard edges synced with high frequencies.
    -   **Shockwave:** Radial ripple effect on Beats/Kick.
-   **Communication:** Raw HID (32-byte custom packets).

## 2. Architecture & Tech Stack

### Host (macOS)
-   **Language:** Python 3.11
-   **Libraries:** `numpy` (FFT), `sounddevice` (Audio Capture), `hid` (Raw HID)
-   **Audio Loopback:** BlackHole 2ch (Virtual Audio Driver)

### Firmware (Moonlander / QMK)
-   **Core:** QMK Firmware
-   **Protocol:** Raw HID
-   **Structure:**
    -   `portable_musicviz/`: **[Source of Truth]** The library code (distributable).
    -   `firmware/moonlander_musicviz_integrated/`: **[Reference]** Working example keymap.
    -   `firmware/oryx_source/`: **[User Input]** Place for user's Oryx layout export.
    -   `build_firmware.sh`: **[Build System]** Script that merges User Input + Portable Library -> Output Binary.

## 3. Operational Workflows

### A. Updating the Keyboard Layout
1.  **Oryx:** Edit layout on [configure.zsa.io](https://configure.zsa.io).
2.  **Download:** Download Source (zip).
3.  **Deploy:** Unzip the folder into `firmware/oryx_source/`.
    *   *Note:* The `.gitignore` is set to ignore contents here (except README), keeping the repo clean.
4.  **Build:** Run `./build_firmware.sh`.
    *   The script auto-detects the new source, injects the Visualizer library, disables conflicting Oryx features, and compiles.
5.  **Flash:** Use Keymapp or `qmk flash`.

### B. Running the Visualizer
1.  **Setup Audio:** Set "BlackHole 2ch" as the Output for Music/System and Input for the Visualizer.
2.  **Run:**
    ```bash
    mise run run
    # OR
    python -m moonlander_musicviz.main
    ```

### C. Coding Conventions
-   **Python:** PEP 8, formatted with Black/Ruff (if available).
-   **Firmware:** QMK C coding style.
-   **Management:** `mise` for environment/tasks.

## 4. Known Memories (Serena)

-   **`project_overview`**: "Bass/Mid/Treble 3-band rendering", "Shockwave on beat".
-   **`task_completion`**: Checklist includes "Dependency Check", "Device Discovery", "Runtime Verification".
-   **`suggested_commands`**: `mise run install`, `mise run list-devices`, `qmk compile`.

## 5. Current State Notes
-   The "Oryx Source" (`firmware/oryx_source`) is treated as volatile user input.
-   The "Portable Library" (`portable_musicviz`) is the stable product core.
-   The build script (`build_firmware.sh`) bridges the two.
-   **Critical:** Do not edit files in `firmware/oryx_source` directly; they will be overwritten by new downloads. Edit `portable_musicviz` for logic changes.
