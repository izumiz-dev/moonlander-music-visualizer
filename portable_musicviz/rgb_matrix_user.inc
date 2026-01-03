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
  float beat;         // Smoothed kick envelope
  float snare;        // Smoothed snare/hihat envelope (from perimeter_sparkle)
  float outer_wave_r; // Persisted radius for Layer 2
  float bass_r;       // Persisted radius for Layer 1 Bass (Restored)
  float mid_r;        // Persisted radius for Layer 1 Mid (Restored)
  float treble_r;     // Persisted radius for Layer 1 Treble (Restored)
  uint32_t last_update;
} smoothed = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 };

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
  float dt = (float)(now - smoothed.last_update) / 1000.0f;
  if (dt > 0.1f) dt = 0.1f; // Cap delta
  smoothed.last_update = now;

  const float lerp_factor = 12.0f; 
  float k = lerp_factor * dt;
  if (k > 1.0f) k = 1.0f;

  smoothed.bass   += ((float)mv.bass   - smoothed.bass)   * k;
  smoothed.mid    += ((float)mv.mid    - smoothed.mid)    * k;
  smoothed.treble += ((float)mv.treble - smoothed.treble) * k;
  smoothed.beat   += ((float)mv.beat   - smoothed.beat)   * k; 
  smoothed.snare  += ((float)mv.perimeter_sparkle - smoothed.snare) * k; 
  
  // Normalized levels
  float b_n = smoothed.bass / 255.0f;
  float m_n = smoothed.mid / 255.0f;
  float t_n = smoothed.treble / 255.0f;
  float beat_n  = smoothed.beat / 255.0f;
  float snare_n = smoothed.snare / 255.0f;


  
  // "Hard Edge & Elastic Bounce" Strategy
  // 1. Snappy Physics: Fast decay to let waves retract quickly.
  // 2. High Contrast: Clear edges to visualize the "movement".
  // 3. Wide Stroke: Low floor + High ceiling = Maximum bouncing range.

  float rms_n = mv.loudness_rms / 255.0f;
  
  // Lowered floor (0.15) to allow deep retraction -> More "Bounce" distance
  float effective_bass = (b_n > (rms_n * 0.15f)) ? b_n : (rms_n * 0.15f);
  
  // Maximum Reach
  const float target_bass_r   = (effective_bass * effective_bass) * 200.0f;
  const float target_mid_r    = (m_n * m_n) * 150.0f;                       
  const float target_treble_r = (t_n * t_n) * 100.0f;                       
  
  // --- Persistence Logic (Elastic / Snappy) ---
  // Increased decay speed (18.0 -> 22.0) for ultra-responsive retraction
  const float decay_k = 22.0f * dt;

  // Center Waves Persistence
  if (target_bass_r > smoothed.bass_r) smoothed.bass_r = target_bass_r;
  else smoothed.bass_r += (target_bass_r - smoothed.bass_r) * decay_k;
  
  if (target_mid_r > smoothed.mid_r) smoothed.mid_r = target_mid_r;
  else smoothed.mid_r += (target_mid_r - smoothed.mid_r) * decay_k;
  
  if (target_treble_r > smoothed.treble_r) smoothed.treble_r = target_treble_r;
  else smoothed.treble_r += (target_treble_r - smoothed.treble_r) * decay_k;

  // Vivid Overdrive Strategy - No more desaturation.
  // We keep the saturation at 100% (mv.saturation) at all times.
  uint8_t dyn_sat = mv.saturation;

  // RGB rgb_b, rgb_m, rgb_t are now calculated locally per pixel for the Vivid Core effect.
  
  // === Render each LED ===
  for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
    float lx = (float)g_led_config.point[i].x;
    float ly = (float)g_led_config.point[i].y;
    
    // Center Distance
    float dx = (i < 36) ? (geometry.max_left_x - lx) : (lx - geometry.min_right_x);
    float dy = ly - 32.0f;
    float r = sqrtf(dx*dx + dy*dy);
    
    int r_out = 0, g_out = 0, b_out = 0;

    // --- Layer 1: Central Waves (Hard Edge + Dynamic Vivid Core) ---
    // Inlined Logic for C compatibility (No Lambdas)
    const float edge_width = 5.0f;
    
    // Dynamic Vivid Core Radius (Linked to Bass & Volume)
    float white_core_r = 0.0f;
    if (mv.loudness_rms > 80) {
        float intensity = (float)(mv.loudness_rms - 80) / 175.0f; // 0.0 to 1.0
        white_core_r = smoothed.bass_r * 0.3f * intensity; 
    }
    
    // Bass Wave
    if (r <= smoothed.bass_r) {
        float k = 1.0f;
        if (r > (smoothed.bass_r - edge_width)) {
            k = (smoothed.bass_r - r) / edge_width;
        }
        
        // Deep Shadow Gamma 3.0 + Threshold Gate (Absolute Black)
        float gain = k * k * k;
        if (gain < 0.02f) gain = 0.0f; // Threshold Gate: Silence the tail
        
        uint8_t local_sat = dyn_sat;
        float local_gain = gain;
        
        // White Core Effect: Only trigger if we have enough base intensity
        if (r <= white_core_r && gain > 0.5f) {
            local_sat = 40;   
            local_gain *= 2.0f; 
        }
        
        RGB c = hsv_to_rgb_u8(mv.hue_bass, local_sat, 255);
        r_out += (int)(c.r * local_gain);
        g_out += (int)(c.g * local_gain);
        b_out += (int)(c.b * local_gain);
    }
    
    // Mid Wave
    if (r <= smoothed.mid_r) {
        float k = 1.0f;
        if (r > (smoothed.mid_r - edge_width)) {
            k = (smoothed.mid_r - r) / edge_width;
        }
        float gain = k * k * k;
        if (gain < 0.02f) gain = 0.0f; // Threshold Gate
        
        uint8_t local_sat = dyn_sat;
        float local_gain = gain;
        if (r <= (white_core_r * 0.7f) && gain > 0.5f) {
            local_sat = 40;
            local_gain *= 2.0f;
        }

        RGB c = hsv_to_rgb_u8(mv.hue_mid, local_sat, 255);
        r_out += (int)(c.r * local_gain);
        g_out += (int)(c.g * local_gain);
        b_out += (int)(c.b * local_gain);
    }

    // Treble Wave
    if (r <= smoothed.treble_r) {
        float k = 1.0f;
        if (r > (smoothed.treble_r - edge_width)) {
            k = (smoothed.treble_r - r) / edge_width;
        }
        float gain = k * k * k;
        if (gain < 0.02f) gain = 0.0f; // Threshold Gate
        
        uint8_t local_sat = dyn_sat;
        float local_gain = gain;
        if (r <= (white_core_r * 0.5f) && gain > 0.5f) {
            local_sat = 40;
            local_gain *= 2.0f;
        }

        RGB c = hsv_to_rgb_u8(mv.hue_treble, local_sat, 255);
        r_out += (int)(c.r * local_gain);
        g_out += (int)(c.g * local_gain);
        b_out += (int)(c.b * local_gain);
    }

    // --- Layer 2: Wing Thrust (Thumb Cluster Engines) ---
    // Moonlander Thumb Clusters: Left [29-35], Right [65-71]
    bool is_wing = (i >= 29 && i <= 35) || (i >= 65 && i <= 71);
    
    if (is_wing) {
        // Recalculate base colors for Wing Thrust (using dynamic saturation)
        RGB wing_rgb_b = hsv_to_rgb_u8(mv.hue_bass, dyn_sat, 255);
        RGB wing_rgb_t = hsv_to_rgb_u8(mv.hue_treble, dyn_sat, 255);

        // Kick drives the engine thrust (Bass Color)
        if (beat_n > 0.05f) {
            float k = beat_n * beat_n; // Sharp thrust
            r_out += (int)(wing_rgb_b.r * k);
            g_out += (int)(wing_rgb_b.g * k);
            b_out += (int)(wing_rgb_b.b * k);
        }
        
        // Snare/Hat adds afterburner sparkle (Treble Color)
        if (snare_n > 0.05f) {
             float k = snare_n * snare_n; 
             r_out += (int)(wing_rgb_t.r * k);
             g_out += (int)(wing_rgb_t.g * k);
             b_out += (int)(wing_rgb_t.b * k);
        }
    }
    
    // Apply master gain (Silence Gate: Squared Curve for True Black)
    // Non-linear gain: 50% volume -> 25% brightness. 10% volume -> 1% brightness.
    uint32_t mg = mv.master_gain;
    uint32_t mg_sq = (mg * mg) >> 8; 
    
    r_out = (r_out * mg_sq) >> 8;
    g_out = (g_out * mg_sq) >> 8;
    b_out = (b_out * mg_sq) >> 8;
    
    rgb_matrix_set_color(i, clamp_u8(r_out), clamp_u8(g_out), clamp_u8(b_out));
  }
  
  return false;
}
#endif
