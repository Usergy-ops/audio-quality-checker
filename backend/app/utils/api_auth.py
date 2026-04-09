"""
Audio Quality Checker - API Key Authentication & Rate Limiting

Simple file-based API key management. Keys are stored in a JSON file.
Rate limiting uses an in-memory sliding window (resets on server restart).
"""
import json
import time
import hashlib
import secrets
import logging
from pathlib import Path
from collections import defaultdict
from functools import wraps

from fastapi import Request, HTTPException, Depends
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

# API keys file
API_KEYS_FILE = Path(__file__).parent.parent.parent / "api_keys.json"

# Rate limit: requests per minute per key
RATE_LIMIT_RPM = 30
RATE_WINDOW_SECONDS = 60

# In-memory rate tracking
_rate_tracker: dict[str, list[float]] = defaultdict(list)

# API key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _load_keys() -> dict:
    """Load API keys from file."""
    if not API_KEYS_FILE.exists():
        return {}
    try:
        with open(API_KEYS_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_keys(keys: dict):
    """Save API keys to file."""
    with open(API_KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=2)


def generate_api_key(name: str, tier: str = "free") -> dict:
    """
    Generate a new API key.
    Tiers: free (30 rpm), pro (120 rpm), unlimited (no limit)
    """
    raw_key = f"aqc_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    keys = _load_keys()
    keys[key_hash] = {
        "name": name,
        "tier": tier,
        "created": time.time(),
        "enabled": True,
        "requests": 0,
    }
    _save_keys(keys)

    return {
        "api_key": raw_key,
        "name": name,
        "tier": tier,
        "message": "Store this key securely. It cannot be retrieved later.",
    }


def validate_api_key(raw_key: str) -> dict | None:
    """Validate an API key. Returns key info or None."""
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    keys = _load_keys()
    info = keys.get(key_hash)
    if info and info.get("enabled", True):
        # Increment request count
        info["requests"] = info.get("requests", 0) + 1
        info["last_used"] = time.time()
        keys[key_hash] = info
        _save_keys(keys)
        return info
    return None


def check_rate_limit(key_id: str, tier: str = "free") -> bool:
    """Check if request is within rate limit. Returns True if allowed."""
    limits = {"free": 30, "pro": 120, "unlimited": 999999}
    limit = limits.get(tier, 30)

    now = time.time()
    window = _rate_tracker[key_id]

    # Remove old entries outside window
    _rate_tracker[key_id] = [t for t in window if now - t < RATE_WINDOW_SECONDS]

    if len(_rate_tracker[key_id]) >= limit:
        return False

    _rate_tracker[key_id].append(now)
    return True


async def optional_api_key(api_key: str = Depends(api_key_header)) -> dict | None:
    """
    Optional API key dependency.
    - If no key provided: allow (anonymous, uses default rate limit)
    - If key provided: validate and apply tier rate limit
    """
    if not api_key:
        # Anonymous access — rate limit by... nothing for now (web UI)
        return None

    info = validate_api_key(api_key)
    if not info:
        raise HTTPException(status_code=401, detail="Invalid or disabled API key")

    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
    if not check_rate_limit(key_hash, info.get("tier", "free")):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Tier: {info.get('tier', 'free')}. Try again in {RATE_WINDOW_SECONDS}s."
        )

    return info
