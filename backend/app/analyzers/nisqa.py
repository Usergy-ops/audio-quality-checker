"""
Audio Quality Checker - NISQA Speech Quality Assessment
Uses NISQA (Non-Intrusive Speech Quality Assessment) for MOS prediction.
Provides industry-standard MOS score (1-5) plus sub-dimensions.
"""
import numpy as np
import torch
import librosa

from app.models.schemas import SpeechQualityInfo

# Module-level model cache
_nisqa_model = None

# Max duration to analyze (seconds) — NISQA works on short segments
NISQA_MAX_SECONDS = 30


def _get_nisqa():
    """Lazy-load NISQA model (singleton)."""
    global _nisqa_model
    if _nisqa_model is None:
        from torchmetrics.audio import NonIntrusiveSpeechQualityAssessment
        _nisqa_model = NonIntrusiveSpeechQualityAssessment(16000)
    return _nisqa_model


def _mos_to_rating(mos: float) -> str:
    """Convert MOS score to human-readable rating."""
    if mos >= 4.0:
        return "Excellent"
    elif mos >= 3.5:
        return "Good"
    elif mos >= 3.0:
        return "Fair"
    elif mos >= 2.5:
        return "Poor"
    else:
        return "Bad"


def assess_speech_quality(
    audio_data: np.ndarray = None,
    sample_rate: int = 16000,
    filepath=None,
) -> SpeechQualityInfo:
    """
    Assess speech quality using NISQA neural model.
    
    Returns MOS (1-5) plus sub-scores for:
    - noisiness: how noisy the signal is (1=very noisy, 5=clean)
    - coloration: spectral distortion (1=distorted, 5=natural)
    - discontinuity: temporal artifacts (1=choppy, 5=smooth)
    - loudness: appropriate level (1=too quiet/loud, 5=good)
    """
    model = _get_nisqa()

    if audio_data is not None:
        if sample_rate != 16000:
            audio_16k = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=16000)
        else:
            audio_16k = audio_data
    elif filepath is not None:
        audio_16k, _ = librosa.load(str(filepath), sr=16000, mono=True)
    else:
        return SpeechQualityInfo(
            mos=1.0, mos_rating="Bad",
            noisiness=1.0, coloration=1.0,
            discontinuity=1.0, loudness=1.0,
        )

    # Cap duration
    max_samples = NISQA_MAX_SECONDS * 16000
    audio_16k = audio_16k[:max_samples]

    # NISQA needs at least 1 second
    if len(audio_16k) < 16000:
        # Pad short audio
        audio_16k = np.pad(audio_16k, (0, 16000 - len(audio_16k)))

    print(f"[NISQA] Assessing {len(audio_16k)/16000:.1f}s of audio (cap: {NISQA_MAX_SECONDS}s)")

    waveform = torch.FloatTensor(audio_16k)
    
    with torch.no_grad():
        scores = model(waveform)

    # scores: [mos, noisiness, coloration, discontinuity, loudness]
    mos = round(float(scores[0].clamp(1.0, 5.0)), 2)
    noisiness = round(float(scores[1].clamp(1.0, 5.0)), 2)
    coloration = round(float(scores[2].clamp(1.0, 5.0)), 2)
    discontinuity = round(float(scores[3].clamp(1.0, 5.0)), 2)
    loudness_score = round(float(scores[4].clamp(1.0, 5.0)), 2)

    return SpeechQualityInfo(
        mos=mos,
        mos_rating=_mos_to_rating(mos),
        noisiness=noisiness,
        coloration=coloration,
        discontinuity=discontinuity,
        loudness=loudness_score,
    )
