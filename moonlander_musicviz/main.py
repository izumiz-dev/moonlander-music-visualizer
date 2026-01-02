"Main CLI: capture audio from BlackHole → analyze → send to Moonlander."
import time
import signal
import argparse
import sounddevice as sd
import numpy as np
from .audio_analyzer import AudioAnalyzer
from .hid_sender import HIDSender

def find_blackhole_device():
    """Find BlackHole input device index."""
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        if "BlackHole" in d["name"] and d["max_input_channels"] > 0:
            return i
    
    raise RuntimeError(
        "BlackHole device not found.\n"
        "Please:\n"
        "  1. Install BlackHole: brew install blackhole-2ch\n"
        "  2. Restart your Mac\n"
        "  3. Configure a Multi-Output device in Audio MIDI Setup\n"
        "  4. Set it as system output\n"
    )

def main():
    """Main loop: capture → analyze → send."""
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--screen", action="store_true", help="Sync colors with screen content")
    args = parser.parse_args()

    print("[*] Moonlander Music Visualizer (macOS)")
    if args.screen:
        print("[*] Mode: Screen Color Sync")
    print("[*] Finding BlackHole device...")
    
    try:
        device_id = find_blackhole_device()
        device_name = sd.query_devices()[device_id]['name']
        print(f"[+] Using device: {device_name}")
    except RuntimeError as e:
        print(f"[-] Error: {e}")
        return
    
    print("[*] Opening QMK Raw HID...")
    try:
        sender = HIDSender()
    except RuntimeError as e:
        print(f"[-] Error: {e}")
        return
    
    print("[*] Starting audio capture...")
    
    sr = 48000
    hop = 1024
    analyzer = AudioAnalyzer(sr=sr, nfft=2048, hop=hop)
    
    # Import new modules
    from .dashboard import TerminalDashboard
    from .palettes import PALETTES, PALETTE_NAMES
    from rich.live import Live
    
    if args.screen:
        from .screen_analyzer import ScreenAnalyzer
        screen_analyzer = ScreenAnalyzer()
    
    dashboard = TerminalDashboard()
    
    frame_count = 0
    update_rate_hz = 30
    update_interval = 1.0 / update_rate_hz
    last_update = time.time()
    
    # === Visual State ===
    hue_rotation = 0.0
    palette_index = 0
    last_palette_switch = time.time()
    current_p_name = PALETTE_NAMES[palette_index]
    
    def signal_handler(sig, frame):
        # We don't print here to avoid breaking the dashboard layout
        sender.close()
        exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    with sd.InputStream(device=device_id, channels=2, samplerate=sr,
                        blocksize=hop, dtype='float32') as stream:
        
        # Use Rich Live Display
        with Live(dashboard.layout, refresh_per_second=30, screen=True) as live:
            while True:
                # Read audio frame
                audio, _ = stream.read(hop)
                features = analyzer.update(audio)
                
                # Send to keyboard at fixed rate (~30 Hz)
                now = time.time()
                if now - last_update >= update_interval:
                    
                    saturation = 255
                    if args.screen:
                        h_b, h_m, h_t, saturation = screen_analyzer.get_palette()
                        current_p_name = "Screen Sync"
                    else:
                        # --- Palette Switching Logic (Musical Trigger) ---
                        # Calculate a weighted "impact score"
                        # Beat has the highest impact, followed by Bass and Treble peaks.
                        impact_score = (
                            features.get('beat', 0) * 0.5 +
                            features.get('bass', 0) * 0.25 +
                            features.get('treble', 0) * 0.25
                        )
                        
                        time_since_last = now - last_palette_switch
                        
                        # Triggers:
                        # 1. High impact event (Beat + High energy) - 3s cooldown
                        # 2. Extremely loud peak - 6s cooldown
                        # 3. Fallback: 30s if the song is very quiet or static
                        is_impact = (impact_score > 0.82) and (time_since_last > 3.0)
                        is_peak   = (features.get('loudness_peak', 0) > 0.95) and (time_since_last > 6.0)
                        is_timeout = (time_since_last > 30.0)
                        
                        if is_impact or is_peak or is_timeout:
                            palette_index = (palette_index + 1) % len(PALETTE_NAMES)
                            current_p_name = PALETTE_NAMES[palette_index]
                            last_palette_switch = now
                        
                        active_palette = PALETTES[current_p_name]
                        base_hues = active_palette["hues"]
                        
                        # --- Dynamic Hue Rotation (EDM Style) ---
                        speed = 0.5 + (features['loudness_rms'] * 2.0)
                        if features['beat'] > 0.8:
                            hue_rotation += 5.0
                        hue_rotation = (hue_rotation + speed) % 255.0
                        
                        h_b = int((base_hues[0] + hue_rotation * 0.1) % 255)
                        h_m = int((base_hues[1] + hue_rotation * 0.5) % 255)
                        h_t = int((base_hues[2] + hue_rotation * 1.0) % 255)

                    # Send Packet via HID
                    sender.send_packet(features, hue_bass=h_b, hue_mid=h_m, hue_treble=h_t, saturation=saturation)
                    
                    # Update Dashboard
                    live.update(dashboard.update(features, current_p_name, device_name, hues=(h_b, h_m, h_t)))
                    
                    last_update = now
                    frame_count += 1

if __name__ == "__main__":
    main()
