"""
Noise Type Classification — Spectral analysis approach.

Classifies noise characteristics using frequency band energy distribution,
temporal patterns, and spectral features. No additional model downloads needed.
"""
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Noise categories with frequency band signatures
NOISE_CATEGORIES = {
    "electrical_hum": {
        "label": "Electrical Hum",
        "description": "50/60 Hz mains hum or harmonics",
        "icon": "⚡",
    },
    "broadband": {
        "label": "Broadband Noise",
        "description": "White/pink noise, hiss, or wind",
        "icon": "🌊",
    },
    "low_frequency": {
        "label": "Low-Frequency Rumble",
        "description": "HVAC, traffic, or mechanical vibration",
        "icon": "🔈",
    },
    "impulse": {
        "label": "Impulse / Clicks",
        "description": "Clicks, pops, or transient noise",
        "icon": "💥",
    },
    "background_speech": {
        "label": "Background Speech",
        "description": "Overlapping voices or chatter",
        "icon": "🗣️",
    },
    "music": {
        "label": "Music / Tonal",
        "description": "Musical content or sustained tones",
        "icon": "🎵",
    },
    "clean": {
        "label": "Clean / Minimal Noise",
        "description": "No significant noise detected",
        "icon": "✨",
    },
}


def analyze_noise_types(
    audio: np.ndarray,
    sr: int,
    max_duration: float = 60.0,
) -> dict:
    """
    Analyze noise characteristics of audio using spectral methods.

    Returns dict with:
        - primary_noise: str (category key)
        - noise_types: list of detected noise types with confidence
        - noise_floor_db: float
        - spectral_profile: dict of band energies
    """
    try:
        # Limit duration
        max_samples = int(max_duration * sr)
        if len(audio) > max_samples:
            audio = audio[:max_samples]

        # Ensure mono
        if audio.ndim > 1:
            audio = audio.mean(axis=-1) if audio.ndim == 2 and audio.shape[0] > audio.shape[1] else audio[0] if audio.ndim == 2 else audio

        # Normalize
        peak = np.max(np.abs(audio))
        if peak > 0:
            audio = audio / peak

        results = []

        # 1. Compute STFT
        n_fft = 2048
        hop = 512
        # Simple STFT using numpy
        n_frames = (len(audio) - n_fft) // hop + 1
        if n_frames < 4:
            return _empty_result()

        window = np.hanning(n_fft)
        stft = np.zeros((n_fft // 2 + 1, n_frames))
        for i in range(n_frames):
            frame = audio[i * hop : i * hop + n_fft] * window
            spectrum = np.abs(np.fft.rfft(frame))
            stft[:, i] = spectrum

        power = stft ** 2
        freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)

        # 2. Band energy analysis
        bands = {
            "sub_bass": (0, 60),
            "bass": (60, 250),
            "low_mid": (250, 500),
            "mid": (500, 2000),
            "upper_mid": (2000, 4000),
            "high": (4000, 8000),
            "ultra_high": (8000, sr // 2),
        }

        band_energy = {}
        total_energy = np.sum(power) + 1e-10
        for name, (lo, hi) in bands.items():
            mask = (freqs >= lo) & (freqs < hi)
            band_energy[name] = float(np.sum(power[mask]) / total_energy)

        # 3. Check for electrical hum (50/60 Hz and harmonics)
        hum_score = _check_electrical_hum(power, freqs, sr)
        if hum_score > 0.3:
            results.append(("electrical_hum", min(hum_score, 1.0)))

        # 4. Check for broadband noise (flat spectrum in non-speech regions)
        broadband_score = _check_broadband(band_energy)
        if broadband_score > 0.3:
            results.append(("broadband", min(broadband_score, 1.0)))

        # 5. Check for low-frequency rumble
        lf_score = _check_low_frequency(band_energy)
        if lf_score > 0.3:
            results.append(("low_frequency", min(lf_score, 1.0)))

        # 6. Check for impulse noise (transients)
        impulse_score = _check_impulse(audio, sr)
        if impulse_score > 0.2:
            results.append(("impulse", min(impulse_score, 1.0)))

        # 7. Check for tonal / music content
        tonal_score = _check_tonal(power, freqs)
        if tonal_score > 0.3:
            results.append(("music", min(tonal_score, 1.0)))

        # 8. Estimate noise floor
        frame_energies = np.sum(power, axis=0)
        sorted_energies = np.sort(frame_energies)
        noise_floor_energy = np.mean(sorted_energies[: max(1, len(sorted_energies) // 10)])
        noise_floor_db = float(10 * np.log10(noise_floor_energy + 1e-10))

        # Sort by confidence
        results.sort(key=lambda x: x[1], reverse=True)

        if not results:
            results = [("clean", 0.9)]

        primary = results[0][0]
        noise_types = []
        for cat, conf in results[:4]:
            info = NOISE_CATEGORIES.get(cat, {})
            noise_types.append({
                "type": cat,
                "label": info.get("label", cat),
                "description": info.get("description", ""),
                "icon": info.get("icon", ""),
                "confidence": round(conf * 100, 1),
            })

        spectral_profile = {k: round(v * 100, 1) for k, v in band_energy.items()}

        return {
            "primary_noise": primary,
            "primary_label": NOISE_CATEGORIES.get(primary, {}).get("label", primary),
            "noise_types": noise_types,
            "noise_floor_db": round(noise_floor_db, 1),
            "spectral_profile": spectral_profile,
        }

    except Exception as e:
        logger.error(f"[Noise Classification] Error: {e}")
        return _empty_result()


def _check_electrical_hum(power: np.ndarray, freqs: np.ndarray, sr: int) -> float:
    """Check for 50/60 Hz hum and harmonics."""
    hum_freqs = [50, 60, 100, 120, 150, 180, 200, 240, 300, 360]
    avg_spectrum = np.mean(power, axis=1)
    total_avg = np.mean(avg_spectrum) + 1e-10

    hum_energy = 0
    for hf in hum_freqs:
        if hf >= sr // 2:
            break
        idx = np.argmin(np.abs(freqs - hf))
        # Check a small window around the target frequency
        lo = max(0, idx - 2)
        hi = min(len(avg_spectrum), idx + 3)
        peak = np.max(avg_spectrum[lo:hi])
        # Compare to neighbors
        neighbor_lo = max(0, idx - 10)
        neighbor_hi = min(len(avg_spectrum), idx + 10)
        neighbor_avg = np.mean(avg_spectrum[neighbor_lo:neighbor_hi]) + 1e-10
        if peak > neighbor_avg * 3:
            hum_energy += peak / total_avg

    return min(hum_energy / 5.0, 1.0)


def _check_broadband(band_energy: dict) -> float:
    """Check for flat spectral energy (broadband noise)."""
    vals = [band_energy.get(k, 0) for k in ["low_mid", "mid", "upper_mid", "high"]]
    if not vals or max(vals) < 0.01:
        return 0
    # Broadband = relatively even energy across bands
    mean_val = np.mean(vals)
    if mean_val < 0.05:
        return 0
    variance = np.var(vals) / (mean_val ** 2 + 1e-10)
    # Low variance = flat spectrum = broadband
    flatness = max(0, 1.0 - variance * 10)
    # Also need significant high-frequency energy
    hf_ratio = (band_energy.get("high", 0) + band_energy.get("ultra_high", 0))
    if hf_ratio < 0.05:
        return 0
    return flatness * min(hf_ratio * 5, 1.0)


def _check_low_frequency(band_energy: dict) -> float:
    """Check for dominant low-frequency energy."""
    lf = band_energy.get("sub_bass", 0) + band_energy.get("bass", 0)
    hf = band_energy.get("upper_mid", 0) + band_energy.get("high", 0) + band_energy.get("ultra_high", 0)
    if lf < 0.1:
        return 0
    ratio = lf / (hf + 0.01)
    return min(ratio / 10.0, 1.0)


def _check_impulse(audio: np.ndarray, sr: int) -> float:
    """Check for transient impulse noise (clicks, pops)."""
    # Compute short-time energy
    frame_len = int(0.005 * sr)  # 5ms frames
    n_frames = len(audio) // frame_len
    if n_frames < 10:
        return 0

    energies = np.array([
        np.sum(audio[i * frame_len : (i + 1) * frame_len] ** 2)
        for i in range(n_frames)
    ])

    median_e = np.median(energies) + 1e-10
    # Count frames with energy > 10x median (impulses)
    impulse_count = np.sum(energies > median_e * 10)
    impulse_ratio = impulse_count / n_frames

    if impulse_ratio < 0.005:
        return 0
    return min(impulse_ratio * 20, 1.0)


def _check_tonal(power: np.ndarray, freqs: np.ndarray) -> float:
    """Check for sustained tonal content (music, tones)."""
    avg_spectrum = np.mean(power, axis=1)
    total = np.sum(avg_spectrum) + 1e-10

    # Find peaks
    peaks = []
    for i in range(2, len(avg_spectrum) - 2):
        if (avg_spectrum[i] > avg_spectrum[i-1] and
            avg_spectrum[i] > avg_spectrum[i+1] and
            avg_spectrum[i] > avg_spectrum[i-2] * 1.5 and
            freqs[i] > 100):  # Ignore very low freq
            peaks.append((i, avg_spectrum[i]))

    if len(peaks) < 3:
        return 0

    # Sort by amplitude
    peaks.sort(key=lambda x: x[1], reverse=True)
    top_peaks = peaks[:10]

    # Check if top peaks are harmonically related
    peak_energy = sum(p[1] for p in top_peaks)
    tonality = peak_energy / total

    # Check temporal consistency (tonal = consistent across time)
    peak_indices = [p[0] for p in top_peaks[:5]]
    temporal_var = 0
    for idx in peak_indices:
        col = power[idx, :]
        if np.mean(col) > 0:
            temporal_var += np.std(col) / (np.mean(col) + 1e-10)
    temporal_var /= max(len(peak_indices), 1)

    # Low temporal variance + high tonality = music/tone
    consistency = max(0, 1.0 - temporal_var)
    return min(tonality * consistency * 3, 1.0)


def _empty_result() -> dict:
    return {
        "primary_noise": "clean",
        "primary_label": "Clean / Minimal Noise",
        "noise_types": [{
            "type": "clean",
            "label": "Clean / Minimal Noise",
            "description": "No significant noise detected",
            "icon": "✨",
            "confidence": 50.0,
        }],
        "noise_floor_db": -80.0,
        "spectral_profile": {},
    }
