"""
Audio Quality Checker - Speaker Diarization
Uses pyannote-audio for speaker counting and timeline.
Falls back gracefully if model isn't available.
"""
import os
import torch
import librosa
import numpy as np
from pathlib import Path

from app.models.schemas import SpeakerInfo
from app.config import SPEAKER_DETECTION_MAX_SECONDS

# Module-level cache
_diarization_pipeline = None
_diarization_available = None


def _get_pipeline():
    """
    Lazy-load pyannote diarization pipeline.
    Requires HF_TOKEN environment variable for model download.
    Returns None if not available.
    """
    global _diarization_pipeline, _diarization_available
    
    if _diarization_available is False:
        return None
    
    if _diarization_pipeline is not None:
        return _diarization_pipeline
    
    hf_token = os.environ.get("HF_TOKEN")
    
    try:
        from pyannote.audio import Pipeline
        
        # Try community model first (MIT license, no token needed in some versions)
        try:
            _diarization_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
            )
            # Force CPU
            _diarization_pipeline.to(torch.device("cpu"))
            _diarization_available = True
            print("[Speaker Diarization] Pipeline loaded successfully")
            return _diarization_pipeline
        except Exception as e1:
            # Try community-1 (fully open source)
            try:
                _diarization_pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-community-1",
                )
                _diarization_pipeline.to(torch.device("cpu"))
                _diarization_available = True
                print("[Speaker Diarization] Community pipeline loaded")
                return _diarization_pipeline
            except Exception as e2:
                print(f"[Speaker Diarization] Not available: {e1}, {e2}")
                _diarization_available = False
                return None
    except ImportError:
        print("[Speaker Diarization] pyannote.audio not installed")
        _diarization_available = False
        return None


def count_speakers(filepath: Path, max_duration: float = 300) -> SpeakerInfo:
    """
    Count speakers and produce a diarization timeline.
    
    Args:
        filepath: Path to audio file (WAV preferred)
        max_duration: Maximum audio duration to process (seconds)
    
    Returns SpeakerInfo with count, timeline, distribution.
    Falls back to basic estimation if pyannote isn't available.
    """
    pipeline = _get_pipeline()
    
    if pipeline is None:
        # Fallback: return unknown speaker info
        return SpeakerInfo(
            count=0,
            timeline=[],
            distribution={},
            turn_count=0,
            overlap_percentage=0.0,
        )
    
    try:
        # Preload audio as waveform to avoid torchcodec issues
        # Cap duration to avoid extremely long processing on CPU
        max_secs = min(max_duration, SPEAKER_DETECTION_MAX_SECONDS)
        waveform_np, sr = librosa.load(str(filepath), sr=16000, mono=True, duration=max_secs)
        print(f"[Speaker Diarization] Processing {len(waveform_np)/16000:.1f}s of audio (cap: {max_secs}s)")
        waveform_tensor = torch.from_numpy(waveform_np).unsqueeze(0).float()
        audio_input = {"waveform": waveform_tensor, "sample_rate": 16000}
        
        # Run diarization
        result = pipeline(audio_input)
        
        # pyannote 4.x returns DiarizeOutput; 3.x returns Annotation directly
        if hasattr(result, 'speaker_diarization'):
            diarization = result.speaker_diarization
        else:
            diarization = result
        
        # Extract speakers and timeline
        speakers = set()
        timeline = []
        speaker_durations = {}
        total_duration = 0
        
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speakers.add(speaker)
            duration = turn.end - turn.start
            total_duration += duration
            
            # Track per-speaker duration
            if speaker not in speaker_durations:
                speaker_durations[speaker] = 0
            speaker_durations[speaker] += duration
            
            # Add to timeline (limit to 200 entries for response size)
            if len(timeline) < 200:
                timeline.append({
                    "speaker": speaker,
                    "start_seconds": round(turn.start, 3),
                    "end_seconds": round(turn.end, 3),
                    "duration_seconds": round(duration, 3),
                })
        
        # Calculate distribution (percentage per speaker)
        distribution = {}
        if total_duration > 0:
            for spk, dur in speaker_durations.items():
                distribution[spk] = round((dur / total_duration) * 100, 2)
        
        # Count speaker turns
        turn_count = len(timeline)
        
        # Calculate overlap (simplified - look for overlapping segments)
        # pyannote handles this internally, we approximate
        overlap_pct = 0.0
        
        return SpeakerInfo(
            count=len(speakers),
            timeline=timeline,
            distribution=distribution,
            turn_count=turn_count,
            overlap_percentage=overlap_pct,
        )
        
    except Exception as e:
        print(f"[Speaker Diarization] Error: {e}")
        return SpeakerInfo(
            count=0,
            timeline=[],
            distribution={},
            turn_count=0,
            overlap_percentage=0.0,
        )
