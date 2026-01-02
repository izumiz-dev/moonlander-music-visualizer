#pragma once
#include <stdint.h>
#include "timer.h"

// === Music Visualizer State ===
typedef struct {
  uint8_t enabled;
  uint8_t master_gain;
  uint8_t loudness_rms, loudness_peak;
  uint8_t bass, mid, treble;
  uint8_t beat;
  uint8_t hue_bass, hue_mid, hue_treble;
  uint8_t saturation;
  uint8_t fx_speed;
  uint8_t shockwave_strength;
  uint8_t perimeter_sparkle;
  uint8_t beat_refractory_ms;
  uint32_t last_rx_ms;
  uint32_t last_beat_ms;
  uint8_t strobe_enable, safety_limit;
} musicviz_state_t;
