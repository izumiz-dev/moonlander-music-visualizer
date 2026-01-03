"""
Packet Preview Simulator for Moonlander Music Visualizer.

Mode A: Direct visualization of packet data.
Does NOT replicate firmware logic - shows raw packet data for Python-side debugging.

For firmware-specific effects (smoothing, decay), use the actual keyboard.
"""
import math


class MoonlanderSimulator:
    """
    Simplified simulator that visualizes HID packet data directly.
    
    Purpose: Debug Python-side audio analysis and color calculations.
    NOT for: Debugging firmware rendering effects.
    """
    
    def __init__(self):
        self.points = self._generate_geometry()
        self.led_count = 72
        self.geometry = self._compute_geometry_stats()
        
    def _generate_geometry(self):
        """
        Official QMK Moonlander LED coordinates from keyboard.json.
        Source: zsa/qmk_firmware/keyboards/zsa/moonlander/keyboard.json
        """
        Y_SCALE = 2.0  # For PC display visibility
        
        qmk_coords = [
            # LEFT HALF (LED 0-35)
            (0, 4), (0, 20), (0, 36), (0, 52), (0, 68),      # Col 0
            (16, 3), (16, 19), (16, 35), (16, 51), (16, 67), # Col 1
            (32, 1), (32, 17), (32, 33), (32, 49), (32, 65), # Col 2
            (48, 0), (48, 16), (48, 32), (48, 48), (48, 64), # Col 3
            (64, 1), (64, 17), (64, 33), (64, 49), (64, 65), # Col 4
            (80, 3), (80, 19), (80, 35), (80, 51),           # Col 5
            (96, 4), (96, 20), (96, 36),                     # Col 6
            (88, 69), (100, 80), (112, 91), (108, 69),       # Thumb
            
            # RIGHT HALF (LED 36-71)
            (240, 4), (240, 20), (240, 36), (240, 52), (240, 68), # Col 6
            (224, 3), (224, 19), (224, 35), (224, 51), (224, 67), # Col 5
            (208, 1), (208, 17), (208, 33), (208, 49), (208, 65), # Col 4
            (192, 0), (192, 16), (192, 32), (192, 48), (192, 64), # Col 3
            (176, 1), (176, 17), (176, 33), (176, 49), (176, 65), # Col 2
            (160, 3), (160, 19), (160, 35), (160, 51),        # Col 1
            (144, 4), (144, 20), (144, 36),                   # Col 0
            (152, 69), (140, 80), (128, 91), (132, 69),       # Thumb
        ]
        
        assert len(qmk_coords) == 72
        return [{'x': x, 'y': y, 'y_display': int(y * Y_SCALE)} for x, y in qmk_coords]

    def _compute_geometry_stats(self):
        """Compute inner edge positions for wave visualization."""
        max_left_x = max(p['x'] for i, p in enumerate(self.points) if i < 36)
        min_right_x = min(p['x'] for i, p in enumerate(self.points) if i >= 36)
        return {'max_left_x': max_left_x, 'min_right_x': min_right_x}

    def hsv_to_rgb(self, h, s, v):
        """QMK-compatible HSV to RGB conversion (0-255 scale)."""
        # [Simulation Tweak] Boost saturation to mimic rich LED colors on screen
        s = min(255, int(s * 1.3))

        if s == 0:
            return (v, v, v)
        
        region = h // 43
        remainder = (h - (region * 43)) * 6
        
        p = (v * (255 - s)) >> 8
        q = (v * (255 - ((s * remainder) >> 8))) >> 8
        t = (v * (255 - ((s * (255 - remainder)) >> 8))) >> 8
        
        region = region % 6
        if region == 0: return (v, t, p)
        elif region == 1: return (q, v, p)
        elif region == 2: return (p, v, t)
        elif region == 3: return (p, q, v)
        elif region == 4: return (t, p, v)
        else: return (v, p, q)

    def update(self, packet_data):
        """
        Packet Preview Mode: Direct visualization of packet data.
        
        Shows what the HOST is sending, not how firmware renders it.
        Useful for debugging audio analysis and color calculations.
        """
        leds = []
        
        # Extract packet values (0-255)
        bass = packet_data.get('bass', 0)
        mid = packet_data.get('mid', 0)
        treble = packet_data.get('treble', 0)
        
        hue_bass = packet_data.get('hue_bass', 0)
        hue_mid = packet_data.get('hue_mid', 85)
        hue_treble = packet_data.get('hue_treble', 170)
        saturation = packet_data.get('saturation', 255)
        master_gain = packet_data.get('master_gain', 255)
        
        # Simple radial wave visualization based on band levels
        # Inner LEDs = bass, Middle = mid, Outer = treble
        for i in range(self.led_count):
            p = self.points[i]
            
            # Calculate distance from inner edge (0 = inner, 1 = outer)
            if i < 36:
                dx = self.geometry['max_left_x'] - p['x']
            else:
                dx = p['x'] - self.geometry['min_right_x']
            
            # Normalize distance (max distance ≈ 112)
            max_dist = 112.0
            norm_dist = min(dx / max_dist, 1.0)
            
            # Blend based on distance: inner=bass, mid=mid, outer=treble
            if norm_dist < 0.33:
                # Inner zone: Bass dominant
                blend = norm_dist / 0.33
                brightness = int(bass * (1 - blend * 0.5) + mid * blend * 0.5)
                hue = hue_bass
            elif norm_dist < 0.66:
                # Mid zone: Mid dominant
                blend = (norm_dist - 0.33) / 0.33
                brightness = int(mid * (1 - blend * 0.5) + treble * blend * 0.5)
                hue = hue_mid
            else:
                # Outer zone: Treble dominant
                brightness = treble
                hue = hue_treble
            
            # Apply master gain
            brightness = (brightness * master_gain) // 255
            
            # Convert to RGB
            r, g, b = self.hsv_to_rgb(hue, saturation, brightness)
            leds.append((r, g, b))
        
        return leds

    def get_debug_state(self):
        """Returns detailed debug info for audio analysis optimization."""
        return {
            'mode': 'packet_preview',
            'firmware_emulation': False,
            'last_packet': getattr(self, '_last_packet', {}),
            'geometry': self.geometry,
        }
    
    def log_packet(self, packet_data):
        """
        Log packet data for debugging audio analysis.
        Call this before update() to capture raw packet values.
        """
        self._last_packet = {
            # Audio levels
            'bass': packet_data.get('bass', 0),
            'mid': packet_data.get('mid', 0),
            'treble': packet_data.get('treble', 0),
            'loudness_rms': packet_data.get('loudness_rms', 0),
            
            # Beat detection
            'beat': packet_data.get('beat', 0),
            'perimeter_sparkle': packet_data.get('perimeter_sparkle', 0),
            
            # Color settings
            'hue_bass': packet_data.get('hue_bass', 0),
            'hue_mid': packet_data.get('hue_mid', 0),
            'hue_treble': packet_data.get('hue_treble', 0),
            'saturation': packet_data.get('saturation', 255),
            'master_gain': packet_data.get('master_gain', 255),
            
            # Derived metrics
            'bass_to_rms_ratio': (
                packet_data.get('bass', 0) / max(packet_data.get('loudness_rms', 1), 1)
            ),
            'dynamic_range': max(
                packet_data.get('bass', 0),
                packet_data.get('mid', 0),
                packet_data.get('treble', 0)
            ) - min(
                packet_data.get('bass', 0),
                packet_data.get('mid', 0),
                packet_data.get('treble', 0)
            ),
        }
        return self._last_packet
