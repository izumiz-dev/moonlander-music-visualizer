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



// Smooth step (Hermite spline): fade 0->1 over [edge0, edge1]
static float smoothstep(float edge0, float edge1, float x) {
  float t = (x - edge0) / (edge1 - edge0 + 1e-6);
  if (t < 0.0) return 0.0;
  if (t > 1.0) return 1.0;
  return t * t * (3.0 - 2.0 * t);
}

// Compute distance from center point (Moonlander is [120, 36])
static float led_distance(uint8_t i, int cx, int cy) {
  int dx = (int)g_led_config.point[i].x - cx;
  int dy = (int)g_led_config.point[i].y - cy;
  return sqrtf((float)(dx * dx + dy * dy));
}

// === Beat shockwave state ===
static struct {
  uint32_t trigger_ms;
  uint8_t  strength;
  float    decay_ms;  // time constant for expansion + fade
} shockwave = { 0, 0, 200.0 };

// === Laser Beams State (Treble) ===
#define MAX_LASERS 4
typedef struct {
  bool  active;
  float y;          // Vertical position (0..72 approx)
  float x;          // Horizontal head position
  float speed;      // units per second (+ for L->R, - for R->L)
  float brightness; 
} laser_t;

static laser_t lasers[MAX_LASERS] = {0};
static uint32_t last_laser_ms = 0;
// Simple PRNG
static uint16_t rand_state = 1234;
static uint8_t fast_rand(void) {
    rand_state = rand_state * 137 + 53;
    return (rand_state >> 8);
}

// === LED neighborhood (perimeter detection, computed once at startup) ===
static struct {
  uint8_t  led_indices[RGB_MATRIX_LED_COUNT];
  uint8_t  count;
  float    max_r;
} perimeter = { { 0 }, 0, 0.0 };

static void compute_perimeter(void) {
  const int cx = 120, cy = 36;
  float max_dist = 0.0;
  
  // First pass: find max distance
  for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
    float r = led_distance(i, cx, cy);
    if (r > max_dist) max_dist = r;
  }
  perimeter.max_r = max_dist;
  
  // Second pass: collect LEDs in top 15% (outer ring)
  float threshold = max_dist * 0.85;  // Keep top 15%
  perimeter.count = 0;
  for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
    float r = led_distance(i, cx, cy);
    if (r > threshold) {
      perimeter.led_indices[perimeter.count++] = i;
    }
  }
}





// === RGB Matrix Effect ===

// RGB_MATRIX_EFFECT(musicviz) - Moved to top

