import mss
import numpy as np
import colorsys

class ScreenAnalyzer:
    """
    Captures screen content and calculates dominant colors
    for the music visualizer.
    """
    def __init__(self):
        self.sct = mss.mss()
        # Monitor 1 is usually the primary display
        self.monitor = self.sct.monitors[1]

    def get_palette(self):
        """
        Capture screen and return (hue_bass, hue_mid, hue_treble, saturation).
        Hues and saturation are 0-255 integers.
        """
        try:
            # Capture the screen
            sct_img = self.sct.grab(self.monitor)
            
            # Convert to numpy array. Format is BGRA.
            # Downsample for performance
            img = np.array(sct_img)[::20, ::20, :3]
            
            # Reshape to a list of pixels (N, 3)
            pixels = img.reshape(-1, 3)
            
            # Convert all pixels to HSV to find the most "vivid" one
            # We normalize to 0-1 for colorsys
            r, g, b = pixels[:, 2]/255.0, pixels[:, 1]/255.0, pixels[:, 0]/255.0
            
            # Finding the most vivid pixel.
            # For performance, let's just use the average but boost it aggressively, 
            # or better: pick the pixel with the highest (Saturation * Value).
            
            # Simple but effective: Calculate mean BGR first
            avg_bgr = np.mean(img, axis=(0, 1))
            b, g, r = avg_bgr[0], avg_bgr[1], avg_bgr[2]
            h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
            
            base_hue = int(h * 255)
            
            # AGGRESSIVE VIVID LOGIC:
            # If there's any detectable color (s > 0.01), force saturation to MAX (255).
            # This ignores the "paleness" of the screen and gives you pure colors.
            if s > 0.01:
                saturation = 255
            else:
                saturation = 0
            
            # Create an analogous palette
            offset = 21
            
            h_b = (base_hue - offset) % 255
            h_m = base_hue
            h_t = (base_hue + offset) % 255
            
            return int(h_b), int(h_m), int(h_t), saturation
            
        except Exception as e:
            # Fallback on error
            print(f"[Screen] Capture error: {e}")
            return 160, 40, 220, 255
