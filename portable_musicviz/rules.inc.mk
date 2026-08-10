# Add these to your rules.mk.
# Music Visualizer requires control over Raw HID, so we must disable Oryx's default handler.
ORYX_ENABLE = no
RAW_ENABLE = yes
RGB_MATRIX_CUSTOM_USER = yes

# Oryx exports set RGB_MATRIX_CUSTOM_KB = yes, which makes rgb_matrix.h include
# keyboards/zsa/moonlander/rgb_matrix_kb.inc. That file only exists in ZSA's QMK
# fork, so upstream QMK fails with "rgb_matrix_kb.inc: No such file or directory".
# We supply our effect through RGB_MATRIX_CUSTOM_USER instead, so turn it off.
RGB_MATRIX_CUSTOM_KB = no

# Include the core logic source file
SRC += musicviz_core.c
