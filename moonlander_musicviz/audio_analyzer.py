"""FFT-based audio analysis: 3 bands + loudness + beat detection."""
import numpy as np
import time

class AudioAnalyzer:
    """
    Performs real-time audio FFT analysis.
    
    Outputs:
    - loudness_rms: frame energy (0–1)
    - loudness_peak: frame peak (0–1)
    - bass, mid, treble: band energies (0–1)
    - beat: beat strength (0–1); computed from bass with dynamic threshold + refractory
    """
    
    def __init__(self, sr=48000, nfft=2048, hop=1024):
        self.sr = sr
        self.nfft = nfft
        self.hop = hop
        self.window = np.hanning(nfft).astype(np.float32)
        
        # Envelope followers (attack/release)
        # Tuned for "Jab-like" feel: faster attack, sharper release
        self.env_bass = Envelope(attack=0.85, release=0.25)
        self.env_mid = Envelope(attack=0.60, release=0.15)
        self.env_treble = Envelope(attack=0.35, release=0.06)
        self.env_loudness = Envelope(attack=0.50, release=0.10)
        
        # Adaptive normalization
        self.peak_tracks = {'bass': 0.01, 'mid': 0.01, 'treble': 0.01, 'rms': 0.01}
        
        # Beat detection
        self.beat_history = []
        self.beat_history_len = int(2.0 * sr / hop)  # ~2 seconds
        self.prev_bass = 0.0
        
        # Circular buffer for FFT
        self.buf = np.zeros((nfft, 2), dtype=np.float32)
    
    def update(self, frame):
        """
        Process a frame of audio (shape: (hop, 2) for stereo, or (hop,) for mono).
        Returns dict with audio features.
        """
        # Ensure stereo
        if frame.ndim == 1:
            frame = np.column_stack([frame, frame])
        
        # Shift buffer and append new frame
        self.buf = np.roll(self.buf, -self.hop, axis=0)
        self.buf[-self.hop:] = frame
        
        # Convert to mono
        mono = self.buf.mean(axis=1)
        windowed = mono * self.window
        
        # FFT
        spec = np.fft.rfft(windowed)
        mag = np.abs(spec)
        freqs = np.fft.rfftfreq(self.nfft, d=1.0/self.sr)
        
        # Loudness (RMS)
        rms = float(np.sqrt(np.mean(windowed * windowed)) + 1e-12)
        
        # Band energies (Log scaling will be applied via normalization)
        # Wider range for Treble to catch "air"
        bass_raw = self._band_energy(mag, freqs, 20, 120)
        mid_raw = self._band_energy(mag, freqs, 120, 4000)
        treble_raw = self._band_energy(mag, freqs, 4000, 20000)
        
        # Adaptive normalization with Log-like boost for quiet sounds
        pt = self.peak_tracks
        # Decay factor 0.995 is slower, keeping the "ceiling" high for longer (better dynamics)
        decay = 0.995
        pt['bass'] = max(pt['bass'] * decay, bass_raw)
        pt['mid'] = max(pt['mid'] * decay, mid_raw)
        pt['treble'] = max(pt['treble'] * decay, treble_raw)
        pt['rms'] = max(pt['rms'] * decay, rms)
        
        # Normalize: (val / peak) ^ 0.75 -> Moderate boost (more contrast than sqrt)
        def norm(v, p):
            return np.clip(np.power(v / (p + 1e-6), 0.75), 0.0, 1.0)

        bass_n = norm(bass_raw, pt['bass'])
        mid_n = norm(mid_raw, pt['mid'])
        treble_n = norm(treble_raw, pt['treble'])
        rms_n = norm(rms, pt['rms'])
        
        # Apply envelopes
        bass_e = self.env_bass.update(bass_n)
        mid_e = self.env_mid.update(mid_n)
        treble_e = self.env_treble.update(treble_n)
        
        # Loudness: Keep it linear to preserve dynamics (quiet is quiet, loud is loud)
        # Faster release for crisp silence
        self.env_loudness.release = 0.2
        loudness_e = self.env_loudness.update(rms_n)
        
        # Beat detection (bass transient + dynamic threshold)
        self.beat_history.append(bass_e)
        if len(self.beat_history) > self.beat_history_len:
            self.beat_history.pop(0)
        
        beat = self._detect_beat(bass_e, threshold=0.15)
        
        # BPM Estimation
        if beat > 0.5:
            now = time.time()
            if hasattr(self, 'last_beat_time'):
                interval = now - self.last_beat_time
                if 0.3 < interval < 2.0:  # 30-200 BPM range
                    if not hasattr(self, 'intervals'): self.intervals = []
                    self.intervals.append(interval)
                    if len(self.intervals) > 8: self.intervals.pop(0)
            self.last_beat_time = now
        
        bpm = 0
        if hasattr(self, 'intervals') and len(self.intervals) > 0:
            avg_interval = sum(self.intervals) / len(self.intervals)
            bpm = 60.0 / avg_interval

        # Clamp to 0–1
        features = {
            'loudness_rms': np.clip(loudness_e, 0.0, 1.0),
            'loudness_peak': np.clip(np.clip(rms_n, 0.0, 1.0), 0.0, 1.0),
            'bass': np.clip(bass_e, 0.0, 1.0),
            'mid': np.clip(mid_e, 0.0, 1.0),
            'treble': np.clip(treble_e, 0.0, 1.0),
            'beat': beat,
            'bpm': bpm
        }
        
        self.prev_bass = bass_e
        return features
    
    def _band_energy(self, mag, freqs, f0, f1):
        """
        Compute band energy using Peak/Mean mix.
        This captures sharp transients (hi-hats) better.
        """
        idx = (freqs >= f0) & (freqs < f1)
        if not np.any(idx):
            return 0.0
        
        band_mag = mag[idx]
        
        # Mix of Mean (sustain) and Max (transient)
        # Treble needs more Peak weight to catch hi-hats
        if f0 > 2000:
            val = 0.3 * np.mean(band_mag) + 0.7 * np.max(band_mag)
        else:
            val = 0.7 * np.mean(band_mag) + 0.3 * np.max(band_mag)
            
        return float(val)
    
    def _detect_beat(self, bass_now, threshold=0.08):
        """
        Aggressive onset detection: triggers on rapid rise in bass energy.
        """
        # Calculate flux (positive change)
        flux = bass_now - self.prev_bass
        
        # Debugging beat detection (Verbose)
        # print(f"DEBUG: bass={bass_now:.2f} prev={self.prev_bass:.2f} flux={flux:.2f} thresh={threshold}")
        
        # Check if flux exceeds threshold and we are past refractory period
        is_beat = False
        if flux > threshold:
            if not hasattr(self, 'frames_since_beat'):
                self.frames_since_beat = 10
            
            if self.frames_since_beat > 5: # ~150ms at 30fps
                is_beat = True
                self.frames_since_beat = 0
                # print("DEBUG: >>> BEAT DETECTED <<<")
        
        if hasattr(self, 'frames_since_beat'):
            self.frames_since_beat += 1
            
        return 1.0 if is_beat else 0.0


class Envelope:
    """Exponential moving average (attack/release)."""
    def __init__(self, attack=0.4, release=0.1):
        self.v = 0.0
        self.attack = attack
        self.release = release
    
    def update(self, x):
        if x > self.v:
            self.v = self.attack * x + (1.0 - self.attack) * self.v
        else:
            self.v = self.release * x + (1.0 - self.release) * self.v
        return self.v
