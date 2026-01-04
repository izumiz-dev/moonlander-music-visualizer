"""List available audio devices and find BlackHole."""
import sounddevice as sd

def main():
    print("Available audio input devices:")
    print("-" * 60)
    
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        if d['max_input_channels'] > 0:
            name = d['name']
            channels = d['max_input_channels']
            sr = d['default_samplerate']
            
            marker = ""
            if "BlackHole" in name: marker = " <-- BLACKHOLE"
            elif "CABLE Output" in name: marker = " <-- VB-CABLE"
            elif "Stereo Mix" in name or "ステレオ ミキサー" in name: marker = " <-- STEREO MIX"
            
            if i == sd.default.device[0]:
                marker += " [DEFAULT]"
            
            print(f"[{i:2d}] {name:40s} | ch={channels} | sr={sr}")
            if marker:
                print(f"     {marker}")
    
    print("-" * 60)
    print("\nTo use this tool:")
    print("1. Set your system output to a Multi-Output device (Speakers + BlackHole)")
    print("2. Run: mise run run")
    print("   The script will auto-detect BlackHole as input device")

if __name__ == "__main__":
    main()

