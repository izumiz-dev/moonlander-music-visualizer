"Main CLI: capture audio from BlackHole → analyze → send to Moonlander."
import time
import signal
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
    
    print("[*] Moonlander Music Visualizer (macOS)")
    print("[*] Finding BlackHole device...")
    
    try:
        device_id = find_blackhole_device()
        print(f"[+] Using device: {sd.query_devices()[device_id]['name']}")
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
    
    frame_count = 0
    update_rate_hz = 30
    update_interval = 1.0 / update_rate_hz
    last_update = time.time()
    
    # === Visual State ===
    hue_rotation = 0.0
    palette_index = 0
    last_palette_switch = time.time()
    
    # Palettes: (Bass, Mid, Treble)
    palettes = [
        {"name": "Cyberpunk", "hues": (160, 200, 240)}, # Blue / Purple / Pink
        {"name": "NeonPop",   "hues": (230, 140, 20)},  # Hot Pink / Cyan / Orange (K-Pop style)
        {"name": "BlackGold", "hues": (30,  45,  60)},  # Deep Orange / Gold / Yellow
        {"name": "EDM Arena", "hues": (170, 0,   120)}, # Cyan / Red / Green
        {"name": "Magma",     "hues": (0,   30,  60)},  # Red / Orange / Yellow
    ]

    def signal_handler(sig, frame):
        print("\n[*] Shutting down...")
        sender.close()
        exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    with sd.InputStream(device=device_id, channels=2, samplerate=sr,
                        blocksize=hop, dtype='float32') as stream:
        print("[+] Capturing and streaming...")
        print("[*] Press Ctrl+C to stop")
        
        while True:
            # Read audio frame
            audio, _ = stream.read(hop)
            features = analyzer.update(audio)
            
            # Send to keyboard at fixed rate (~30 Hz)
            now = time.time()
            if now - last_update >= update_interval:
                
                # --- Palette Switching Logic ---
                if now - last_palette_switch > 15.0 or (features['beat'] > 0.90 and now - last_palette_switch > 5.0):
                    palette_index = (palette_index + 1) % len(palettes)
                    last_palette_switch = now
                
                active_palette = palettes[palette_index]
                base_hues = active_palette["hues"]
                
                # --- Dynamic Hue Rotation (EDM Style) ---
                # Rotate normal speed, but JUMP on beats
                speed = 0.5 + (features['loudness_rms'] * 2.0)
                
                # If a strong beat hits, jump hue slightly to create glitch/energy effect
                if features['beat'] > 0.8:
                    hue_rotation += 5.0
                
                hue_rotation = (hue_rotation + speed) % 255.0
                
                h_b = int((base_hues[0] + hue_rotation * 0.1) % 255) # Bass stays relatively grounded
                h_m = int((base_hues[1] + hue_rotation * 0.5) % 255)
                h_t = int((base_hues[2] + hue_rotation * 1.0) % 255) # Treble spins fast

                # Send Packet
                sender.send_packet(features, hue_bass=h_b, hue_mid=h_m, hue_treble=h_t)
                last_update = now
                frame_count += 1
                
                # Immediate log on beat
                if features['beat'] > 0.5:
                     print(f"!!! BEAT !!! bass={features['bass']:.2f}")

                # Log Treble Laser Beam (High frequency activity) - Rate limited
                # Firmware "Laser Beam" effect triggers on treble intensity.
                if features['treble'] > 0.8:
                    if not hasattr(main, 'last_laser_log'): main.last_laser_log = 0
                    if now - main.last_laser_log > 0.25:  # Max 4 times/sec to avoid spam
                        print(f"=== LASER BEAM === treble={features['treble']:.2f}")
                        main.last_laser_log = now

                # Status every 30 frames (~1 sec at 30Hz)
                if frame_count % 30 == 0:
                    print(
                        f"[{frame_count:6d}] "
                        f"bass={features['bass']:.2f} "
                        f"mid={features['mid']:.2f} "
                        f"treble={features['treble']:.2f} "
                        f"beat={features['beat']:.2f} "
                        f"bpm={features.get('bpm', 0):.1f} "
                        f"[{active_palette['name']}]"
                    )

if __name__ == "__main__":
    main()
