RGB_MATRIX_EFFECT(musicviz)

#ifdef RGB_MATRIX_CUSTOM_EFFECT_IMPLS

#include "musicviz.h"

// Forward declaration (defined in keymap.c)
extern musicviz_state_t mv;

// === Utilities ===

static uint8_t clamp_u8(int v) {
  return (v < 0) ? 0 : (v > 255 ? 255 : v);
}

static RGB hsv_to_rgb_u8(uint8_t h, uint8_t s, uint8_t v) {
  HSV hsv = { .h = h, .s = s, .v = v };
  return hsv_to_rgb(hsv);
}

// === LED Geometry (computed once at startup) ===
static struct {
  float max_left_x;
  float min_right_x;
  float max_r;
  bool  initialized;
} geometry = { 0, 255, 0.0, false };

static void compute_geometry(void) {
  geometry.max_left_x = 0;
  geometry.min_right_x = 255;
  
  // Find inner edges
  for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
      float x = (float)g_led_config.point[i].x;
      if (i < 36) { // Left half
          if (x > geometry.max_left_x) geometry.max_left_x = x;
      } else { // Right half
          if (x < geometry.min_right_x) geometry.min_right_x = x;
      }
  }
  
  // Find max distance from inner edge for perimeter/normalization
  float max_dist = 0.0;
  for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
    float lx = (float)g_led_config.point[i].x;
    float ly = (float)g_led_config.point[i].y;
    float dx = (i < 36) ? (geometry.max_left_x - lx) : (lx - geometry.min_right_x);
    float dy = ly - 32.0f;
    float r = sqrtf(dx*dx + dy*dy);
    if (r > max_dist) max_dist = r;
  }
  geometry.max_r = max_dist;
  geometry.initialized = true;
}

// === RGB Matrix Effect ===

bool musicviz(effect_params_t *params) {
  // Initialize geometry on first run
  if (!geometry.initialized) {
    compute_geometry();
  }
  
  // Timeout: if no packet for 500ms, fade out
  uint32_t now = timer_read32();
  bool alive = (now - mv.last_rx_ms) <= 500;
  
  if (!mv.enabled || !alive) {
    for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
        rgb_matrix_set_color(i, 0, 0, 0);
    }
    return false;
  }
  
  // Audio levels (0–255) -> radii
  const float bass_r   = (float)mv.bass   * 100.0 / 255.0;
  const float mid_r    = (float)mv.mid    *  70.0 / 255.0;
  const float treble_r = (float)mv.treble *  40.0 / 255.0;
  
  // Hues to RGB
  RGB rgb_b = hsv_to_rgb_u8(mv.hue_bass, mv.saturation, 255);
  RGB rgb_m = hsv_to_rgb_u8(mv.hue_mid, mv.saturation, 255);
  RGB rgb_t = hsv_to_rgb_u8(mv.hue_treble, mv.saturation, 255);
  
  // === Render each LED ===
  for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
    float lx = (float)g_led_config.point[i].x;
    float ly = (float)g_led_config.point[i].y;
    
    // Symmetric distance calculation:
    // Left side origin is its rightmost LED.
    // Right side origin is its leftmost LED.
    float dx = (i < 36) ? (geometry.max_left_x - lx) : (lx - geometry.min_right_x);
    float dy = ly - 32.0f;
    float r = sqrtf(dx*dx + dy*dy);
    
    int r_out = 0, g_out = 0, b_out = 0;

    // --- Layer 1: Central Waves ---
    if (r <= bass_r) {
      float k = (bass_r - r) / (bass_r + 1e-3);
      r_out += (int)(rgb_b.r * k);
      g_out += (int)(rgb_b.g * k);
      b_out += (int)(rgb_b.b * k);
    }
    if (r <= mid_r) {
      float k = (mid_r - r) / (mid_r + 1e-3);
      r_out += (int)(rgb_m.r * k);
      g_out += (int)(rgb_m.g * k);
      b_out += (int)(rgb_m.b * k);
    }
    if (r <= treble_r) {
      float k = (treble_r - r) / (treble_r + 1e-3);
      r_out += (int)(rgb_t.r * k);
      g_out += (int)(rgb_t.g * k);
      b_out += (int)(rgb_t.b * k);
    }

    // --- Layer 2: Inward Edge Glow ---
    float dist_from_edge = geometry.max_r - r;
    float glow_range = geometry.max_r * 0.4f; 
    
    if (dist_from_edge < glow_range) {
      float intensity = (1.0f - (dist_from_edge / glow_range)) * ((float)mv.treble / 255.0f);
      intensity *= 0.8f;
      r_out += (int)(rgb_t.r * intensity);
      g_out += (int)(rgb_t.g * intensity);
      b_out += (int)(rgb_t.b * intensity);
    }
    
    // Apply master gain and clamp
    r_out = (int)r_out * (int)mv.master_gain / 255;
    g_out = (int)g_out * (int)mv.master_gain / 255;
    b_out = (int)b_out * (int)mv.master_gain / 255;
    
    rgb_matrix_set_color(i, clamp_u8(r_out), clamp_u8(g_out), clamp_u8(b_out));
  }
  
  return false;
}
#endif