bool musicviz(effect_params_t *params) {
  // Initialize perimeter on first run
  if (perimeter.max_r == 0.0) {
    compute_perimeter();
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
  
  // Moonlander center point (per Perplexity research: 112, 32)
  const int cx = 112, cy = 32;
  
  // === Convert audio levels (0–255) to spatial radii ===
  // Bass: wide spread (up to 100 units from center)
  // Mid: medium (up to 70)
  // Treble: narrow (up to 40)
  const float bass_r   = (float)mv.bass   * 100.0 / 255.0;
  const float mid_r    = (float)mv.mid    *  70.0 / 255.0;
  const float treble_r = (float)mv.treble *  40.0 / 255.0;
  
  // === Convert hues to RGB ===
  RGB rgb_b = hsv_to_rgb_u8(mv.hue_bass, mv.saturation, 255);
  RGB rgb_m = hsv_to_rgb_u8(mv.hue_mid, mv.saturation, 255);
  RGB rgb_t = hsv_to_rgb_u8(mv.hue_treble, mv.saturation, 255);
  
  // === Beat shockwave update ===
  if (mv.beat > 200) {  // Beat trigger threshold
    // Check refractory period
    uint32_t beat_interval_ms = mv.beat_refractory_ms * 4;  // 0–255 units = 0–1020ms
    if (beat_interval_ms == 0) beat_interval_ms = 120;      // default 120ms
    
    if (now - mv.last_beat_ms > beat_interval_ms) {
      shockwave.trigger_ms = now;
      shockwave.strength = mv.beat;  // use beat value as amplitude
      mv.last_beat_ms = now;
    }
  }

  // === Update Laser Beams ===
  // 1. Update existing lasers
  float dt = (now - last_laser_ms) / 1000.0f;
  if (dt < 0) dt = 0;
  if (dt > 0.1) dt = 0.1;
  last_laser_ms = now;

  for (int i = 0; i < MAX_LASERS; i++) {
    if (lasers[i].active) {
       lasers[i].x += lasers[i].speed * dt;
       // Boundary check (Moonlander width approx 240 units? cx=120)
       // Let's assume range -20 to 260
       if (lasers[i].x > 260.0f || lasers[i].x < -20.0f) {
         lasers[i].active = false;
       }
    }
  }

  // 2. Spawn new lasers based on Treble
  // Threshold: > 50 (Very sensitive)
  // Refractory period: 50ms (Flood allowed)
  static uint32_t last_spawn_request = 0;
  
  if (mv.treble > 50 && (now - last_spawn_request > 50)) {
      last_spawn_request = now;
      
      // GUARANTEED SPAWN if slot available
      for (int i = 0; i < MAX_LASERS; i++) {
          if (!lasers[i].active) {
              lasers[i].active = true;
              
              // Random Y height: Snap to a real LED row
              uint8_t rand_idx = fast_rand() % RGB_MATRIX_LED_COUNT;
              lasers[i].y = (float)g_led_config.point[rand_idx].y;
              
              // Random Direction
              if (fast_rand() > 127) {
                  lasers[i].x = -50.0f; // Start Far Left
                  lasers[i].speed = 300.0f; // Slower for visibility
              } else {
                  lasers[i].x = 280.0f; // Start Far Right
                  lasers[i].speed = -300.0f; 
              }
              
              // Max brightness
              lasers[i].brightness = 1.0f; 
              break;
          }
      }
  }
  
  // === Render each LED ===
  for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
    float r = led_distance(i, cx, cy);
    
    int r_out = 0, g_out = 0, b_out = 0;
    
    // --- Layer 1: Central Waves (Bass/Mid/Treble) ---
    // These expand from the center (cx, cy)
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

    // --- Layer 2: Inward Edge Glow (Restored & Enhanced) ---
    // Light bleeds from the perimeter inwards.
    // We use the distance from the outer edge (max_r - r).
    float dist_from_edge = perimeter.max_r - r;
    // Glow reaches about 40% into the keyboard from the edge.
    float glow_range = perimeter.max_r * 0.4f; 
    
    if (dist_from_edge < glow_range) {
      // Glow intensity based on Treble (high energy)
      float intensity = (1.0f - (dist_from_edge / glow_range)) * ((float)mv.treble / 255.0f);
      intensity *= 0.8f; // Cap glow contribution

      // Additive blend: the glow mixes with the central waves.
      // If waves are Red and Glow is Blue, we get Purple in the middle.
      r_out += (int)(rgb_t.r * intensity);
      g_out += (int)(rgb_t.g * intensity);
      b_out += (int)(rgb_t.b * intensity);
    }
    
    // --- Laser Beams (Horizontal) ---
    for (int s = 0; s < MAX_LASERS; s++) {
        if (!lasers[s].active) continue;

        // LED coords
        float lx = (float)g_led_config.point[i].x;
        float ly = (float)g_led_config.point[i].y;

        // Vertical distance check (Beam thickness)
        // INCREASED WIDTH for visibility: 8.0 -> 15.0 (Huge)
        if (fabsf(ly - lasers[s].y) < 15.0f) {
            // Horizontal check (Trail)
            float dist_x;
            if (lasers[s].speed > 0) { // Moving Right
                 dist_x = lasers[s].x - lx;
            } else { // Moving Left
                 dist_x = lx - lasers[s].x;
            }

            // Trail length: 200 units (Full keyboard width)
            if (dist_x >= 0.0f && dist_x < 200.0f) {
                float intensity = 1.0f - (dist_x / 200.0f);
                if (intensity < 0) intensity = 0;
                // intensity *= lasers[s].brightness; // Max brightness always

                // White Color (Overwrite/Max Add)
                r_out += (int)(255 * intensity);
                g_out += (int)(255 * intensity);
                b_out += (int)(255 * intensity);
            }
        }
    }
    
    // --- Shockwave effect (beat-triggered expanding ring) ---
    // Tuned for "Spike" effect: fast, thin, sharp
    float time_since_beat = (float)(now - shockwave.trigger_ms);
    if (time_since_beat >= 0 && time_since_beat <= 150.0) {  // 150ms duration (short spike)
      float wave_speed = 350.0;  // units/sec (very fast)
      float wavefront = wave_speed * (time_since_beat / 1000.0);
      float ring_thickness = 3.0 + (float)mv.treble * 1.5 / 255.0; // Thin ring
      
      // Radial ring intensity
      float dist_to_wave = fabsf(r - wavefront);
      float ring_i = smoothstep(ring_thickness, 0.0, dist_to_wave);
      ring_i *= expf(-time_since_beat / 100.0);  // fast decay (100ms)
      
      // Add white or magenta to the ring
      uint8_t ring_brightness = (uint8_t)(255.0 * ring_i * (float)shockwave.strength / 255.0);
      if (mv.safety_limit && ring_brightness > 200) ring_brightness = 200;  // safety cap
      
      r_out += ring_brightness;
      g_out += (ring_brightness >> 1);  // magenta tint: less green
      b_out += ring_brightness;
    }
    
    // --- Beat strobe (optional safety-gated flash) ---
    if (mv.beat > 240 && mv.strobe_enable) {
      uint8_t strobe_bright = mv.safety_limit ? 100 : 180;
      r_out += strobe_bright;
      g_out += strobe_bright;
      b_out += strobe_bright;
    }
    
    // --- Apply master gain and clamp ---
    r_out = (int)r_out * (int)mv.master_gain / 255;
    g_out = (int)g_out * (int)mv.master_gain / 255;
    b_out = (int)b_out * (int)mv.master_gain / 255;
    
    rgb_matrix_set_color(i, clamp_u8(r_out), clamp_u8(g_out), clamp_u8(b_out));
  }
  
  return false; // Effect always active
}
#endif
