# Refined Color Palettes with Saturation and Rotation controls

PALETTES = {
    # --- Vivid / Party ---
    "Cyberpunk": {
        "hues": (165, 205, 235),  # Blue / Purple / Pink
        "saturation": 240,
        "rotation_allowed": True
    },
    "NeonPop": {
        "hues": (230, 145, 15),   # Hot Pink / Aqua / Orange
        "saturation": 245,
        "rotation_allowed": True
    },
    "Magma": {
        "hues": (0, 20, 45),       # Red / Orange / Gold
        "saturation": 235,
        "rotation_allowed": True
    },
    
    # --- Chic / Modern ---
    "Arctic": {
        "hues": (140, 150, 160),  # Ice Blue / Blue / White-ish
        "saturation": 180,        # Slightly desaturated
        "rotation_allowed": False
    },

    "TokyoNight": {
        "hues": (180, 210, 150),  # Deep Purple / Magenta / Cyan
        "saturation": 230,
        "rotation_allowed": False
    },
    "Warmth": {
        "hues": (25, 35, 45),     # Amber / Gold / Yellow
        "saturation": 220,        # Warm, not neon
        "rotation_allowed": False
    },
    
    # --- Moody / Deep ---
    "DeepSea": {
        "hues": (150, 165, 180),  # Blue / Azure / Deep Blue
        "saturation": 235,
        "rotation_allowed": True
    },
    "Forest": {
        "hues": (80, 110, 140),   # Dark Green / Green / Mint
        "saturation": 235,
        "rotation_allowed": True
    },
    "Matrix": {
        "hues": (85, 95, 105),    # Pure Green variations
        "saturation": 245,
        "rotation_allowed": True
    }
}

# List of names for cycling
PALETTE_NAMES = list(PALETTES.keys())
