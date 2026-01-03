"Main CLI: capture audio from BlackHole → analyze → send to Moonlander."
import time
import signal
import argparse
import random
import sounddevice as sd
import numpy as np
from .audio_analyzer import AudioAnalyzer
from .hid_sender import HIDSender
from .track_info import TrackInfo

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
    track_info = TrackInfo()
    current_track_name = "Waiting..."
    last_track_check = 0.0
    
    frame_count = 0
    update_rate_hz = 30
    update_interval = 1.0 / update_rate_hz
    last_update = time.time()
    
    # === Visual State ===
    hue_rotation = 0.0
    palette_index = 0
    last_palette_switch = time.time()
    current_p_name = PALETTE_NAMES[palette_index]
    
    # Rhythm Modulation State (Smoothing/Decay)
    mod_master_gain = 1.0
    mod_saturation = 1.0
    mod_treble_boost = 0.0
    
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
                dt = now - last_update
                
                if dt >= update_interval:
                    
                    # Check Track Info (every 5.0s)
                    if now - last_track_check > 5.0:
                        current_track_name = track_info.get_current_track()
                        last_track_check = now

                    # --- Rhythm Modulation (Pre-Processing) ---
                    # Tuned down for subtlety (Less is more)
                    
                    # 1. Kick -> Master Gain (Very subtle pulse)
                    if features.get('kick', 0) > 0.5:
                        mod_master_gain = 1.15 
                    else:
                        mod_master_gain = max(1.0, mod_master_gain - 2.0 * dt) # Faster decay
                    
                    # 2. Snare -> Saturation (Mild desaturation, not full bleach)
                    if features.get('snare', 0) > 0.5:
                        mod_saturation = 0.7 
                    else:
                        mod_saturation = min(1.0, mod_saturation + 2.5 * dt) # Fast recovery
                    
                    # 3. Hi-Hat -> Treble Boost (Tiny sparkle)
                    if features.get('hihat', 0) > 0.5:
                        mod_treble_boost = 0.2
                    else:
                        mod_treble_boost = max(0.0, mod_treble_boost - 2.0 * dt)
                    
                    # Apply Modulations to Features
                    # Master Gain is handled by sending it in the packet, 
                    # but here we can modulate the band levels directly too.
                    features['bass']   = np.clip(features['bass'] * mod_master_gain, 0, 1.0)
                    features['treble'] = np.clip(features['treble'] + mod_treble_boost, 0, 1.0)
                    
                    # --- Chorus Boost & Saturation Preservation (The Master's Touch) ---
                    is_chorus = features.get('is_chorus', False)
                    
                    if args.screen:
                        h_b, h_m, h_t, screen_sat = screen_analyzer.get_palette()
                        current_p_name = "Screen Sync"
                        final_saturation = int(screen_sat * mod_saturation)
                    else:
                        # --- Palette Switching Logic (Expert Tuned) ---
                        impact_score = (
                            features.get('kick', 0) * 0.6 + 
                            features.get('bass', 0) * 0.2 +
                            features.get('treble', 0) * 0.2
                        )
                        
                        time_since_last = now - last_palette_switch
                        
                        # Trigger: High impact or 45s timeout
                        if (impact_score > 0.85 and time_since_last > 4.0) or (time_since_last > 45.0):
                            # Transition: "Blackout" effect (Lumiere's scene change)
                            mod_master_gain = 0.0 # Force instant darkness
                            
                            # Random selection (excluding current)
                            others = [n for n in PALETTE_NAMES if n != current_p_name]
                            current_p_name = random.choice(others)
                            last_palette_switch = now

                        active_palette = PALETTES[current_p_name]
                        base_hues = active_palette["hues"]
                        p_sat = active_palette["saturation"]
                        p_rot = active_palette["rotation_allowed"]
                        
                        # --- Dynamic Hue Rotation ---
                        rot_speed_mult = 1.5 if is_chorus else 1.0
                        
                        if p_rot:
                            speed = (0.5 + (features['loudness_rms'] * 2.0)) * rot_speed_mult
                            if features['kick'] > 0.5:
                                hue_rotation += 3.0
                            hue_rotation = (hue_rotation + speed) % 255.0
                        else:
                            # Subdued "shimmer" for chic palettes
                            hue_rotation = (hue_rotation + 0.1) % 255.0
                        
                        h_b = int((base_hues[0] + hue_rotation * 0.1) % 255)
                        h_m = int((base_hues[1] + hue_rotation * 0.5) % 255)
                        h_t = int((base_hues[2] + hue_rotation * 1.0) % 255)
                        
                        # Combine Palette Base Saturation with Rhythm Modulation
                        # Vivid Overdrive: No more 220 limit. Pure color at all times.
                        if is_chorus:
                            mod_master_gain = 1.2 # Overdrive brightness
                            final_saturation = 255 
                        else:
                            final_saturation = int(p_sat * mod_saturation)

                    # Send Packet via HID
                    # We also send the modulated master_gain via features['master_gain'] if needed, 
                    # but modulating band values directly is often more predictable.
                    
                    # Update master gain in features for the packet
                    features['master_gain'] = np.clip(mod_master_gain, 0.0, 1.0) # Actually handled by bands, but kept for logic
                    
                    sender.send_packet(features, hue_bass=h_b, hue_mid=h_m, hue_treble=h_t, saturation=final_saturation)
                    
                    # Update Dashboard
                    live.update(dashboard.update(features, current_p_name, device_name, current_track_name, hues=(h_b, h_m, h_t), saturation=final_saturation))
                    
                    last_update = now
                    frame_count += 1

if __name__ == "__main__":
    main()
