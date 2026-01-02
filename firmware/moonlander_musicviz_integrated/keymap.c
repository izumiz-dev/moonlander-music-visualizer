#include QMK_KEYBOARD_H
#include "version.h"
#include "i18n.h"
#include "raw_hid.h"
#include "timer.h"
#include <string.h>

#define MOON_LED_LEVEL LED_LEVEL
#ifndef ZSA_SAFE_RANGE
#define ZSA_SAFE_RANGE SAFE_RANGE
#endif

#include "musicviz.h"

// Dummy definition to satisfy linker when ORYX_ENABLE=no
uint8_t webhid_leds = 0;

// === Music Visualizer State (Shared with rgb_matrix_user.inc) ===
// musicviz_state_t defined in musicviz.h and instantiated in musicviz_core.c
extern musicviz_state_t mv;

// raw_hid_receive is handled in musicviz_core.c

// === User Keymap Definition ===
enum custom_keycodes { RGB_SLD = ZSA_SAFE_RANGE, };
enum tap_dance_codes { DANCE_0, DANCE_1, DANCE_2, DANCE_3, };

const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
  [0] = LAYOUT_moonlander(
    KC_GRAVE, KC_1, KC_2, KC_3, KC_4, KC_5, KC_TRANSPARENT, TD(DANCE_0), KC_6, KC_7, KC_8, KC_9, KC_0, KC_MINUS,
    KC_EQUAL, KC_Q, KC_W, KC_E, KC_R, KC_T, KC_TRANSPARENT, TD(DANCE_1), KC_Y, KC_U, KC_I, KC_O, KC_P, KC_BSLS,
    MO(2), KC_A, KC_S, KC_D, KC_F, KC_G, JP_MEISU, JP_MKANA, KC_H, KC_J, KC_K, KC_L, KC_SCLN, LT(3, KC_QUOTE),
    KC_LEFT_SHIFT, MT(MOD_LCTL, KC_Z), KC_X, KC_C, KC_V, KC_B, KC_N, KC_M, KC_COMMA, KC_DOT, MT(MOD_RCTL, KC_SLASH), KC_RIGHT_SHIFT,
    KC_DELETE, KC_HOME, KC_END, KC_LEFT, KC_RIGHT, KC_LEFT_ALT, KC_ESCAPE, KC_UP, KC_DOWN, KC_LBRC, KC_RBRC, KC_RIGHT_GUI,
    KC_BSPC, KC_SPACE, KC_LEFT_CTRL, KC_RIGHT_CTRL, KC_TAB, KC_ENTER
  ),
  [1] = LAYOUT_moonlander(
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, TD(DANCE_2), KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, TD(DANCE_3), KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_S, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_J, KC_TRANSPARENT, KC_L, KC_TRANSPARENT, KC_TRANSPARENT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,
    KC_TRANSPARENT, LGUI(KC_LEFT), LGUI(KC_RIGHT), KC_TRANSPARENT, KC_TRANSPARENT, KC_LEFT_ALT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_LBRC, KC_TRANSPARENT, KC_TRANSPARENT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_LEFT_GUI, KC_RIGHT_GUI, KC_TRANSPARENT, KC_TRANSPARENT
  ),
  [2] = LAYOUT_moonlander(
    KC_TRANSPARENT, KC_F1, KC_F2, KC_F3, KC_F4, KC_F5, KC_TRANSPARENT, KC_TRANSPARENT, KC_F6, KC_F7, KC_F8, KC_F9, KC_F10, KC_F11,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_UP, KC_TRANSPARENT, KC_TRANSPARENT, KC_F12,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_LEFT, KC_DOWN, KC_RIGHT, KC_TRANSPARENT, KC_TRANSPARENT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT
  ),
  [3] = LAYOUT_moonlander(
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, RGB_SAI, RGB_SAD, KC_TRANSPARENT, KC_TRANSPARENT, KR_HANJ, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, RGB_HUI, RGB_HUD, KC_TRANSPARENT, KR_HAEN, RGUI(KC_SPACE), KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, RGB_SPI, RGB_SPD, KC_TRANSPARENT, KC_AUDIO_MUTE, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,
    KC_TRANSPARENT, RGB_MODE_FORWARD, TOGGLE_LAYER_COLOR, RGB_VAI, RGB_VAD, TO(1), TO(0), KC_AUDIO_VOL_UP, KC_AUDIO_VOL_DOWN, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TAB, KC_ENTER
  ),
};

extern rgb_config_t rgb_matrix_config;
RGB hsv_to_rgb_with_value(HSV hsv) {
  RGB rgb = hsv_to_rgb(hsv);
  float f = (float)rgb_matrix_config.hsv.v / UINT8_MAX;
  return (RGB){ f * rgb.r, f * rgb.g, f * rgb.b };
}
void keyboard_post_init_user(void) { rgb_matrix_enable(); }

