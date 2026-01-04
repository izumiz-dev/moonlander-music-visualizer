"QMK Raw HID sender: find device + send 32-byte packets."
import hid
import struct

USAGE_PAGE = 0xFF60
USAGE_ID = 0x61
MAGIC = 0x4D
VERSION = 0x01

class HIDSender:
    """
    Finds and communicates with a QMK Raw HID device.
    """
    
    def __init__(self, vendor_id=None, product_id=None):
        """
        Find and open a QMK Raw HID device.
        
        If vendor_id/product_id are None, searches by Usage Page/ID (default).
        """
        self.dev = None
        self.vendor_id = vendor_id
        self.product_id = product_id
        self._find_and_open()
    
    def _find_and_open(self):
        """Search for QMK Raw HID interface and open it."""
        devices = hid.enumerate()
        
        for d in devices:
            # Filter by Usage Page/ID if specified
            if self.vendor_id is not None and self.product_id is not None:
                if d.get('vendor_id') != self.vendor_id or d.get('product_id') != self.product_id:
                    continue
            
            # Try matching by Usage Page/ID
            if d.get('usage_page') == USAGE_PAGE and d.get('usage') == USAGE_ID:
                try:
                    self.dev = hid.device()
                    self.dev.open_path(d['path'])
                    print(f"[HID] Opened: {d['manufacturer_string']} {d['product_string']}")
                    return
                except Exception as e:
                    print(f"[HID] Failed to open {d['path']}: {e}")
                    continue
        
        raise RuntimeError(
            "QMK Raw HID device not found.\n"
            "Ensure Moonlander is connected and firmware is flashed with RAW_ENABLE=yes."
        )
    
    def send_packet(self, audio_features, hue_bass=160, hue_mid=40, hue_treble=220, saturation=255):
        """
        Send a music visualizer packet to the Moonlander.
        
        Args:
            audio_features: dict with keys bass, mid, treble, loudness_rms, loudness_peak, beat (all 0–1)
            hue_*: hue values (0–255) for each band
            saturation: global saturation (0-255)
        
        Returns:
            True if successful, False on error
        """
        if self.dev is None:
            return False
        
        try:
            # Build 32-byte packet
            pkt = bytearray(32)
            
            # Map loudness to master gain with a square curve for better contrast
            # Quiet parts (loudness ~0.2) will be very dim (~10+10=20)
            # Loud parts (loudness ~1.0) will be max brightness (10+245=255)
            gain_curve = audio_features['loudness_rms'] ** 2.0
            master_gain = int(10 + (gain_curve * 245))
            
            pkt[0] = MAGIC
            pkt[1] = VERSION
            pkt[2] = 0x05  # flags: enable=1, strobe_enable=0, safety_limit=1, debug=0
            pkt[3] = master_gain
            
            # Audio features: convert 0–1 to 0–255
            pkt[4] = int(audio_features['loudness_rms'] * 255)
            pkt[5] = int(audio_features['loudness_peak'] * 255)
            pkt[6] = int(audio_features['bass'] * 255)
            pkt[7] = int(audio_features['mid'] * 255)
            pkt[8] = int(audio_features['treble'] * 255)
            pkt[9] = int(audio_features['beat'] * 255)
            
            # Hues and colors
            pkt[10] = hue_bass
            pkt[11] = hue_mid
            pkt[12] = hue_treble
            pkt[13] = saturation
            pkt[14] = 128      # fx_speed (unused)
            pkt[15] = int(audio_features['beat'] * 255)  # shockwave_strength
            pkt[16] = int(audio_features['treble'] * 200)  # perimeter_sparkle (0–200)
            pkt[17] = 30       # beat_refractory_ms (30 * 4 = 120ms)
            
            # Pad rest with 0
            for i in range(18, 32):
                pkt[i] = 0
            
            # Windows HID compatibility: 
            # On Windows, the first byte must be the Report ID (0x00 for none).
            # This makes the packet 33 bytes.
            import os
            if os.name == 'nt':
                self.dev.write([0x00] + list(pkt))
            else:
                self.dev.write(list(pkt))
            return True
        
        except Exception as e:
            print(f"[HID] Write failed: {e}")
            return False
    
    def close(self):
        """Close the HID device."""
        if self.dev:
            self.dev.close()
            self.dev = None
