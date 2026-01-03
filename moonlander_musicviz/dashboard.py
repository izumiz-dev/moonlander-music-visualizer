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
    
    def __init__(self, simulator_enabled=False):
        self.simulator_enabled = simulator_enabled
        self.console = Console()
        self.layout = Layout()
        
        # History for Sparkline (last 50 frames)
        self.loudness_history = collections.deque([0.0] * 50, maxlen=50)
        
        # Text animation state
        self.text_phase = 0.0
        self.marquee_offset = 0
        self.last_track_name = ""
        
        if simulator_enabled:
            # Simulator mode with expanded debug info
            self.layout.split(
                Layout(name="header", size=3),
                Layout(name="body"),  # Simulator view
                Layout(name="footer", size=8)  # Expanded debug log
            )
        else:
            self.layout.split(
                Layout(name="header", size=3),
                Layout(name="body"), # Spectrum Visualizer
                Layout(name="footer", size=10)
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

    def update(self, features, palette_name, device_name, track_name, hues=(0, 0, 0), saturation=255, leds=None, debug_state=None):
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
        
        if self.simulator_enabled:
            # Body: Enlarged Simulator (Square-ish chips)
            sim_view = self._render_simulator(leds, debug_state)
            self.layout["body"].update(Align.center(sim_view, vertical="middle"))

            # Footer: Expanded debug log for audio analysis
            debug_table = Table.grid(expand=True, padding=(0, 2))
            debug_table.add_column("L1", justify="right")
            debug_table.add_column("V1", justify="left")
            debug_table.add_column("L2", justify="right")
            debug_table.add_column("V2", justify="left")
            debug_table.add_column("L3", justify="right")
            debug_table.add_column("V3", justify="left")
            debug_table.add_column("L4", justify="right")
            debug_table.add_column("V4", justify="left")
            
            # Row 1: Main audio levels
            debug_table.add_row(
                Text("BASS", style=c_b), Text(f"{features.get('bass',0):.2f}", style=c_b),
                Text("MID", style=c_m), Text(f"{features.get('mid',0):.2f}", style=c_m),
                Text("TREB", style=c_t), Text(f"{features.get('treble',0):.2f}", style=c_t),
                Text("RMS", style="white"), Text(f"{features.get('loudness_rms',0):.2f}", style="white"),
            )
            
            # Row 2: Beat detection and ratios
            beat = features.get('beat', 0)
            snare = features.get('perimeter_sparkle', 0)
            rms = features.get('loudness_rms', 0.01)
            bass = features.get('bass', 0)
            
            bass_rms_ratio = bass / max(rms, 0.01)
            dynamic_range = max(bass, features.get('mid', 0), features.get('treble', 0)) - \
                           min(bass, features.get('mid', 0), features.get('treble', 0))
            
            debug_table.add_row(
                Text("BEAT", style="yellow"), Text(f"{beat:.2f}", style="yellow"),
                Text("SNARE", style="magenta"), Text(f"{snare:.2f}", style="magenta"),
                Text("B/RMS", style="cyan"), Text(f"{bass_rms_ratio:.2f}", style="cyan"),
                Text("DynRng", style="green"), Text(f"{dynamic_range:.2f}", style="green"),
            )
            
            # Row 3: Color info
            debug_table.add_row(
                Text("HueBass", style=c_b), Text(f"{h_b}", style=c_b),
                Text("HueMid", style=c_m), Text(f"{h_m}", style=c_m),
                Text("HueTreb", style=c_t), Text(f"{h_t}", style=c_t),
                Text("SAT", style="dim"), Text(f"{saturation}", style="dim"),
            )
            
            self.layout["footer"].update(Align.center(debug_table, vertical="middle"))
        else:
            # Body: Spectrum Visualizer
            center_width = self.console.size.width * 0.6
            num_bars = int(center_width // 3)
            num_bars = max(8, min(num_bars, 40)) 
            spectrum = self._get_spectrum_visualizer(features, (c_b, c_m, c_t), num_bars=num_bars, height=18)
            self.layout["body"].update(spectrum)

            # Footer: Compact Info with Bars
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

    def _render_simulator(self, leds, debug_state=None):
        """
        Renders the 72 LEDs using the ACTUAL QMK Moonlander LED index layout.
        
        QMK Layout (columns top-to-bottom):
        LEFT (0-35):  Col0(0-4), Col1(5-9), Col2(10-14), Col3(15-19), Col4(20-24), Col5(25-28), Col6(29-31), Thumb(32-35)
        RIGHT (36-71): Col6(36-40), Col5(41-45), Col4(46-50), Col3(51-55), Col2(56-60), Col1(61-64), Col0(65-67), Thumb(68-71)
        """
        if not leds: return Text("No Data")
        
        def get_style(idx):
            if idx < 0 or idx >= len(leds): return "black"
            r, g, b = leds[idx]
            return f"rgb({r},{g},{b})"
        
        KEY_F = "██████"
        KEY_E = "      "
        
        rows_txt = []
        
        # QMK LED index lookup tables
        # Left: 7 columns (0-6), each with varying number of rows
        # Column indices store LEDs from top (row0) to bottom (row4)
        left_cols = [
            [0, 1, 2, 3, 4],      # Col 0 (outer, X=0)
            [5, 6, 7, 8, 9],      # Col 1
            [10, 11, 12, 13, 14], # Col 2
            [15, 16, 17, 18, 19], # Col 3
            [20, 21, 22, 23, 24], # Col 4
            [25, 26, 27, 28],     # Col 5 (4 keys)
            [29, 30, 31],         # Col 6 (inner, 3 keys)
        ]
        left_thumb = [32, 33, 34, 35]
        
        # Right: reversed column order (outer first in array)
        right_cols = [
            [36, 37, 38, 39, 40], # Col 6 (outer, X=240)  
            [41, 42, 43, 44, 45], # Col 5
            [46, 47, 48, 49, 50], # Col 4
            [51, 52, 53, 54, 55], # Col 3
            [56, 57, 58, 59, 60], # Col 2
            [61, 62, 63, 64],     # Col 1 (4 keys)
            [65, 66, 67],         # Col 0 (inner, 3 keys)
        ]
        right_thumb = [68, 69, 70, 71]
        
        # Render main grid rows (0-4)
        for row in range(5):
            for h in range(2):  # 2 text lines per row
                t = Text("")
                
                # LEFT HALF: Col 0 (outer) -> Col 6 (inner)
                for col_idx in range(7):
                    col = left_cols[col_idx]
                    if row < len(col):
                        t.append(KEY_F, style=get_style(col[row]))
                    else:
                        t.append(KEY_E)
                    t.append(" ")
                
                t.append("      ")  # Center gap
                
                # RIGHT HALF: Col 0 (inner) -> Col 6 (outer)
                # We need to reverse to show inner-to-outer visually
                for col_idx in range(6, -1, -1):
                    col = right_cols[col_idx]
                    if row < len(col):
                        t.append(KEY_F, style=get_style(col[row]))
                    else:
                        t.append(KEY_E)
                    t.append(" ")
                
                rows_txt.append(t)
            rows_txt.append(Text(""))
        
        # Thumb Cluster - Based on actual Moonlander layout (see photo)
        # Red key (32/68) is outermost, piano keys (33-35/69-71) form "ハ" shape inward
        #
        # Left half visual (from outer to inner):
        #   Row1: [Red32]  [Piano33]
        #   Row2:          [Piano34]
        #   Row3:             [Piano35]
        #
        # In code terms: columns 4-6 (from outer=4 to inner=6)
        
        # Row 1: Red key + first piano key (side by side)
        for h in range(2):
            t = Text("")
            # Left: Red at col4, Piano33 at col5
            t.append((KEY_E + " ") * 4)
            t.append(KEY_F, style=get_style(32))
            t.append(" ")
            t.append(KEY_F, style=get_style(33))
            t.append(" ")
            t.append(KEY_E + " ")  # col6 empty
            t.append("      ")
            # Right: Piano69 at col5, Red at col4 (mirrored)
            t.append(" ")
            t.append(KEY_E + " ")  # col6 empty
            t.append(KEY_F, style=get_style(69))
            t.append(" ")
            t.append(KEY_F, style=get_style(68))
            t.append((KEY_E + " ") * 4)
            rows_txt.append(t)
        
        # Row 2: Piano34 at col5
        for h in range(2):
            t = Text("")
            # Left
            t.append((KEY_E + " ") * 5)
            t.append(KEY_F, style=get_style(34))
            t.append(" ")
            t.append(KEY_E + " ")  # col6 empty
            t.append("      ")
            # Right
            t.append(" ")
            t.append(KEY_E + " ")  # col6 empty
            t.append(KEY_F, style=get_style(70))
            t.append((KEY_E + " ") * 5)
            rows_txt.append(t)
        
        # Row 3: Piano35 at col6 (innermost)
        for h in range(2):
            t = Text("")
            # Left
            t.append((KEY_E + " ") * 6)
            t.append(KEY_F, style=get_style(35))
            t.append(" ")
            t.append("      ")
            # Right
            t.append(" ")
            t.append(KEY_F, style=get_style(71))
            t.append((KEY_E + " ") * 6)
            rows_txt.append(t)
        
        return Group(*rows_txt)
