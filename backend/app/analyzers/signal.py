"""
Audio Quality Checker - Signal Analyzer
Core signal analysis using librosa: peak, RMS, dynamic range, DC offset.
"""
import numpy as np
import librosa
import soundfile as sf
from pathlib import Path


# Max duration to fully load for signal analysis (seconds).
# For longer files we load the full thing at reduced sample rate.
SIGNAL_MAX_SECONDS = 600  # 10 minutes


def analyze_signal(filepath: Path, sr: int = None) -> dict:
    """
    Perform core signal analysis on audio file.
    
    Returns dict with:
        - peak_amplitude_db
        - rms_level_db
        - dynamic_range_db
        - dc_offset
        - peak_amplitude_linear
        - rms_level_linear
    """
    # Load audio (mono). Cap at SIGNAL_MAX_SECONDS to avoid huge memory usage.
    y, sr_actual = librosa.load(str(filepath), sr=sr, mono=True, duration=SIGNAL_MAX_SECONDS)
    print(f"[Signal Analysis] Loaded {len(y)/sr_actual:.1f}s at {sr_actual}Hz ({len(y)} samples)")
    
    if len(y) == 0:
        raise ValueError("Audio file is empty (no samples)")
    
    # Peak amplitude
    peak_linear = float(np.max(np.abs(y)))
    peak_db = float(20 * np.log10(peak_linear + 1e-10))  # dBFS
    
    # RMS level
    rms = float(np.sqrt(np.mean(y ** 2)))
    rms_db = float(20 * np.log10(rms + 1e-10))  # dBFS
    
    # Dynamic range (difference between peak and RMS of quiet sections)
    # Use windowed RMS for better dynamic range estimation
    frame_length = int(sr_actual * 0.05)  # 50ms frames
    hop_length = frame_length // 2
    rms_frames = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    
    if len(rms_frames) > 0:
        # Remove silent frames (below -60 dB) for dynamic range calc
        rms_db_frames = 20 * np.log10(rms_frames + 1e-10)
        non_silent = rms_db_frames[rms_db_frames > -60]
        
        if len(non_silent) > 1:
            dynamic_range = float(np.max(non_silent) - np.percentile(non_silent, 10))
        else:
            dynamic_range = 0.0
    else:
        dynamic_range = 0.0
    
    # DC offset (mean of signal - should be near 0)
    dc_offset = float(np.mean(y))
    
    return {
        "peak_amplitude_db": round(peak_db, 2),
        "rms_level_db": round(rms_db, 2),
        "dynamic_range_db": round(dynamic_range, 2),
        "dc_offset": round(dc_offset, 6),
        "peak_amplitude_linear": round(peak_linear, 6),
        "rms_level_linear": round(rms, 6),
        "sample_rate": sr_actual,
        "num_samples": len(y),
        "audio_data": y,  # Pass along for other analyzers
        "sr": sr_actual,
    }
