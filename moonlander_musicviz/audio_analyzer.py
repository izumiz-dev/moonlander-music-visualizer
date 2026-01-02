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
        self.peak_tracks = {
            'bass': 0.01, 'mid': 0.01, 'treble': 0.01, 'rms': 0.01,
            'kick': 0.01, 'snare': 0.01, 'hihat': 0.01
        }
        
        # Rhythm detection state (prev_val, frames_since_onset)
        self.rhythm_state = {
            'kick':  {'prev': 0.0, 'timer': 0},
            'snare': {'prev': 0.0, 'timer': 0},
            'hihat': {'prev': 0.0, 'timer': 0}
        }
        
        # Beat detection (legacy support for BPM)
        self.beat_history = []
        self.beat_history_len = int(2.0 * sr / hop)
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
        
        # === Visual Bands (Smoothed) ===
        # Expert Optimized Crossover:
        # Bass: 40-150Hz -> Kick & Bass guitar core
        # Mid: 150-2500Hz -> Vocal body, snare body, guitar mids
        # Treble: 2500-20000Hz -> Snare snap, hi-hats, vocal air, lead synths/guitars
        bass_raw = self._band_energy(mag, freqs, 40, 150)
        mid_raw = self._band_energy(mag, freqs, 150, 2500)
        treble_raw = self._band_energy(mag, freqs, 2500, 20000)
        
        # === Rhythm Bands (Transient Only) ===
        # Expert Tuning:
        # Kick: 60-150Hz -> Cut sub-bass rumble, focus on attack.
        # Snare: 1.5-4kHz -> Cut vocal/body resonance, focus on "snap" noise.
        # HiHat: 8-16kHz -> Standard high frequency range.
        kick_raw  = self._transient_energy(mag, freqs, 60, 150)
        snare_raw = self._transient_energy(mag, freqs, 1500, 4000)
        hihat_raw = self._transient_energy(mag, freqs, 8000, 16000)

        # Adaptive normalization
        pt = self.peak_tracks
        
        # Expert Review Tuning:
        # Visual bands need slow decay (0.995) for smooth gain control.
        # Rhythm bands need faster decay (0.990) to follow dynamic changes and breaks.
        for k, v in [('bass', bass_raw), ('mid', mid_raw), ('treble', treble_raw), ('rms', rms)]:
            pt[k] = max(pt[k] * 0.995, v)
        for k, v in [('kick', kick_raw), ('snare', snare_raw), ('hihat', hihat_raw)]:
            pt[k] = max(pt[k] * 0.990, v)
        
        def norm(v, p):
            return np.clip(np.power(v / (p + 1e-6), 0.75), 0.0, 1.0)

        # Normalize Visual Bands
        bass_n = norm(bass_raw, pt['bass'])
        mid_n = norm(mid_raw, pt['mid'])
        treble_n = norm(treble_raw, pt['treble'])
        rms_n = norm(rms, pt['rms'])
        
        # Normalize Rhythm Bands
        kick_n = norm(kick_raw, pt['kick'])
        snare_n = norm(snare_raw, pt['snare'])
        hihat_n = norm(hihat_raw, pt['hihat'])

        # Apply envelopes for Visuals
        bass_e = self.env_bass.update(bass_n)
        mid_e = self.env_mid.update(mid_n)
        treble_e = self.env_treble.update(treble_n)
        
        self.env_loudness.release = 0.2
        loudness_e = self.env_loudness.update(rms_n)
        
        # === Rhythm Detection ===
        is_kick  = self._detect_onset('kick', kick_n, threshold=0.10, refractory=4)
        is_snare = self._detect_onset('snare', snare_n, threshold=0.12, refractory=3)
        is_hihat = self._detect_onset('hihat', hihat_n, threshold=0.10, refractory=2)

        # Legacy Beat support (aliased to Kick)
        beat = is_kick
        
        # BPM Estimation (using Kick)
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
            'kick': beat,   # Alias for consistency
            'snare': is_snare,
            'hihat': is_hihat,
            'bpm': bpm
        }
        
        # Legacy support
        self.prev_bass = bass_e
        return features
    
    def _band_energy(self, mag, freqs, f0, f1):
        """
        Compute band energy using Peak/Mean mix for VISUALIZATION.
        Smoothed response for LED radii.
        """
        idx = (freqs >= f0) & (freqs < f1)
        if not np.any(idx):
            return 0.0
        
        band_mag = mag[idx]
        
        # Balanced mix for smooth visuals
        val = 0.6 * np.mean(band_mag) + 0.4 * np.max(band_mag)
        return float(val)

    def _transient_energy(self, mag, freqs, f0, f1):
        """
        Compute band energy using ONLY Peak for RHYTHM DETECTION.
        Ignores sustain/rumble, captures attack transients.
        """
        idx = (freqs >= f0) & (freqs < f1)
        if not np.any(idx):
            return 0.0
        
        band_mag = mag[idx]
        
        # 100% Peak to catch transients
        return float(np.max(band_mag))
    
    def _detect_onset(self, name, val_now, threshold=0.10, refractory=4):
        """
        Generic onset detector using flux (rapid rise) and refractory period.
        """
        state = self.rhythm_state[name]
        
        # Calculate flux
        flux = val_now - state['prev']
        state['prev'] = val_now
        
        is_onset = False
        if flux > threshold:
            if state['timer'] > refractory:
                is_onset = True
                state['timer'] = 0
        
        state['timer'] += 1
        return 1.0 if is_onset else 0.0

        # Note: BPM estimation logic in update() handles the rest.


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
