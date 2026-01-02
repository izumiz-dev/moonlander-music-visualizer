# GEMINI Project Context

This file contains the "brain dump" of the project context, synthesized from Serena memories and current project structure.
Use this file to understand the project's purpose, architecture, and operational workflows.

## 1. Project Overview

### Purpose
High-performance Music & Screen Visualizer for the ZSA Moonlander keyboard.
Synchronizes RGB LEDs with macOS system audio and screen colors in real-time.

### Key Features
-   **Audio Analysis:** 3-Band (Bass/Mid/Treble) analysis using FFT.
-   **Screen Sync:** Captures primary monitor content to dynamically color-grade the keyboard (`--screen` flag).
-   **Symmetric Visuals:** Radial waves expand from the inner edges of both keyboard halves, ensuring perfect left-right symmetry.
-   **Communication:** Raw HID (32-byte custom packets) with hue/saturation support.

## 2. Architecture & Tech Stack

### Host (macOS)
-   **Language:** Python 3.11
-   **Libraries:** 
    -   `numpy`: FFT & data processing
    -   `sounddevice`: Audio Capture
    -   `mss`: High-speed Screen Capture
    -   `hid`: Raw HID communication
-   **Audio Loopback:** BlackHole 2ch (Virtual Audio Driver)

### Firmware (Moonlander / QMK)
-   **Core:** QMK Firmware
-   **Protocol:** Raw HID
-   **Structure:**
    -   `portable_musicviz/`: **[Source of Truth]** The library code (distributable).
    -   `firmware/oryx_source/`: **[User Input]** Place for user's Oryx layout export.
    -   `build_firmware.sh`: **[Build System]** Script that merges User Input + Portable Library -> Output Binary.

## 3. Operational Workflows

### A. Updating the Keyboard Layout
1.  **Oryx:** Edit layout on [configure.zsa.io](https://configure.zsa.io).
2.  **Download:** Download Source (zip).
3.  **Deploy:** Unzip the folder into `firmware/oryx_source/`.
4.  **Build:** Run `./build_firmware.sh`.
5.  **Flash:** Use Keymapp or `qmk flash`.

### B. Running the Visualizer
1.  **Setup Audio:** Set "BlackHole 2ch" as the Output.
2.  **Run Music Mode:** `python -m moonlander_musicviz.main`
3.  **Run Screen Sync:** `python -m moonlander_musicviz.main --screen`

## 4. Known Memories (Serena)

-   **`project_overview`**: "Screen Sync added", "Symmetric Radial Waves", "Laser/Shockwave removed".
-   **`task_completion`**: "Symmetry Logic Fixed", "Vivid Color Boost implemented".

## 5. Current State Notes
-   The visualizer logic is strictly defined in `portable_musicviz/rgb_matrix_user.inc`.
-   Symmetry is handled by independently calculating distance from the "inner edge" for left (0-35) and right (36-71) halves.
-   Screen capture uses `mss` and boosts saturation to avoid washing out colors.