const uint8_t PROGMEM ledmap[][RGB_MATRIX_LED_COUNT][3] = {
    [1] = { {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253}, {89,67,253} },
    [2] = { {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255}, {143,248,255} },
    [3] = { {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255}, {20,255,255} },
};

void set_layer_color(int layer) {
  for (int i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
    HSV hsv = { pgm_read_byte(&ledmap[layer][i][0]), pgm_read_byte(&ledmap[layer][i][1]), pgm_read_byte(&ledmap[layer][i][2]) };
    if (!hsv.h && !hsv.s && !hsv.v) { rgb_matrix_set_color( i, 0, 0, 0 ); }
    else { RGB rgb = hsv_to_rgb_with_value(hsv); rgb_matrix_set_color(i, rgb.r, rgb.g, rgb.b); }
  }
}

bool rgb_matrix_indicators_user(void) {
  // if (rawhid_state.rgb_control) return false;
  if (!keyboard_config.disable_layer_led) { 
    switch (biton32(layer_state)) {
      case 1: set_layer_color(1); break;
      case 2: set_layer_color(2); break;
      case 3: set_layer_color(3); break;
      default: if (rgb_matrix_get_flags() == LED_FLAG_NONE) rgb_matrix_set_color_all(0, 0, 0);
    }
  } else { if (rgb_matrix_get_flags() == LED_FLAG_NONE) rgb_matrix_set_color_all(0, 0, 0); }
  return true;
}

typedef struct { bool is_press_action; uint8_t step; } tap;
enum { SINGLE_TAP = 1, SINGLE_HOLD, DOUBLE_TAP, DOUBLE_HOLD, DOUBLE_SINGLE_TAP, MORE_TAPS };
static tap dance_state[4];
uint8_t dance_step(tap_dance_state_t *state) {
    if (state->count == 1) { if (state->interrupted || !state->pressed) return SINGLE_TAP; else return SINGLE_HOLD; }
    else if (state->count == 2) { if (state->interrupted) return DOUBLE_SINGLE_TAP; else if (state->pressed) return DOUBLE_HOLD; else return DOUBLE_TAP; }
    return MORE_TAPS;
}
void dance_0_finished(tap_dance_state_t *state, void *user_data) { dance_state[0].step = dance_step(state); switch (dance_state[0].step) { case DOUBLE_TAP: register_code16(RGUI(KC_L)); break; } }
void dance_0_reset(tap_dance_state_t *state, void *user_data) { wait_ms(10); switch (dance_state[0].step) { case DOUBLE_TAP: unregister_code16(RGUI(KC_L)); break; } dance_state[0].step = 0; }
void dance_1_finished(tap_dance_state_t *state, void *user_data) { dance_state[1].step = dance_step(state); switch (dance_state[1].step) { case DOUBLE_TAP: register_code16(KC_PSCR); break; } }
void dance_1_reset(tap_dance_state_t *state, void *user_data) { wait_ms(10); switch (dance_state[1].step) { case DOUBLE_TAP: unregister_code16(KC_PSCR); break; } dance_state[1].step = 0; }
void dance_2_finished(tap_dance_state_t *state, void *user_data) { dance_state[2].step = dance_step(state); switch (dance_state[2].step) { case DOUBLE_TAP: register_code16(LCTL(LGUI(KC_Q))); break; } }
void dance_2_reset(tap_dance_state_t *state, void *user_data) { wait_ms(10); switch (dance_state[2].step) { case DOUBLE_TAP: unregister_code16(LCTL(LGUI(KC_Q))); break; } dance_state[2].step = 0; }
void dance_3_finished(tap_dance_state_t *state, void *user_data) { dance_state[3].step = dance_step(state); switch (dance_state[3].step) { case DOUBLE_TAP: register_code16(LGUI(RSFT(KC_3))); break; } }
void dance_3_reset(tap_dance_state_t *state, void *user_data) { wait_ms(10); switch (dance_state[3].step) { case DOUBLE_TAP: unregister_code16(LGUI(RSFT(KC_3))); break; } dance_state[3].step = 0; }

tap_dance_action_t tap_dance_actions[] = {
    [DANCE_0] = ACTION_TAP_DANCE_FN_ADVANCED(NULL, dance_0_finished, dance_0_reset),
    [DANCE_1] = ACTION_TAP_DANCE_FN_ADVANCED(NULL, dance_1_finished, dance_1_reset),
    [DANCE_2] = ACTION_TAP_DANCE_FN_ADVANCED(NULL, dance_2_finished, dance_2_reset),
    [DANCE_3] = ACTION_TAP_DANCE_FN_ADVANCED(NULL, dance_3_finished, dance_3_reset),
};

bool process_record_user(uint16_t keycode, keyrecord_t *record) {
  switch (keycode) { case RGB_SLD: /* if (rawhid_state.rgb_control) return false; */ if (record->event.pressed) rgblight_mode(1); return false; }
  return true;
}
