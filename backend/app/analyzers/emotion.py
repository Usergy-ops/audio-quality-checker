"""
Audio Quality Checker - Emotion / Tone Analysis
Lightweight prosody-based emotion estimation using acoustic features.
No additional model downloads required (uses librosa features).

Analyzes: pitch range, speech rate proxy, energy dynamics, spectral tilt.
Maps to basic emotion dimensions: valence (positive/negative) and arousal (calm/excited).
"""
import numpy as np
import logging

logger = logging.getLogger(__name__)


def analyze_emotion(
    audio: np.ndarray,
    sr: int,
    max_duration: float = 30.0,
) -> dict | None:
    """
    Estimate speech emotion/tone from acoustic prosody features.

    Returns dict with:
        - primary_tone: str (neutral/calm/energetic/tense/warm/flat)
        - valence: float (-1 to 1, negative to positive)
        - arousal: float (0 to 1, calm to excited)
        - confidence: float (0-100)
        - features: dict of extracted acoustic features
        - description: str
    """
    try:
        # Limit duration
        max_samples = int(max_duration * sr)
        if len(audio) > max_samples:
            audio = audio[:max_samples]

        # Ensure mono float32
        if audio.ndim > 1:
            audio = audio.mean(axis=-1) if audio.shape[0] > audio.shape[1] else audio[0]
        audio = audio.astype(np.float32)

        # Normalize
        peak = np.max(np.abs(audio))
        if peak < 1e-6:
            return _neutral_result("Silent audio")

        audio = audio / peak

        # Extract features
        features = {}

        # 1. Pitch analysis (fundamental frequency via autocorrelation)
        pitch_stats = _analyze_pitch(audio, sr)
        features.update(pitch_stats)

        # 2. Energy dynamics
        energy_stats = _analyze_energy(audio, sr)
        features.update(energy_stats)

        # 3. Spectral features
        spectral_stats = _analyze_spectral(audio, sr)
        features.update(spectral_stats)

        # 4. Map features to emotion dimensions
        valence, arousal, tone, description, confidence = _classify_tone(features)

        return {
            "primary_tone": tone,
            "valence": round(float(valence), 2),
            "arousal": round(float(arousal), 2),
            "confidence": round(float(confidence), 1),
            "description": description,
            "features": {k: round(float(v), 3) for k, v in features.items()},
        }

    except Exception as e:
        logger.error(f"[Emotion] Error: {e}")
        return _neutral_result("Analysis error")


def _analyze_pitch(audio: np.ndarray, sr: int) -> dict:
    """Extract pitch-related features using zero-crossing rate as proxy."""
    # Zero-crossing rate (correlates with pitch)
    frame_len = int(0.025 * sr)  # 25ms frames
    hop = int(0.010 * sr)  # 10ms hop
    n_frames = (len(audio) - frame_len) // hop

    if n_frames < 10:
        return {"pitch_mean": 0, "pitch_std": 0, "pitch_range": 0}

    zcr = np.array([
        np.sum(np.abs(np.diff(np.sign(audio[i*hop:i*hop+frame_len])))) / (2 * frame_len)
        for i in range(n_frames)
    ])

    # Convert ZCR to approximate pitch (very rough)
    approx_pitch = zcr * sr  # Rough Hz estimate

    # Filter out obviously non-speech frames (< 50 Hz or > 500 Hz proxy)
    speech_mask = (approx_pitch > 50) & (approx_pitch < 500)
    if np.sum(speech_mask) < 5:
        return {"pitch_mean": 0, "pitch_std": 0, "pitch_range": 0}

    speech_pitch = approx_pitch[speech_mask]

    return {
        "pitch_mean": float(np.mean(speech_pitch)),
        "pitch_std": float(np.std(speech_pitch)),
        "pitch_range": float(np.percentile(speech_pitch, 90) - np.percentile(speech_pitch, 10)),
    }


