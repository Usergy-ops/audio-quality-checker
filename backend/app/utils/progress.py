"""
Simple file-based progress tracker for the analysis pipeline.

Each active job writes a JSON snapshot to /tmp/aqc-progress-{job_id}.json.
Frontend polls GET /api/analyze/progress/{job_id} to read it back.

Write-at-every-stage is cheap (<1 KB per stage) and avoids pulling in an
event-loop/pubsub dependency. Self-cleans when the analysis finishes or
explicitly via clear().
"""
import json
import os
import time
from pathlib import Path
from typing import Optional

PROGRESS_DIR = Path("/tmp")
PROGRESS_PREFIX = "aqc-progress-"
VALID_ID = __import__("re").compile(r"^[A-Za-z0-9_-]{8,64}$")


def _path(job_id: str) -> Optional[Path]:
    """Validate + return the progress file path for a job id."""
    if not job_id or not VALID_ID.match(job_id):
        return None
    return PROGRESS_DIR / f"{PROGRESS_PREFIX}{job_id}.json"


def mark(job_id: Optional[str], stage: str, pct: float, message: str = ""):
    """Record a progress milestone. No-op if job_id is missing/invalid."""
    if not job_id:
        return
    p = _path(job_id)
    if p is None:
        return
    try:
        data = {
            "job_id": job_id,
            "stage": stage,
            "progress_pct": round(max(0.0, min(100.0, float(pct))), 1),
            "message": message,
            "updated_at": time.time(),
        }
        p.write_text(json.dumps(data))
    except Exception:
        # Progress tracking must never break the pipeline.
        pass


def read(job_id: str) -> Optional[dict]:
    """Read current progress for a job. Returns None if missing/invalid."""
    p = _path(job_id)
    if p is None or not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def clear(job_id: Optional[str]):
    """Remove the progress file for a completed/failed job."""
    if not job_id:
        return
    p = _path(job_id)
    if p is None:
        return
    try:
        p.unlink(missing_ok=True)
    except Exception:
        pass


def sweep_stale(max_age_seconds: int = 3600):
    """Delete progress files older than max_age. Called opportunistically."""
    cutoff = time.time() - max_age_seconds
    try:
        for p in PROGRESS_DIR.glob(f"{PROGRESS_PREFIX}*.json"):
            try:
                if p.stat().st_mtime < cutoff:
                    p.unlink(missing_ok=True)
            except Exception:
                continue
    except Exception:
        pass
