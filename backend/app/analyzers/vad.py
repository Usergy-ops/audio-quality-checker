"""
Audio Quality Checker - Voice Activity Detector
Uses Silero VAD to detect speech regions.
"""
import torch
import numpy as np
import librosa
from pathlib import Path

from app.models.schemas import SpeechActivityInfo

# Max duration to process for VAD (seconds)
VAD_MAX_SECONDS = 600  # 10 minutes

# Module-level model cache
_vad_model = None
_vad_utils = None


def _get_vad():
    """Lazy-load Silero VAD model (singleton)."""
    global _vad_model, _vad_utils
    if _vad_model is None:
        _vad_model, _vad_utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            trust_repo=True,
        )
    return _vad_model, _vad_utils


def _load_audio_16k(filepath: Path) -> torch.Tensor:
    """Load audio as 16kHz mono tensor using librosa (avoids torchcodec issues)."""
    y, _ = librosa.load(str(filepath), sr=16000, mono=True)
    return torch.FloatTensor(y)


def detect_speech_activity(filepath: Path) -> SpeechActivityInfo:
    """
    Detect speech vs silence/noise using Silero VAD.
    
    Returns SpeechActivityInfo with speech %, regions, longest segments.
    """
    model, utils = _get_vad()
    get_speech_timestamps = utils[0]
    
    # Load audio at 16kHz using librosa (reliable, no torchcodec dependency)
    # Cap duration to avoid slow processing on very long files
    wav = _load_audio_16k(filepath)
    duration = len(wav) / 16000
    
    if duration > VAD_MAX_SECONDS:
        max_samples = int(VAD_MAX_SECONDS * 16000)
        wav = wav[:max_samples]
        print(f"[VAD] Trimmed from {duration:.1f}s to {VAD_MAX_SECONDS}s for processing")
        # Keep original duration for percentage calculations
        analyzed_duration = VAD_MAX_SECONDS
    else:
        analyzed_duration = duration
    
    if analyzed_duration == 0:
        return SpeechActivityInfo(
            speech_percentage=0.0, silence_percentage=100.0,
            speech_regions=[], longest_speech_seconds=0.0,
            longest_silence_seconds=0.0
        )
    
    # Get speech timestamps
    speech_timestamps = get_speech_timestamps(
        wav, model,
        sampling_rate=16000,
        threshold=0.5,
        min_speech_duration_ms=250,
        min_silence_duration_ms=300,
        return_seconds=False,
    )
    
    # Convert to seconds and build regions
    speech_regions = []
    total_speech = 0.0
    longest_speech = 0.0
    
    for ts in speech_timestamps:
        start_sec = ts['start'] / 16000
        end_sec = ts['end'] / 16000
        seg_duration = end_sec - start_sec
        
        total_speech += seg_duration
        longest_speech = max(longest_speech, seg_duration)
        
        speech_regions.append({
            "start_seconds": round(start_sec, 3),
            "end_seconds": round(end_sec, 3),
            "duration_seconds": round(seg_duration, 3),
        })
    
    # Calculate longest silence
    longest_silence = 0.0
    if len(speech_regions) > 0:
        # Silence before first speech
        if speech_regions[0]["start_seconds"] > 0.1:
            longest_silence = speech_regions[0]["start_seconds"]
        
        # Silence between speech segments
        for i in range(1, len(speech_regions)):
            gap = speech_regions[i]["start_seconds"] - speech_regions[i-1]["end_seconds"]
            longest_silence = max(longest_silence, gap)
        
        # Silence after last speech
        trailing = analyzed_duration - speech_regions[-1]["end_seconds"]
        longest_silence = max(longest_silence, trailing)
    else:
        longest_silence = analyzed_duration
    
    speech_pct = (total_speech / analyzed_duration) * 100 if analyzed_duration > 0 else 0
    silence_pct = 100 - speech_pct
    
    return SpeechActivityInfo(
        speech_percentage=round(speech_pct, 2),
        silence_percentage=round(silence_pct, 2),
        speech_regions=speech_regions,
        longest_speech_seconds=round(longest_speech, 3),
        longest_silence_seconds=round(longest_silence, 3),
    )
