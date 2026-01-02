# Add these to your rules.mk.
# Music Visualizer requires control over Raw HID, so we must disable Oryx's default handler.
ORYX_ENABLE = no
RAW_ENABLE = yes
RGB_MATRIX_CUSTOM_USER = yes

# Include the core logic source file
SRC += musicviz_core.c
