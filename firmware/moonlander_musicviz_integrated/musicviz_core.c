#include "musicviz.h"
#include "raw_hid.h"
#include <string.h>

// Dummy definition to satisfy linker when ORYX_ENABLE=no
uint8_t webhid_leds = 0;

// Global instance (forward declared in musicviz.h if needed, or just exposed here)
musicviz_state_t mv = {0};

void raw_hid_receive(uint8_t *data, uint8_t length) {
  // Raw HID reports are fixed-size (32 bytes in our protocol).
  if (length < 32) return;
  
  // Check magic and version
  if (data[0] != 0x4D) return;      // 'M'
  if (data[1] != 0x01) return;      // v1
  
  // Parse flags
  uint8_t flags = data[2];
  mv.enabled       = (flags & 0x01) ? 1 : 0;
  mv.strobe_enable = (flags & 0x02) ? 1 : 0;
  mv.safety_limit  = (flags & 0x04) ? 1 : 0;
  
  // Parse numeric fields
  mv.master_gain           = data[3];
  mv.loudness_rms          = data[4];
  mv.loudness_peak         = data[5];
  mv.bass                  = data[6];
  mv.mid                   = data[7];
  mv.treble                = data[8];
  mv.beat                  = data[9];
  mv.hue_bass              = data[10];
  mv.hue_mid               = data[11];
  mv.hue_treble            = data[12];
  mv.saturation            = data[13];
  mv.fx_speed              = data[14];
  mv.shockwave_strength    = data[15];
  mv.perimeter_sparkle     = data[16];
  mv.beat_refractory_ms    = data[17];
  
  mv.last_rx_ms = timer_read32();
}
