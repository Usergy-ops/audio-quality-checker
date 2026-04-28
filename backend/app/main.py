"""
Audio Quality Checker - FastAPI Application
Production-ready with rate limiting and security.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.routes.analyze import router as analyze_router

# ── Configuration ──
# Set ALLOWED_ORIGINS env var for production (comma-separated)
# Example: ALLOWED_ORIGINS=https://usergy.ai,https://audio.usergy.ai
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"

# ── Rate Limiter ──
limiter = Limiter(
    key_func=get_remote_address,
    enabled=RATE_LIMIT_ENABLED,
    default_limits=["100/minute"],  # Global fallback
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    # Optionally preload models here for faster first request
    # For now, models load lazily to keep startup fast and memory-safe
    yield
    # Cleanup on shutdown (if needed)


app = FastAPI(
    title="Audio Quality Checker",
    description="Deep audio analysis tool for the AI data industry",
    version="4.6.0",
    lifespan=lifespan,
)

# Attach rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS Middleware ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ── API Routes ──
app.include_router(analyze_router, prefix="/api")


@app.get("/api/profiles")
async def list_profiles():
    """List available compliance profiles."""
    from app.utils.profiles import get_profile_names
    return get_profile_names()


@app.post("/api/keys/generate")
@limiter.limit("2/hour")  # Strict rate limit on key generation
async def generate_key(request: Request, name: str = "default", tier: str = "free"):
    """
    Generate a new API key.
    Rate limited to 2 per hour to prevent abuse.
    """
    from fastapi import HTTPException
    from app.utils.api_auth import generate_api_key
    
    if tier not in ("free", "pro", "unlimited"):
        raise HTTPException(400, "Tier must be: free, pro, or unlimited")
    return generate_api_key(name, tier)


@app.get("/api/keys/info")
async def key_info(api_key: str = ""):
    """Check API key status and usage."""
    from app.utils.api_auth import validate_api_key
    if not api_key:
        return {"error": "Provide ?api_key=..."}
    info = validate_api_key(api_key)
    if not info:
        return {"error": "Invalid key"}
    return {
        "name": info["name"],
        "tier": info["tier"],
        "requests": info["requests"],
        "enabled": info["enabled"]
    }


# ── Frontend Static Files ──
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

# Mount /assets/* for brand kit images (favicon, mark, wordmark, etc.)
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")


@app.get("/")
async def root():
    """Serve the main frontend page."""
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/style.css")
async def get_css():
    """Serve CSS with cache-busting for development."""
    return FileResponse(
        FRONTEND_DIR / "style.css",
        media_type="text/css",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )


@app.get("/app.js")
async def get_js():
    """Serve JavaScript with cache-busting for development."""
    return FileResponse(
        FRONTEND_DIR / "app.js",
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )


@app.get("/health")
async def health():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "version": "4.6.0"}


@app.get("/api/limits")
async def rate_limits():
    """Show current rate limit configuration."""
    return {
        "enabled": RATE_LIMIT_ENABLED,
        "analyze": "10/minute per IP",
        "batch": "5/minute per IP",
        "key_generate": "2/hour per IP",
    }
