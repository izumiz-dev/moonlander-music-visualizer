# Project Overview: Moonlander Music Visualizer

## Purpose
macOS上のシステムオーディオ再生に合わせて、ZSA MoonlanderキーボードのRGB LEDを同期させるビジュアライザー。ベース、ミッド、トレブルの3つの周波数帯域に基づいた空間的なレンダリング、ビート検出によるショックウェーブ・エフェクト、高域に応じた外周のスパークルなどを実現する。

## Tech Stack
- **Firmware**: QMK (Moonlander) + Raw HID + custom RGB Matrix effect
- **Host (macOS)**: Python 3.11 + FFT (NumPy) + audio loopback (BlackHole) + HID (hidapi)
- **Environment Management**: `mise` (tool versions, venv, task runner)
- **Audio Loopback**: BlackHole 2ch (macOS virtual audio driver)

## Planned Structure
- `src/`: Python source files (User preference)
- `moonlander_musicviz/`: Python package directory (from spec)
- `.mise.toml`: Tool and task configurations
- `requirements.txt`: Python dependencies
- `moonlander-musicviz-spec.md`: Detailed specification document
