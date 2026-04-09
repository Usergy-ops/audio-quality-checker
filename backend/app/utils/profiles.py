"""
Audio Quality Checker - Compliance Spec Profiles
Predefined and customizable compliance specifications for different clients/standards.
"""

# Each profile defines thresholds for compliance checks.
# None = skip that check.

PROFILES = {
    "default": {
        "name": "General AI Data",
        "description": "Common requirements for AI training data",
        "sample_rate_min": 16000,
        "bit_depth_min": 16,
        "channels": "mono",
        "clipping_max_pct": 0.1,
        "snr_min_db": 20,
        "silence_max_pct": 10,
        "format": "lossless_or_256kbps",
    },
    "defined_ai": {
        "name": "AI Data Platform Standard",
        "description": "High-quality AI data platform requirements",
        "sample_rate_min": 48000,
        "bit_depth_min": 24,
        "channels": "mono",
        "clipping_max_pct": 0.01,
        "snr_min_db": 25,
        "silence_max_pct": 5,
        "format": "lossless",
    },
    "appen": {
        "name": "Crowd Platform Standard",
        "description": "Typical crowd-sourced speech collection specs",
        "sample_rate_min": 16000,
        "bit_depth_min": 16,
        "channels": "mono",
        "clipping_max_pct": 0.1,
        "snr_min_db": 15,
        "silence_max_pct": 20,
        "format": "lossless_or_256kbps",
    },
    "common_voice": {
        "name": "Open Speech Dataset",
        "description": "Open-source speech dataset standards",
        "sample_rate_min": 48000,
        "bit_depth_min": 16,
        "channels": "mono",
        "clipping_max_pct": 0.05,
        "snr_min_db": 20,
        "silence_max_pct": 15,
        "format": "lossless_or_256kbps",
    },
    "telephony": {
        "name": "Telephony / Call Center",
        "description": "Telephony-grade audio (8kHz, low bandwidth)",
        "sample_rate_min": 8000,
        "bit_depth_min": 16,
        "channels": "mono",
        "clipping_max_pct": 0.5,
        "snr_min_db": 10,
        "silence_max_pct": 30,
        "format": "any",
    },
    "broadcast": {
        "name": "Broadcast / Podcast",
        "description": "High-quality broadcast audio standards",
        "sample_rate_min": 44100,
        "bit_depth_min": 16,
        "channels": None,  # stereo OK
        "clipping_max_pct": 0.0,
        "snr_min_db": 30,
        "silence_max_pct": 5,
        "format": "lossless",
    },
}


def get_profile(name: str) -> dict:
    """Get a compliance profile by name. Falls back to default."""
    return PROFILES.get(name, PROFILES["default"])


def get_profile_names() -> list[dict]:
    """Return list of available profiles with metadata."""
    return [
        {"id": k, "name": v["name"], "description": v["description"]}
        for k, v in PROFILES.items()
    ]
