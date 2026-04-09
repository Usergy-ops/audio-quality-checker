"""
Audio Quality Checker - Transcription Preview
Uses Whisper (already loaded for language detection) to transcribe
the first N seconds of audio as a preview.
"""
import numpy as np
import logging
from pathlib import Path

from app.config import WHISPER_MODEL

logger = logging.getLogger(__name__)

# Reuse the model from language detector
_whisper_model = None


def _get_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        _whisper_model = whisper.load_model(WHISPER_MODEL)
    return _whisper_model


TRANSCRIPTION_MAX_SECONDS = 30  # Only transcribe first 30s


def transcribe_preview(
    filepath: Path = None,
    audio_data: np.ndarray = None,
    sample_rate: int = 16000,
    language: str = None,
) -> dict | None:
    """
    Transcribe the first 30 seconds of audio.

    Returns dict with:
        - text: str (full transcription)
        - segments: list of {start, end, text}
        - word_count: int
        - duration_transcribed: float
        - language_used: str
    """
    try:
        import whisper

        if audio_data is not None:
            audio = audio_data.copy()
            if audio.ndim > 1:
                audio = audio.mean(axis=-1) if audio.ndim == 2 and audio.shape[0] > audio.shape[1] else audio[0]

            # Resample to 16kHz if needed
            if sample_rate != 16000:
                import librosa
                audio = librosa.resample(audio, orig_sr=sample_rate, target_sr=16000)
                sample_rate = 16000

            # Cap at max seconds
            max_samples = TRANSCRIPTION_MAX_SECONDS * sample_rate
            if len(audio) > max_samples:
                audio = audio[:max_samples]

            audio = audio.astype(np.float32)
        elif filepath:
            audio = whisper.load_audio(str(filepath))
            max_samples = TRANSCRIPTION_MAX_SECONDS * 16000
            if len(audio) > max_samples:
                audio = audio[:max_samples]
        else:
            return None

        logger.info(f"[Transcription] Transcribing {len(audio)/16000:.1f}s of audio")

        model = _get_model()

        # Use detected language if available, otherwise let Whisper auto-detect
        options = {
            "fp16": False,
            "verbose": False,
        }
        if language:
            options["language"] = language

        result = model.transcribe(audio, **options)

        text = result.get("text", "").strip()
        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": round(seg["start"], 2),
                "end": round(seg["end"], 2),
                "text": seg["text"].strip(),
            })

        duration_transcribed = len(audio) / 16000
        word_count = len(text.split()) if text else 0

        logger.info(f"[Transcription] Got {word_count} words in {duration_transcribed:.1f}s")

        return {
            "text": text,
            "segments": segments[:50],  # Cap segments
            "word_count": word_count,
            "duration_transcribed": round(duration_transcribed, 1),
            "language_used": result.get("language", language or "unknown"),
        }

    except Exception as e:
        logger.error(f"[Transcription] Error: {e}")
        return None
