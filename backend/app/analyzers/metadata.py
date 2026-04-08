"""
Audio Quality Checker - Metadata Extractor
Uses ffprobe to extract file information.
"""
import json
import subprocess
from pathlib import Path

from app.models.schemas import FileInfo
from app.utils.audio import format_duration, format_file_size


def extract_metadata(filepath: Path, original_filename: str, file_size: int) -> FileInfo:
    """
    Extract audio file metadata using ffprobe.
    Returns FileInfo with format, codec, duration, sample rate, etc.
    """
    probe_data = _run_ffprobe(filepath)
    
    # Get format info
    fmt = probe_data.get("format", {})
    
    # Find the audio stream
    audio_stream = None
    for stream in probe_data.get("streams", []):
        if stream.get("codec_type") == "audio":
            audio_stream = stream
            break
    
    if not audio_stream:
        raise ValueError("No audio stream found in file")
    
    # Extract values
    duration = float(fmt.get("duration", audio_stream.get("duration", 0)))
    sample_rate = int(audio_stream.get("sample_rate", 0))
    channels = int(audio_stream.get("channels", 0))
    bit_rate = _safe_int(fmt.get("bit_rate", audio_stream.get("bit_rate")))
    bit_depth = _extract_bit_depth(audio_stream)
    codec = audio_stream.get("codec_long_name", audio_stream.get("codec_name", "unknown"))
    codec_short = audio_stream.get("codec_name", "unknown")
    format_name = fmt.get("format_long_name", fmt.get("format_name", "unknown"))
    channel_layout = audio_stream.get("channel_layout", _guess_channel_layout(channels))
    
    return FileInfo(
        filename=original_filename,
        format=format_name,
        codec=codec,
        duration_seconds=round(duration, 3),
        duration_formatted=format_duration(duration),
        sample_rate=sample_rate,
        bit_rate=bit_rate,
        bit_depth=bit_depth,
        channels=channels,
        channel_layout=channel_layout,
        file_size_bytes=file_size,
        file_size_formatted=format_file_size(file_size),
    )


def _run_ffprobe(filepath: Path) -> dict:
    """Run ffprobe and return parsed JSON output."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(filepath)
            ],
            capture_output=True,
            timeout=30,
            check=True,
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        raise ValueError(f"ffprobe failed: {e.stderr.decode()[:200]}")
    except subprocess.TimeoutExpired:
        raise ValueError("ffprobe timed out — file may be corrupt")
    except json.JSONDecodeError:
        raise ValueError("Failed to parse ffprobe output")


def _extract_bit_depth(stream: dict) -> int | None:
    """Extract bit depth from stream info."""
    # Direct bits_per_sample field
    bps = stream.get("bits_per_sample")
    if bps and int(bps) > 0:
        return int(bps)
    
    # Try bits_per_raw_sample
    bprs = stream.get("bits_per_raw_sample")
    if bprs and int(bprs) > 0:
        return int(bprs)
    
    # Infer from codec name
    codec = stream.get("codec_name", "")
    if "s16" in codec or "16le" in codec or "16be" in codec:
        return 16
    elif "s24" in codec or "24le" in codec or "24be" in codec:
        return 24
    elif "s32" in codec or "32le" in codec or "32be" in codec or "f32" in codec:
        return 32
    elif "s8" in codec or "u8" in codec:
        return 8
    
    # For lossy formats, bit depth isn't really applicable
    lossy_codecs = {"mp3", "aac", "vorbis", "opus", "wma", "amr_nb", "amr_wb"}
    if codec in lossy_codecs:
        return None
    
    return None


def _guess_channel_layout(channels: int) -> str:
    """Guess channel layout from channel count."""
    layouts = {
        1: "mono",
        2: "stereo",
        3: "2.1",
        4: "quad",
        5: "5.0",
        6: "5.1",
        8: "7.1",
    }
    return layouts.get(channels, f"{channels}ch")


def _safe_int(value) -> int | None:
    """Safely convert to int, return None if not possible."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
