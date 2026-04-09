"""
Audio Quality Checker - Configuration
"""
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

# Upload limits
MAX_FILE_SIZE_MB = 1000  # 1 GB
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Supported audio formats
SUPPORTED_EXTENSIONS = {
    ".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac",
    ".opus", ".webm", ".aiff", ".aif", ".wma", ".amr"
}

SUPPORTED_MIMETYPES = {
    "audio/wav", "audio/x-wav", "audio/wave",
    "audio/mpeg", "audio/mp3",
    "audio/flac", "audio/x-flac",
    "audio/ogg", "audio/vorbis",
    "audio/mp4", "audio/m4a", "audio/x-m4a", "audio/aac",
    "audio/opus",
    "audio/webm", "video/webm",
    "audio/aiff", "audio/x-aiff",
    "audio/x-ms-wma",
    "audio/amr",
    "application/octet-stream",  # Some browsers send this for audio files
}

# Analysis settings
WHISPER_MODEL = "tiny"  # tiny = 75MB, fast, good enough for language detection
LANGUAGE_DETECTION_MAX_SECONDS = 30  # Only analyze first 30s for language
SPEAKER_DETECTION_MAX_SECONDS = 120  # First 2 minutes for speaker diarization (enough for accurate count)

# Quality scoring weights
QUALITY_WEIGHTS = {
    "snr": 0.25,
    "clipping": 0.15,
    "silence_ratio": 0.10,
    "sample_rate": 0.10,
    "bit_depth": 0.05,
    "dynamic_range": 0.10,
    "dc_offset": 0.05,
    "speech_clarity": 0.10,
    "format_quality": 0.10,
}

# Grade mapping
GRADE_MAP = [
    (90, "A+", "Excellent - ready for any project"),
    (80, "A", "Great quality - minor issues at most"),
    (70, "B", "Good - usable for most projects"),
    (60, "C", "Acceptable - has notable issues"),
    (40, "D", "Poor - significant quality problems"),
    (0, "F", "Unusable - needs re-recording"),
]

# Server
HOST = "0.0.0.0"
PORT = 8000
