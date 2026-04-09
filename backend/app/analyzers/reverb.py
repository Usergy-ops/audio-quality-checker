"""
Audio Quality Checker - Reverb / Echo Detection
Estimates RT60 (reverberation time) and echo characteristics
using signal processing methods. No additional models needed.
"""
import numpy as np
import logging

logger = logging.getLogger(__name__)


def analyze_reverb(
    audio: np.ndarray,
    sr: int,
    max_duration: float = 30.0,
) -> dict | None:
    """
    Analyze reverb/echo characteristics using:
    1. Energy decay curve → RT60 estimation
    2. Autocorrelation → echo detection
    3. Spectral flatness → diffuse reverb indicator
    4. Early-to-late energy ratio (C50/C80)

    Returns dict with:
        - rt60_seconds: estimated RT60 (time for 60dB decay)
        - rt60_rating: str (dry/moderate/reverberant/very_reverberant)
        - echo_detected: bool
        - echo_delay_ms: float or None
        - echo_strength_db: float or None
        - c50_db: float (clarity index, early vs late energy at 50ms)
        - environment: str (estimated recording environment)
        - reverb_score: float 0-100 (higher = more reverb)
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
            return _dry_result()
        audio = audio / peak

        # 1. RT60 estimation via energy decay
        rt60 = _estimate_rt60(audio, sr)

        # 2. Echo detection via autocorrelation
        echo_detected, echo_delay_ms, echo_strength_db = _detect_echo(audio, sr)

        # 3. Clarity index C50
        c50 = _calculate_clarity(audio, sr, boundary_ms=50)

        # 4. Rate the reverb
        if rt60 is not None:
            if rt60 < 0.3:
                rt60_rating = "dry"
            elif rt60 < 0.8:
                rt60_rating = "moderate"
            elif rt60 < 1.5:
                rt60_rating = "reverberant"
            else:
                rt60_rating = "very_reverberant"
        else:
            rt60_rating = "unknown"

        # 5. Estimate environment
        environment = _estimate_environment(rt60, echo_detected, c50)

        # 6. Reverb score (0 = bone dry, 100 = cathedral)
        reverb_score = _calculate_reverb_score(rt60, echo_strength_db, c50)

        return {
            "rt60_seconds": round(float(rt60), 3) if rt60 is not None else None,
            "rt60_rating": rt60_rating,
            "echo_detected": bool(echo_detected),
            "echo_delay_ms": round(float(echo_delay_ms), 1) if echo_delay_ms else None,
            "echo_strength_db": round(float(echo_strength_db), 1) if echo_strength_db else None,
            "c50_db": round(float(c50), 1) if c50 is not None else None,
            "environment": environment,
            "reverb_score": round(float(reverb_score), 1),
        }

    except Exception as e:
        logger.error(f"[Reverb] Error: {e}")
        return _dry_result()


def _estimate_rt60(audio: np.ndarray, sr: int) -> float | None:
    """
    Estimate RT60 using Schroeder backward integration.
    Process: compute energy decay curve from impulse response,
    then fit a line to find the -60dB decay time.
    """
    # Compute short-time energy
    frame_len = int(0.01 * sr)  # 10ms frames
    hop = frame_len // 2
    n_frames = (len(audio) - frame_len) // hop
    if n_frames < 20:
        return None

    energy = np.array([
        np.sum(audio[i * hop: i * hop + frame_len] ** 2)
        for i in range(n_frames)
    ])

    if np.max(energy) < 1e-10:
        return None

    # Schroeder backward integration
    # Reverse cumulative sum of energy (in dB)
    schroeder = np.cumsum(energy[::-1])[::-1]
    schroeder = schroeder / (schroeder[0] + 1e-10)

    # Convert to dB
    schroeder_db = 10 * np.log10(schroeder + 1e-10)

    # Find the region between -5dB and -25dB for RT60 estimation (Lundeby method)
    start_idx = np.argmax(schroeder_db < -5)
    end_idx = np.argmax(schroeder_db < -25)

    if end_idx <= start_idx or end_idx - start_idx < 5:
        # Not enough decay — very dry recording
        # Use -5 to -15 range instead
        end_idx = np.argmax(schroeder_db < -15)
        if end_idx <= start_idx or end_idx - start_idx < 3:
            return 0.05  # Essentially dry

    # Linear regression on the decay portion
    x = np.arange(start_idx, end_idx)
    y = schroeder_db[start_idx:end_idx]

    if len(x) < 3:
        return 0.05

    # Fit line: y = mx + b
    coeffs = np.polyfit(x, y, 1)
    slope = coeffs[0]  # dB per frame

    if slope >= 0:
        return 0.05  # No decay = dry

    # Convert slope to RT60
    # slope is dB/frame, frame duration = hop/sr seconds
    frame_duration = hop / sr
    db_per_second = slope / frame_duration

    # RT60 = time for 60dB decay
    rt60 = -60.0 / db_per_second

    # Clamp to reasonable range
    return max(0.02, min(rt60, 10.0))


def _detect_echo(audio: np.ndarray, sr: int) -> tuple:
    """
    Detect discrete echoes using autocorrelation.
    Look for peaks in the autocorrelation at delays > 20ms (perceptible echo).
    """
    # Use first 2 seconds max
    n = min(len(audio), sr * 2)
    segment = audio[:n]

    # Compute autocorrelation via FFT
    fft_size = 1
    while fft_size < 2 * n:
        fft_size *= 2

    fft_audio = np.fft.rfft(segment, fft_size)
    acorr = np.fft.irfft(fft_audio * np.conj(fft_audio))
    acorr = acorr[:n]

    # Normalize
    if acorr[0] > 0:
        acorr = acorr / acorr[0]

    # Look for peaks between 20ms and 500ms (perceptible echo range)
    min_delay = int(0.02 * sr)  # 20ms
    max_delay = min(int(0.5 * sr), n - 1)  # 500ms

    if max_delay <= min_delay:
        return False, None, None

    search_region = acorr[min_delay:max_delay]

    # Find the strongest peak
    if len(search_region) < 3:
        return False, None, None

    peak_idx = np.argmax(search_region)
    peak_val = search_region[peak_idx]

    # Echo threshold: autocorrelation > 0.15 at delay > 20ms
    if peak_val > 0.15:
        delay_samples = min_delay + peak_idx
        delay_ms = (delay_samples / sr) * 1000
        strength_db = 20 * np.log10(peak_val + 1e-10)
        return True, delay_ms, strength_db

    return False, None, None


def _calculate_clarity(audio: np.ndarray, sr: int, boundary_ms: int = 50) -> float | None:
    """
    Calculate clarity index C50 (or C80).
    C50 = 10*log10(early energy / late energy)
    Higher C50 = clearer (less reverb). Typical: -5 to +15 dB.
    """
    # Compute energy in short frames
    frame_len = int(0.001 * sr)  # 1ms frames
    n_frames = len(audio) // frame_len
    if n_frames < boundary_ms + 10:
        return None

    energy = np.array([
        np.sum(audio[i * frame_len: (i + 1) * frame_len] ** 2)
        for i in range(n_frames)
    ])

    early = np.sum(energy[:boundary_ms])
    late = np.sum(energy[boundary_ms:])

    if late < 1e-10:
        return 20.0  # Very dry — essentially no late energy

    c50 = 10 * np.log10(early / late)
    return max(-20.0, min(c50, 30.0))


def _estimate_environment(rt60: float | None, echo: bool, c50: float | None) -> str:
    """Estimate the likely recording environment."""
    if rt60 is None:
        return "Unknown"

    if rt60 < 0.15 and not echo:
        return "Recording booth / Anechoic"
    elif rt60 < 0.4 and not echo:
        return "Treated room / Small studio"
    elif rt60 < 0.6:
        return "Office / Small room"
    elif rt60 < 1.0:
        if echo:
            return "Untreated room with reflections"
        return "Medium room / Conference room"
    elif rt60 < 2.0:
        return "Large room / Hall"
    else:
        return "Very large space / Cathedral"


def _calculate_reverb_score(rt60: float | None, echo_db: float | None, c50: float | None) -> float:
    """
    Combined reverb score 0-100.
    0 = perfectly dry, 100 = cathedral.
    """
    score = 0.0

    if rt60 is not None:
        # RT60 contribution (0-70 points)
        # 0.05s = 0pts, 3.0s = 70pts
        score += min(70.0, (rt60 / 3.0) * 70.0)

    if echo_db is not None:
        # Echo contribution (0-20 points)
        # -20dB echo = 5pts, 0dB echo = 20pts
        echo_factor = max(0, (echo_db + 20) / 20.0)
        score += min(20.0, echo_factor * 20.0)

    if c50 is not None:
        # C50 contribution (inverted: low C50 = more reverb, 0-10 points)
        # C50 of +15 = 0pts (dry), C50 of -5 = 10pts (reverberant)
        c50_factor = max(0, (15.0 - c50) / 20.0)
        score += min(10.0, c50_factor * 10.0)

    return max(0, min(100, score))


def _dry_result() -> dict:
    return {
        "rt60_seconds": 0.05,
        "rt60_rating": "dry",
        "echo_detected": False,
        "echo_delay_ms": None,
        "echo_strength_db": None,
        "c50_db": 15.0,
        "environment": "Recording booth / Anechoic",
        "reverb_score": 0.0,
    }
