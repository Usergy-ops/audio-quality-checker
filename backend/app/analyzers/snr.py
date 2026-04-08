"""
Audio Quality Checker - SNR Calculator
Estimates Signal-to-Noise Ratio.
"""
import numpy as np
import librosa


def calculate_snr(y: np.ndarray, sr: int) -> dict:
    """
    Estimate Signal-to-Noise Ratio (SNR) of audio.
    
    Uses a segmented approach:
    1. Compute RMS energy per frame
    2. Separate "signal" frames (high energy) from "noise" frames (low energy)
    3. SNR = 20 * log10(rms_signal / rms_noise)
    
    Returns dict with snr_db, noise_floor_db, signal_level_db
    """
    if len(y) == 0:
        return {"snr_db": 0.0, "noise_floor_db": -96.0, "signal_level_db": -96.0}
    
    # Calculate RMS in frames
    frame_length = int(sr * 0.05)  # 50ms frames
    hop_length = frame_length // 2
    
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    
    if len(rms) == 0:
        return {"snr_db": 0.0, "noise_floor_db": -96.0, "signal_level_db": -96.0}
    
    # Convert to dB
    rms_db = 20 * np.log10(rms + 1e-10)
    
    # Use percentile-based separation
    # Bottom 10% = noise estimate, Top 10% = signal estimate
    noise_floor_db = float(np.percentile(rms_db, 10))
    signal_level_db = float(np.percentile(rms_db, 90))
    
    # SNR
    snr_db = signal_level_db - noise_floor_db
    
    # Alternative: Use a threshold to separate speech from noise
    # Median as threshold (adaptive)
    median_db = float(np.median(rms_db))
    
    # Noise frames = below median - 6dB
    noise_threshold = median_db - 6
    noise_frames = rms[rms_db < noise_threshold]
    signal_frames = rms[rms_db >= median_db]
    
    if len(noise_frames) > 0 and len(signal_frames) > 0:
        rms_noise = float(np.mean(noise_frames))
        rms_signal = float(np.mean(signal_frames))
        
        if rms_noise > 1e-10:
            snr_adaptive = float(20 * np.log10(rms_signal / rms_noise))
            # Use the more conservative (lower) estimate
            snr_db = min(snr_db, snr_adaptive)
    
    return {
        "snr_db": round(max(snr_db, 0), 2),  # SNR can't be negative in practice
        "noise_floor_db": round(noise_floor_db, 2),
        "signal_level_db": round(signal_level_db, 2),
    }
