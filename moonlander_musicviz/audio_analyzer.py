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
        # Tuned for "Guan-Guan" Resonance: Ultra-fast attack, snappy release
        self.env_bass = Envelope(attack=0.90, release=0.25)
        self.env_mid = Envelope(attack=0.95, release=0.10)
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
        
        # Chorus Detection State
        self.energy_history = []
        self.history_len = int(3.0 * (sr / hop)) # 3 seconds history
        self.chorus_threshold = 0.55 # Threshold for chorus detection
        
        # Beat Envelope State
        self.beat_envelope = 0.0
        self.snare_envelope = 0.0
        self.hihat_envelope = 0.0
    
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
        
        # Update Energy History (Chorus Detection)
        self.energy_history.append(rms)
        if len(self.energy_history) > self.history_len:
            self.energy_history.pop(0)
        
        # === Visual Bands (Smoothed) ===
        # Expert Optimized Crossover:
        # Bass: 20-250Hz -> Extended to catch Low-Mid groove & Bass guitar harmonics.
        # Mid: 250-4000Hz -> Focused on Vocal core and Lead synths.
        # Treble: 4000-20000Hz -> Focused on Snap, air, and high-frequency percussion.
        bass_raw = self._band_energy(mag, freqs, 20, 250)
        mid_raw = self._band_energy(mag, freqs, 250, 4000)
        treble_raw = self._band_energy(mag, freqs, 4000, 20000)
        
        # === Rhythm Bands (Transient Only) ===
        # Expert Tuning:
        # Kick: 40-140Hz -> Deep thud.
        # Snare: 1.5-4kHz -> Snap noise.
        # HiHat: 8-16kHz -> High sizzle.
        kick_raw  = self._transient_energy(mag, freqs, 40, 140)
        snare_raw = self._transient_energy(mag, freqs, 1500, 4000)
        hihat_raw = self._transient_energy(mag, freqs, 8000, 16000)

        # Adaptive normalization
        pt = self.peak_tracks
        
        # Expert Review Tuning:
        # Visual bands need slower recovery (0.998) for more stable brightness.
        # Rhythm bands need snappy recovery (0.990) to ensure impact isn't lost.
        for k, v in [('bass', bass_raw), ('mid', mid_raw), ('treble', treble_raw), ('rms', rms)]:
            pt[k] = max(pt[k] * 0.998, v)
        for k, v in [('kick', kick_raw), ('snare', snare_raw), ('hihat', hihat_raw)]:
            pt[k] = max(pt[k] * 0.990, v)
        
        def norm(v, p):
            # Gamma 1.0 (linear) - No boost, more dynamic range
            return np.clip(v / (p + 1e-6), 0.0, 1.0)

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
        
        # === Rhythm Detection (Sharpened) ===
        # Thresholds lowered for better sensitivity (0.15 -> 0.08 for kick)
        is_kick  = self._detect_onset('kick', kick_n, threshold=0.08, refractory=3)
        is_snare = self._detect_onset('snare', snare_n, threshold=0.12, refractory=3)
        is_hihat = self._detect_onset('hihat', hihat_n, threshold=0.12, refractory=2)

        # Beat Envelopes Logic (Faster Decay for Strobe Effect)
        if is_kick: self.beat_envelope = 1.0
        else: self.beat_envelope *= 0.70 
        
        if is_snare: self.snare_envelope = 1.0
        else: self.snare_envelope *= 0.70

        if is_hihat: self.hihat_envelope = 1.0
        else: self.hihat_envelope *= 0.70
        
        # Mix Snare and HiHat for the secondary rhythm channel
        snare_hat_mix = max(self.snare_envelope, self.hihat_envelope)

        # Chorus Detection Logic
        # Normalize history against peak tracker
        energy_density = 0.0
        if self.energy_history:
             raw_density = sum(self.energy_history) / len(self.energy_history)
             # Reuse RMS peak tracker for normalization
             pt['density'] = max(pt.get('density', 0.01) * 0.999, raw_density)
             energy_density = np.clip(raw_density / (pt['density'] + 1e-6), 0.0, 1.0)
        
        is_chorus = energy_density > self.chorus_threshold

        # Clamp to 0–1
        features = {
            'loudness_rms': np.clip(loudness_e, 0.0, 1.0),
            'loudness_peak': np.clip(np.clip(rms_n, 0.0, 1.0), 0.0, 1.0),
            'bass': np.clip(bass_e, 0.0, 1.0),
            'mid': np.clip(mid_e, 0.0, 1.0),
            'treble': np.clip(treble_e, 0.0, 1.0),
            'beat': np.clip(self.beat_envelope, 0.0, 1.0),   # Kick Envelope -> Byte 9
            'perimeter_sparkle': np.clip(snare_hat_mix, 0.0, 1.0), # Snare/Hat Envelope -> Byte 16 (Repurposed)
            'kick': is_kick, 
            'snare': is_snare,
            'hihat': is_hihat,
            'is_chorus': is_chorus,
            'energy_density': energy_density
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
