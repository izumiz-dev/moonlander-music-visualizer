// Appended to the Oryx keymap's config.h by build_firmware.sh.
//
// Oryx generates keymaps against ZSA's QMK fork, which still uses the legacy
// RGB Matrix keycode spellings. Upstream QMK renamed them (RGB_* -> RM_*) and
// dropped the old names, so an unmodified Oryx export fails to compile with
// errors like:
//
//     error: 'RGB_TOG' undeclared here (not in a function)
//
// Map the legacy spellings onto the current ones so the exported keymap.c
// builds untouched. These are inert if the old names never appear.
//
// Note: RGB_SLD is NOT listed here -- Oryx defines it itself in keymap.c's
// custom_keycodes enum, so defining it would break that declaration.

#define RGB_TOG          RM_TOGG
#define RGB_MODE_FORWARD RM_NEXT
#define RGB_HUI          RM_HUEU
#define RGB_HUD          RM_HUED
#define RGB_SAI          RM_SATU
#define RGB_SAD          RM_SATD
#define RGB_VAI          RM_VALU
#define RGB_VAD          RM_VALD
#define RGB_SPI          RM_SPDU
#define RGB_SPD          RM_SPDD
