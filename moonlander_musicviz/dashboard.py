import time
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.console import Console, Group
from rich.progress import BarColumn, Progress, TextColumn
from rich.text import Text
from rich.align import Align

class TerminalDashboard:
    """
    Music Visualizer Dashboard using Rich.
    Displays:
    - Status (BPM, Device, Active Palette)
    - Audio Levels (Bass/Mid/Treble/Loudness)
    - Beat Indicator
    """
    
    def __init__(self):
        self.console = Console()
        self.layout = Layout()
        
        # Split layout: Header (Status) + Body (Bars)
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="body")
        )
        
        # Audio Level Progress Bars
        self.level_progress = Progress(
            TextColumn("{task.description}"),
            BarColumn(bar_width=None, complete_style="blue", finished_style="green"),
            TextColumn("{task.fields[value]:.2f}"),
            expand=True
        )
        
        # Tasks for bars
        self.task_bass = self.level_progress.add_task("[cyan]BASS[/cyan]", total=1.0, value=0.0)
        self.task_mid = self.level_progress.add_task("[yellow]MID [/yellow]", total=1.0, value=0.0)
        self.task_treble = self.level_progress.add_task("[magenta]TREB[/magenta]", total=1.0, value=0.0)
        self.task_loudness = self.level_progress.add_task("[white]RMS [/white]", total=1.0, value=0.0)
        self.task_beat = self.level_progress.add_task("[red]BEAT[/red]", total=1.0, value=0.0)

    def update(self, features, palette_name, device_name):
        """
        Update the dashboard with new audio features.
        Returns the renderable layout.
        """
        
        # Update Progress Bars
        self.level_progress.update(self.task_bass, completed=features.get('bass', 0), value=features.get('bass', 0))
        self.level_progress.update(self.task_mid, completed=features.get('mid', 0), value=features.get('mid', 0))
        self.level_progress.update(self.task_treble, completed=features.get('treble', 0), value=features.get('treble', 0))
        self.level_progress.update(self.task_loudness, completed=features.get('loudness_rms', 0), value=features.get('loudness_rms', 0))
        self.level_progress.update(self.task_beat, completed=features.get('beat', 0), value=features.get('beat', 0))
        
        # Header Info
        bpm = features.get('bpm', 0)
        beat_indicator = "🔴" if features.get('beat', 0) > 0.8 else "⚪"
        
        header_text = Text(f"Moonlander MusicViz  |  Device: {device_name}  |  Palette: {palette_name}  |  BPM: {bpm:.1f}  {beat_indicator}", style="bold white on black", justify="center")
        
        self.layout["header"].update(header_text)
        
        # Body: Bars + Info
        body_panel = Panel(
            self.level_progress,
            title="Audio Levels",
            border_style="blue"
        )
        self.layout["body"].update(body_panel)
        
        return self.layout
