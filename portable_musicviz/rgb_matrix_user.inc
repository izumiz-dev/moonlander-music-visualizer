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
  float max_left_x;   // Inner edge of left half
  float min_right_x;  // Inner edge of right half
  float min_left_x;   // Outer edge of left half (New)
  float max_right_x;  // Outer edge of right half (New)
  float max_r;
  bool  initialized;
} geometry = { 0, 255, 255, 0, 0.0, false };

static void compute_geometry(void) {
  geometry.max_left_x = 0;
  geometry.min_right_x = 255;
  geometry.min_left_x = 255; // Reset to max for finding min
  geometry.max_right_x = 0;   // Reset to min for finding max
  
  // Find edges
  for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
      float x = (float)g_led_config.point[i].x;
      if (i < 36) { // Left half
          if (x > geometry.max_left_x) geometry.max_left_x = x;
          if (x < geometry.min_left_x) geometry.min_left_x = x;
      } else { // Right half
          if (x < geometry.min_right_x) geometry.min_right_x = x;
          if (x > geometry.max_right_x) geometry.max_right_x = x;
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

// === Smoothing State ===
static struct {
  float bass;
  float mid;
  float treble;
  uint32_t last_update;
} smoothed = { 0, 0, 0, 0 };

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
    // Reset smoothing when inactive
    smoothed.bass = 0;
    smoothed.mid = 0;
    smoothed.treble = 0;
    return false;
  }

  // --- Smoothing Logic ---
  // The goal is to move smoothed.x towards (float)mv.x
  // We use a simple exponential moving average, but we scale it by time 
  // to be independent of the refresh rate of the RGB matrix.
  float dt = (float)(now - smoothed.last_update) / 1000.0f;
  if (dt > 0.1f) dt = 0.1f; // Cap delta to avoid jumps after pauses
  smoothed.last_update = now;

  // Smoothing factor: how fast to react. 
  // Lowered to 12.0f for a more relaxed, "organic" feel.
  const float lerp_factor = 12.0f; 
  float k = lerp_factor * dt;
  if (k > 1.0f) k = 1.0f;

  smoothed.bass   += ((float)mv.bass   - smoothed.bass)   * k;
  smoothed.mid    += ((float)mv.mid    - smoothed.mid)    * k;
  smoothed.treble += ((float)mv.treble - smoothed.treble) * k;
  
  // Audio levels (smoothed) -> radii
  // Apply Square Curve (Gamma 2.0) to make the expansion feel more "fluid" and less abrupt at startup.
  // Input (0..255) -> Norm (0..1) -> Square -> Scale
  float b_n = smoothed.bass / 255.0f;
  float m_n = smoothed.mid / 255.0f;
  float t_n = smoothed.treble / 255.0f;

  const float bass_r   = (b_n * b_n) * 110.0f; // Slightly increased max range to compensate for curve
  const float mid_r    = (m_n * m_n) *  80.0f;
  const float treble_r = (t_n * t_n) *  50.0f;
  
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

    // --- Layer 2: Inward Edge Glow (Round Dynamic Wave) ---
    // Calculate distance from the OUTER edge (creating a ripple effect)
    float dx_outer = (i < 36) ? (lx - geometry.min_left_x) : (geometry.max_right_x - lx);
    float dy_outer = ly - 32.0f; // Center Y is 32
    float r_outer  = sqrtf(dx_outer*dx_outer + dy_outer*dy_outer);

    // Calculate wave radius based on smoothed treble volume (Gamma 2.0 applied via t_n*t_n)
    // Reach is 50% of the total width.
    float outer_wave_radius = (t_n * t_n) * (geometry.max_r * 0.5f);

    if (r_outer <= outer_wave_radius) {
      // Fade out towards the edge of the wave
      float k = (outer_wave_radius - r_outer) / (outer_wave_radius + 1e-3);
      
      // Add color (Treble) scaled by k
      r_out += (int)(rgb_t.r * k);
      g_out += (int)(rgb_t.g * k);
      b_out += (int)(rgb_t.b * k);
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
