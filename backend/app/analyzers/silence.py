"""
Audio Quality Checker - Silence Analyzer
Detects silent regions and calculates silence percentage.
"""
import numpy as np
import librosa
from app.models.schemas import SilenceInfo


def analyze_silence(
    y: np.ndarray,
    sr: int,
    silence_threshold_db: float = -40.0,
    min_silence_duration: float = 0.3,
) -> SilenceInfo:
    """
    Analyze silence in audio file.
    
    Args:
        y: Audio samples
        sr: Sample rate
        silence_threshold_db: dB threshold below which is considered silence
        min_silence_duration: Minimum duration (seconds) to count as a silent region
    
    Returns SilenceInfo with percentage, regions, and durations.
    """
    duration = len(y) / sr
    if duration == 0:
        return SilenceInfo(
            percentage=0.0, total_silence_seconds=0.0,
            regions=[], longest_silence_seconds=0.0
        )
    
    # Calculate RMS energy in frames
    frame_length = int(sr * 0.025)  # 25ms frames
    hop_length = int(sr * 0.010)    # 10ms hop
    
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    rms_db = 20 * np.log10(rms + 1e-10)
    
    # Mark silent frames
    silent_mask = rms_db < silence_threshold_db
    
    # Find silent regions
    regions = []
    total_silence = 0.0
    longest_silence = 0.0
    
    # Find transitions
    if len(silent_mask) > 0:
        diff = np.diff(silent_mask.astype(int))
        starts = np.where(diff == 1)[0] + 1
        ends = np.where(diff == -1)[0] + 1
        
        # Handle edge cases
        if silent_mask[0]:
            starts = np.concatenate([[0], starts])
        if silent_mask[-1]:
            ends = np.concatenate([ends, [len(silent_mask)]])
        
        for start_frame, end_frame in zip(starts, ends):
            start_sec = start_frame * hop_length / sr
            end_sec = end_frame * hop_length / sr
            silence_dur = end_sec - start_sec
            
            if silence_dur >= min_silence_duration:
                total_silence += silence_dur
                longest_silence = max(longest_silence, silence_dur)
                
                # Limit stored regions to 100
                if len(regions) < 100:
                    regions.append({
                        "start_seconds": round(start_sec, 3),
                        "end_seconds": round(end_sec, 3),
                        "duration_seconds": round(silence_dur, 3),
                    })
    
    silence_pct = (total_silence / duration) * 100 if duration > 0 else 0
    
    return SilenceInfo(
        percentage=round(silence_pct, 2),
        total_silence_seconds=round(total_silence, 3),
        regions=regions,
        longest_silence_seconds=round(longest_silence, 3),
    )
