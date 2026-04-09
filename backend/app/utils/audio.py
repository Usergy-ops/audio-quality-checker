"""
Audio Quality Checker - Audio file utilities
"""
import os
import uuid
import subprocess
import json
from pathlib import Path

import shutil
from datetime import datetime

from app.config import TEMP_DIR, UPLOADS_DIR, SUPPORTED_EXTENSIONS, MAX_FILE_SIZE_BYTES


def save_upload(temp_path: Path, original_filename: str, file_size: int):
    """Save uploaded file to permanent uploads directory with metadata."""
    try:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        ext = Path(original_filename).suffix.lower()
        safe_name = Path(original_filename).stem[:50]  # Truncate long names
        save_name = f"{timestamp}_{safe_name}{ext}"
        dest = UPLOADS_DIR / save_name
        shutil.copy2(str(temp_path), str(dest))
        
        # Save metadata alongside
        meta_path = dest.with_suffix(dest.suffix + ".meta")
        meta_path.write_text(json.dumps({
            "original_filename": original_filename,
            "file_size": file_size,
            "uploaded_at": datetime.utcnow().isoformat() + "Z",
            "saved_as": save_name,
        }, indent=2))
    except Exception:
        pass  # Don't fail analysis if save fails


def validate_file(filename: str, file_size: int) -> tuple[bool, str]:
    """Validate uploaded file by extension and size."""
    ext = Path(filename).suffix.lower()
    
    if ext not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        return False, f"Unsupported format '{ext}'. Supported: {supported}"
    
    if file_size > MAX_FILE_SIZE_BYTES:
        max_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
        file_mb = file_size / (1024 * 1024)
        return False, f"File too large ({file_mb:.1f} MB). Maximum: {max_mb:.0f} MB"
    
    # Minimum file size check (1KB) - empty or near-empty files are invalid
    if file_size < 1024:
        return False, "File too small. Audio files must be at least 1 KB."
    
    return True, ""


def validate_audio_content(filepath: Path) -> tuple[bool, str]:
    """Validate that file contains actual audio content using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=codec_type,duration",
                "-of", "json",
                str(filepath)
            ],
            capture_output=True,
            timeout=10,
        )
        
        if result.returncode != 0:
            stderr = result.stderr.decode()[:200]
            return False, f"Invalid or corrupt audio file: {stderr}"
        
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        
        if not streams:
            return False, "No audio stream found in file. Please upload a valid audio file."
        
        # Check for valid duration
        duration = streams[0].get("duration")
        if duration:
            dur_float = float(duration)
            if dur_float < 0.1:
                return False, "Audio too short. Minimum duration is 0.1 seconds."
            if dur_float > 14400:  # 4 hours
                return False, "Audio too long. Maximum duration is 4 hours."
        
        return True, ""
        
    except subprocess.TimeoutExpired:
        return False, "Audio validation timed out. File may be corrupt."
    except json.JSONDecodeError:
        return False, "Could not parse audio metadata. File may be corrupt."
    except Exception as e:
        return False, f"Error validating audio: {str(e)[:100]}"


def save_temp_file(content: bytes, filename: str) -> Path:
    """Save uploaded file to temp directory with unique name."""
    ext = Path(filename).suffix.lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    filepath = TEMP_DIR / unique_name
    filepath.write_bytes(content)
    return filepath


def cleanup_temp_file(filepath: Path):
    """Remove temporary file."""
    try:
        if filepath and filepath.exists():
            filepath.unlink()
    except Exception:
        pass


def convert_to_wav(input_path: Path) -> Path:
    """Convert any audio format to WAV for consistent processing.
    Returns path to WAV file (may be same as input if already WAV PCM).
    """
    # Check if already WAV
    if input_path.suffix.lower() == ".wav":
        # Verify it's actually PCM WAV we can read
        try:
            probe = get_ffprobe_info(input_path)
            if probe and probe.get("codec_name") in ("pcm_s16le", "pcm_s24le", "pcm_s32le", "pcm_f32le"):
                return input_path
        except Exception:
            pass
    
    # Convert to WAV
    wav_path = input_path.with_suffix(".converted.wav")
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(input_path),
                "-acodec", "pcm_s16le",
                "-ar", "44100",
                "-ac", "1",  # Convert to mono for analysis
                str(wav_path)
            ],
            capture_output=True,
            timeout=120,
            check=True
        )
        return wav_path
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Failed to convert audio: {e.stderr.decode()[:200]}")
    except subprocess.TimeoutExpired:
        raise ValueError("Audio conversion timed out (file may be too large or corrupt)")


def get_ffprobe_info(filepath: Path) -> dict:
    """Get raw ffprobe stream info."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format", "-show_streams",
                str(filepath)
            ],
            capture_output=True,
            timeout=30,
            check=True
        )
        return json.loads(result.stdout)
    except Exception:
        return {}


def smart_sample(audio_data, sr: int, max_seconds: int = 60):
    """Return a representative sample of audio capped at max_seconds.
    For audio longer than max_seconds, take first/middle/last thirds.
    Returns (sampled_audio, original_duration_seconds).
    """
    import numpy as np
    total_samples = len(audio_data)
    max_samples = sr * max_seconds
    original_duration = total_samples / sr

    if total_samples <= max_samples:
        return audio_data, original_duration

    third = max_samples // 3
    mid_start = (total_samples - third) // 2
    start_chunk = audio_data[:third]
    mid_chunk = audio_data[mid_start:mid_start + third]
    end_chunk = audio_data[-third:]
    sampled = np.concatenate([start_chunk, mid_chunk, end_chunk])
    return sampled, original_duration


def format_duration(seconds: float) -> str:
    """Format seconds to HH:MM:SS.ms"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:05.2f}"
    return f"{minutes:02d}:{secs:05.2f}"


def format_file_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024**3):.2f} GB"
    elif size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024**2):.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} KB"
    return f"{size_bytes} bytes"
