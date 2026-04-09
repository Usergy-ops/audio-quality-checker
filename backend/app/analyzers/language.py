"""
Audio Quality Checker - Language Detector
Uses OpenAI Whisper to detect the language of audio.
"""
import numpy as np
import whisper
from pathlib import Path

from app.config import WHISPER_MODEL, LANGUAGE_DETECTION_MAX_SECONDS
from app.models.schemas import LanguageInfo

# Module-level model cache (loaded once, reused)
_whisper_model = None


def _get_model():
    """Lazy-load Whisper model (singleton)."""
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = whisper.load_model(WHISPER_MODEL)
    return _whisper_model


# Language code to name mapping (common ones)
LANGUAGE_NAMES = {
    "en": "English", "zh": "Chinese", "de": "German", "es": "Spanish",
    "ru": "Russian", "ko": "Korean", "fr": "French", "ja": "Japanese",
    "pt": "Portuguese", "tr": "Turkish", "pl": "Polish", "ca": "Catalan",
    "nl": "Dutch", "ar": "Arabic", "sv": "Swedish", "it": "Italian",
    "id": "Indonesian", "hi": "Hindi", "fi": "Finnish", "vi": "Vietnamese",
    "he": "Hebrew", "uk": "Ukrainian", "el": "Greek", "ms": "Malay",
    "cs": "Czech", "ro": "Romanian", "da": "Danish", "hu": "Hungarian",
    "ta": "Tamil", "no": "Norwegian", "th": "Thai", "ur": "Urdu",
    "hr": "Croatian", "bg": "Bulgarian", "lt": "Lithuanian", "la": "Latin",
    "mi": "Maori", "ml": "Malayalam", "cy": "Welsh", "sk": "Slovak",
    "te": "Telugu", "fa": "Persian", "lv": "Latvian", "bn": "Bengali",
    "sr": "Serbian", "az": "Azerbaijani", "sl": "Slovenian", "kn": "Kannada",
    "et": "Estonian", "mk": "Macedonian", "br": "Breton", "eu": "Basque",
    "is": "Icelandic", "hy": "Armenian", "ne": "Nepali", "mn": "Mongolian",
    "bs": "Bosnian", "kk": "Kazakh", "sq": "Albanian", "sw": "Swahili",
    "gl": "Galician", "mr": "Marathi", "pa": "Punjabi", "si": "Sinhala",
    "km": "Khmer", "sn": "Shona", "yo": "Yoruba", "so": "Somali",
    "af": "Afrikaans", "oc": "Occitan", "ka": "Georgian", "be": "Belarusian",
    "tg": "Tajik", "sd": "Sindhi", "gu": "Gujarati", "am": "Amharic",
    "yi": "Yiddish", "lo": "Lao", "uz": "Uzbek", "fo": "Faroese",
    "ht": "Haitian Creole", "ps": "Pashto", "tk": "Turkmen", "nn": "Nynorsk",
    "mt": "Maltese", "sa": "Sanskrit", "lb": "Luxembourgish", "my": "Myanmar",
    "bo": "Tibetan", "tl": "Tagalog", "mg": "Malagasy", "as": "Assamese",
    "tt": "Tatar", "haw": "Hawaiian", "ln": "Lingala", "ha": "Hausa",
    "ba": "Bashkir", "jw": "Javanese", "su": "Sundanese",
}


def detect_language(filepath: Path) -> LanguageInfo:
    """
    Detect the language of an audio file using Whisper.
    Only processes the first N seconds (configurable) for speed.
    
    Returns LanguageInfo with detected language, confidence, and alternatives.
    """
    model = _get_model()
    
    # Load only the first N seconds (no need to load entire file)
    import librosa
    audio_np, _ = librosa.load(str(filepath), sr=16000, mono=True, duration=LANGUAGE_DETECTION_MAX_SECONDS)
    audio = audio_np.astype(np.float32)
    print(f"[Language Detection] Processing {len(audio)/16000:.1f}s of audio (cap: {LANGUAGE_DETECTION_MAX_SECONDS}s)")
    
    # Pad/trim to 30 seconds (Whisper's expected input)
    audio = whisper.pad_or_trim(audio)
    
    # Make log-Mel spectrogram
    mel = whisper.log_mel_spectrogram(audio).to(model.device)
    
    # Detect language
    _, probs = model.detect_language(mel)
    
    # Sort by probability
    sorted_langs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    
    # Top language
    top_lang = sorted_langs[0][0]
    top_conf = sorted_langs[0][1]
    
    # Alternatives (top 5 excluding the winner)
    alternatives = []
    for lang, prob in sorted_langs[1:6]:
        if prob > 0.01:  # Only include if >1% probability
            alternatives.append({
                "language": lang,
                "name": LANGUAGE_NAMES.get(lang, lang),
                "confidence": round(prob * 100, 2),
            })
    
    return LanguageInfo(
        detected=top_lang,
        name=LANGUAGE_NAMES.get(top_lang, top_lang),
        confidence=round(top_conf * 100, 2),
        alternatives=alternatives,
    )