def _analyze_energy(audio: np.ndarray, sr: int) -> dict:
    """Extract energy dynamics."""
    frame_len = int(0.025 * sr)
    hop = int(0.010 * sr)
    n_frames = (len(audio) - frame_len) // hop

    if n_frames < 10:
        return {"energy_mean": 0, "energy_std": 0, "energy_range_db": 0}

    energy = np.array([
        np.sqrt(np.mean(audio[i*hop:i*hop+frame_len] ** 2))
        for i in range(n_frames)
    ])

    # Filter out silence
    active = energy > np.max(energy) * 0.05
    if np.sum(active) < 5:
        return {"energy_mean": 0, "energy_std": 0, "energy_range_db": 0}

    active_energy = energy[active]
    energy_db = 20 * np.log10(active_energy + 1e-10)

    return {
        "energy_mean": float(np.mean(active_energy)),
        "energy_std": float(np.std(active_energy)),
        "energy_range_db": float(np.percentile(energy_db, 90) - np.percentile(energy_db, 10)),
    }


def _analyze_spectral(audio: np.ndarray, sr: int) -> dict:
    """Extract spectral features (brightness, flatness)."""
    n_fft = 2048
    hop = 512
    n_frames = (len(audio) - n_fft) // hop

    if n_frames < 5:
        return {"spectral_centroid": 0, "spectral_flatness": 0}

    window = np.hanning(n_fft)
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)

    centroids = []
    flatnesses = []

    for i in range(n_frames):
        frame = audio[i*hop:i*hop+n_fft] * window
        mag = np.abs(np.fft.rfft(frame))
        mag_sum = np.sum(mag) + 1e-10

        # Spectral centroid (brightness)
        centroid = np.sum(freqs * mag) / mag_sum
        centroids.append(centroid)

        # Spectral flatness (tonal vs noise)
        geo_mean = np.exp(np.mean(np.log(mag + 1e-10)))
        arith_mean = np.mean(mag) + 1e-10
        flatness = geo_mean / arith_mean
        flatnesses.append(flatness)

    return {
        "spectral_centroid": float(np.mean(centroids)),
        "spectral_flatness": float(np.mean(flatnesses)),
    }


def _classify_tone(features: dict) -> tuple:
    """
    Map acoustic features to emotion dimensions and tone label.
    Returns (valence, arousal, tone, description, confidence).
    """
    pitch_mean = features.get("pitch_mean", 0)
    pitch_std = features.get("pitch_std", 0)
    pitch_range = features.get("pitch_range", 0)
    energy_std = features.get("energy_std", 0)
    energy_range = features.get("energy_range_db", 0)
    centroid = features.get("spectral_centroid", 0)

    # No speech detected
    if pitch_mean < 10:
        return 0, 0, "non_speech", "No speech content detected", 30.0

    # Arousal (energy + pitch variation + spectral brightness)
    arousal = 0.0
    arousal += min(1.0, energy_range / 30.0) * 0.35  # Energy range contribution
    arousal += min(1.0, pitch_range / 150.0) * 0.35  # Pitch range contribution
    arousal += min(1.0, centroid / 3000.0) * 0.3  # Brightness contribution
    arousal = max(0, min(1, arousal))

    # Valence (pitch height + pitch variation = more positive; low flat = negative)
    valence = 0.0
    valence += (min(pitch_mean, 300) - 150) / 300.0  # Higher pitch = more positive
    valence += min(1.0, pitch_range / 200.0) * 0.3  # More variation = more positive
    valence = max(-1, min(1, valence))

    # Map to tone
    if arousal < 0.25:
        if valence < -0.1:
            tone = "flat"
            description = "Flat, monotone delivery with low energy"
        else:
            tone = "calm"
            description = "Calm, measured speaking style"
    elif arousal < 0.5:
        if valence > 0.1:
            tone = "warm"
            description = "Warm, conversational tone with moderate energy"
        elif valence < -0.1:
            tone = "tense"
            description = "Tense or restrained delivery"
        else:
            tone = "neutral"
            description = "Neutral, balanced speaking style"
    else:
        if valence > 0.1:
            tone = "energetic"
            description = "Energetic, animated speaking style"
        elif valence < -0.1:
            tone = "intense"
            description = "Intense, forceful delivery"
        else:
            tone = "dynamic"
            description = "Dynamic delivery with high variation"

    # Confidence (based on how much speech-like content we found)
    confidence = min(80.0, 30.0 + pitch_mean / 5.0 + energy_range)

    return valence, arousal, tone, description, confidence


def _neutral_result(reason: str) -> dict:
    return {
        "primary_tone": "non_speech",
        "valence": 0.0,
        "arousal": 0.0,
        "confidence": 10.0,
        "description": reason,
        "features": {},
    }
