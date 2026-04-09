"""
Audio Quality Checker - FastAPI Application
"""
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path

from app.routes.analyze import router as analyze_router


def _preload_models():
    """Preload AI models in a background thread so first request is fast."""
    import time
    start = time.time()
    try:
        from app.analyzers.language import _get_model
        _get_model()
        print(f"[Preload] Whisper loaded in {time.time()-start:.1f}s")
    except Exception as e:
        print(f"[Preload] Whisper failed: {e}")
    try:
        from app.analyzers.vad import _get_vad
        _get_vad()
        print(f"[Preload] Silero VAD loaded in {time.time()-start:.1f}s")
    except Exception as e:
        print(f"[Preload] VAD failed: {e}")
    # Pyannote loaded lazily on first request (heavy model, ~3GB peak RAM)
    print(f"[Preload] Whisper + VAD ready in {time.time()-start:.1f}s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Models are loaded lazily on first request to keep startup fast and memory-safe
    yield


app = FastAPI(
    title="Audio Quality Checker",
    description="Deep audio analysis tool for the AI data industry",
    version="2.4.0",
    lifespan=lifespan,
)

# CORS - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(analyze_router, prefix="/api")


@app.get("/api/profiles")
async def list_profiles():
    from app.utils.profiles import get_profile_names
    return get_profile_names()


@app.post("/api/keys/generate")
async def generate_key(name: str = "default", tier: str = "free"):
    """Generate a new API key. Admin-only (no auth for now, restrict later)."""
    from app.utils.api_auth import generate_api_key
    if tier not in ("free", "pro", "unlimited"):
        from fastapi import HTTPException
        raise HTTPException(400, "Tier must be: free, pro, or unlimited")
    return generate_api_key(name, tier)


@app.get("/api/keys/info")
async def key_info(api_key: str = ""):
    """Check API key status."""
    from app.utils.api_auth import validate_api_key
    if not api_key:
        return {"error": "Provide ?api_key=..."}
    info = validate_api_key(api_key)
    if not info:
        return {"error": "Invalid key"}
    return {"name": info["name"], "tier": info["tier"], "requests": info["requests"], "enabled": info["enabled"]}

# Frontend static files
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


@app.get("/")
async def root():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/style.css")
async def get_css():
    return FileResponse(FRONTEND_DIR / "style.css", media_type="text/css",
                       headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


@app.get("/app.js")
async def get_js():
    return FileResponse(FRONTEND_DIR / "app.js", media_type="application/javascript",
                       headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


@app.get("/health")
async def health():
    return {"status": "healthy"}
