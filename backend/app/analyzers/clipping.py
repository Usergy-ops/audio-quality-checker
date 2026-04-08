"""
Audio Quality Checker - Clipping Detector
Detects clipped audio samples and regions.
"""
import numpy as np
from app.models.schemas import ClippingInfo


def detect_clipping(y: np.ndarray, sr: int, threshold: float = 0.99) -> ClippingInfo:
    """
    Detect audio clipping (samples at or near maximum amplitude).
    
    Args:
        y: Audio samples (normalized to [-1, 1])
        sr: Sample rate
        threshold: Amplitude threshold to consider clipping (default 0.99)
    
    Returns ClippingInfo with percentage, count, and clipped regions.
    """
    total_samples = len(y)
    if total_samples == 0:
        return ClippingInfo(
            detected=False, percentage=0.0,
            clipped_samples=0, total_samples=0, regions=[]
        )
    
    # Find clipped samples
    clipped_mask = np.abs(y) >= threshold
    clipped_count = int(np.sum(clipped_mask))
    clipped_pct = (clipped_count / total_samples) * 100
    
    # Find clipped regions (consecutive clipped samples)
    regions = []
    if clipped_count > 0:
        # Find transitions
        diff = np.diff(clipped_mask.astype(int))
        starts = np.where(diff == 1)[0] + 1
        ends = np.where(diff == -1)[0] + 1
        
        # Handle edge cases
        if clipped_mask[0]:
            starts = np.concatenate([[0], starts])
        if clipped_mask[-1]:
            ends = np.concatenate([ends, [total_samples]])
        
        # Build region list (limit to first 50 for performance)
        for i, (start, end) in enumerate(zip(starts, ends)):
            if i >= 50:
                break
            regions.append({
                "start_seconds": round(start / sr, 3),
                "end_seconds": round(end / sr, 3),
                "duration_seconds": round((end - start) / sr, 4),
                "sample_start": int(start),
                "sample_end": int(end),
            })
    
    return ClippingInfo(
        detected=clipped_count > 0,
        percentage=round(clipped_pct, 4),
        clipped_samples=clipped_count,
        total_samples=total_samples,
        regions=regions,
    )
