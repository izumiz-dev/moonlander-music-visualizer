import time
import colorsys
import collections
import random
import math
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.console import Console, Group
from rich.text import Text
from rich.align import Align
from rich.style import Style
from rich.live import Live
from rich.columns import Columns

class TerminalDashboard:
    """
    Sonic HUD v2.5 - Zen Minimal.
    Features:
    - Borderless, clean aesthetic.
    - Central Spectrum Visualizer (Density Optimized).
    - Compact footer info.
    - Track Info display.
    """
    
    def __init__(self):
        self.console = Console()
        self.layout = Layout()
        
        # History for Sparkline (last 50 frames)
        self.loudness_history = collections.deque([0.0] * 50, maxlen=50)
        
        # Text animation state
        self.text_phase = 0.0
        self.marquee_offset = 0
        self.last_track_name = ""
        
        # Split layout: Header / Body / Footer
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="body"), # Main Visualizer
            Layout(name="footer", size=5)
        )

    def _hue_to_hex(self, hue_255, sat_255=255):
        r, g, b = colorsys.hsv_to_rgb(hue_255 / 255.0, sat_255 / 255.0, 1.0)
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

    def _get_spectrum_visualizer(self, features, colors, num_bars=12, height=16):
        """
        Generate a DENSE & TALL ASCII Spectrum Analyzer.
        """
        c_b, c_m, c_t = colors
        
        # 1. Interpolate Bands
        b, m, t = features.get('bass', 0), features.get('mid', 0), features.get('treble', 0)
        bars = []
        for i in range(num_bars):
            pos = i / max(1, num_bars - 1)
            if pos < 0.33:
                val = b * (1.0 - (pos / 0.33) * 0.15) 
            elif pos < 0.66:
                p = (pos - 0.33) / 0.33
                val = b*(1-p)*0.3 + m*p + m*(1-p)*0.5
            else:
                p = (pos - 0.66) / 0.34
                val = m*(1-p)*0.3 + t*p*1.3
            bars.append(val)
        
        # 2. Render
        rows = []
        chars = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
        
        for y in range(height-1, -1, -1):
            row_txt = Text("")
            thresh = y / height
            
            for i, val in enumerate(bars):
                # Gradient
                pos = i / max(1, num_bars - 1)
                if pos < 0.33: col = c_b
                elif pos < 0.66: col = c_m
                else: col = c_t
                
                # Bar Logic
                if val > thresh + 0.1: 
                    char = "██" # Double width for solidity
                elif val > thresh: 
                    c = chars[min(int((val-thresh)*10), 8)]
                    char = c + c
                else: 
                    char = "  "
                
                # Particles (more subtle)
                if char == "  ":
                    if features.get('snare', 0) > 0.5 and random.random() > 0.95:
                        char = ".."
                        col = "white"
                    elif features.get('hihat', 0) > 0.5 and random.random() > 0.98:
                        char = "::"
                        col = c_t

                # Minimal spacing
                row_txt.append(char + " ", style=col)
            rows.append(row_txt)
            
        return Align.center(Group(*rows), vertical="middle")

    def _get_mini_bar(self, val, color, width=10):
        w = int(val * width)
        bar = "█" * w + "░" * (width - w)
        return Text(bar, style=color)

    def update(self, features, palette_name, device_name, track_name, hues=(0, 0, 0), saturation=255):
        """Update and return the layout."""
        
        h_b, h_m, h_t = hues
        c_b = self._hue_to_hex(h_b, saturation)
        c_m = self._hue_to_hex(h_m, saturation)
        c_t = self._hue_to_hex(h_t, saturation)
        
        # Header (Minimal + Pulsating Track Info)
        left_text = Text.assemble(
            (" MOONLANDER ", "bold black on white"),
            (f"  SCENE: {palette_name}  ", f"bold white on {c_t}")
        )
        
        # Pulsating color between Bass and Treble hues
        self.text_phase = (self.text_phase + 0.05) % (math.pi * 2)
        blend = (math.sin(self.text_phase) + 1.0) / 2.0
        h_mix = int(h_b * (1.0 - blend) + h_t * blend)
        c_mix = self._hue_to_hex(h_mix, saturation)

        # Marquee Logic
        display_width = 50
        track_display = track_name
        
        if track_name != self.last_track_name:
            self.marquee_offset = 0
            self.last_track_name = track_name
            
        if len(track_name) > display_width:
            # Add padding for loop
            padded = track_name + "   ***   " 
            # Scroll speed control (0.2 chars per frame approx)
            idx = int(self.marquee_offset) % len(padded)
            
            # Slice with wrap-around
            track_display = (padded * 2)[idx : idx + display_width]
            
            self.marquee_offset += 0.2
            
        right_text = Text(f" ♫ {track_display} ", style=f"bold {c_mix}")

        header_grid = Table.grid(expand=True)
        header_grid.add_column(justify="left")
        header_grid.add_column(justify="right")
        header_grid.add_row(left_text, right_text)

        self.layout["header"].update(Align.center(header_grid, vertical="middle"))

        # Body: Spectrum Visualizer
        center_width = self.console.size.width * 0.6
        num_bars = int(center_width // 3)
        num_bars = max(8, min(num_bars, 40)) 
        
        # Use full height of the body panel effectively
        spectrum = self._get_spectrum_visualizer(features, (c_b, c_m, c_t), num_bars=num_bars, height=18)
        self.layout["body"].update(spectrum) # No Panel border!

        # Footer: Compact Info
        footer_table = Table.grid(expand=True, padding=(0, 2))
        footer_table.add_column("L", justify="right")
        footer_table.add_column("V", justify="left")
        footer_table.add_column("L", justify="right")
        footer_table.add_column("V", justify="left")
        footer_table.add_column("L", justify="right")
        footer_table.add_column("V", justify="left")
        
        footer_table.add_row(
            Text("BASS", style=c_b), self._get_mini_bar(features.get('bass',0), c_b),
            Text("MID", style=c_m),  self._get_mini_bar(features.get('mid',0), c_m),
            Text("TREB", style=c_t), self._get_mini_bar(features.get('treble',0), c_t)
        )
        footer_table.add_row(
            Text("RMS", style="white"), self._get_mini_bar(features.get('loudness_rms',0), "white"),
            Text("GAIN", style="dim"), Text(f"{features.get('bass',0)*0.15 + 1.0:.2f}x", style="dim"),
            Text("SAT", style="dim"),  Text(f"{saturation/255.0:.2f}x", style="dim")
        )
        
        self.layout["footer"].update(Align.center(footer_table, vertical="middle"))

        return self.layout