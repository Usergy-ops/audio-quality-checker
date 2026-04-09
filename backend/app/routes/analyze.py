"""
Audio Quality Checker - Analysis endpoint
With rate limiting and input validation.
"""
import time
import asyncio
import traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import MAX_FILE_SIZE_BYTES
from app.models.schemas import AnalysisResponse, ErrorResponse
from app.utils.audio import validate_file, validate_audio_content, save_temp_file, cleanup_temp_file, save_upload
from app.utils.api_auth import optional_api_key
from app.utils.profiles import is_valid_mode, is_valid_profile, VALID_MODES, PROFILES
from app.analyzers.pipeline import run_analysis_pipeline

router = APIRouter()

# Rate limiter (shared with main app)
limiter = Limiter(key_func=get_remote_address)

# Dedicated thread pool for analysis (prevents exhausting default pool)
_analysis_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="analysis")

# Server-side analysis timeout (seconds)
ANALYSIS_TIMEOUT = 600  # 10 minutes — large files on CPU need time


@router.post("/analyze", response_model=AnalysisResponse)
@limiter.limit("10/minute")  # 10 analyses per minute per IP
async def analyze_audio(
    request: Request,  # Required for rate limiting
    file: UploadFile = File(...),
    retain: bool = Form(True),
    profile: str = Form("default"),
    mode: str = Form("quick"),
    key_info: dict = Depends(optional_api_key),
):
    """
    Upload an audio file and get a detailed quality analysis report.
    
    Supported formats: WAV, MP3, FLAC, OGG, M4A, AAC, OPUS, WebM, AIFF, WMA, AMR
    Maximum file size: 1 GB
    
    retain: If true, file is kept for improving the tool. Default: true.
    mode: "quick" (fast, essential metrics) or "deep" (full AI analysis). Default: quick.
    profile: Compliance profile to check against. Default: default.
    """
    # Validate mode parameter
    if not is_valid_mode(mode):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode '{mode}'. Must be one of: {', '.join(VALID_MODES)}"
        )
    
    # Validate profile parameter
    if not is_valid_profile(profile):
        valid_profiles = list(PROFILES.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Invalid profile '{profile}'. Must be one of: {', '.join(valid_profiles)}"
        )
    
    start_time = time.time()
    temp_path = None
    timed_out = False
    
    try:
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Validate
        is_valid, error_msg = validate_file(file.filename or "unknown", file_size)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Save to temp
        temp_path = save_temp_file(content, file.filename or "upload.wav")
        del content  # Free memory
        
        # Validate audio content (check for actual audio stream)
        is_valid_audio, audio_error = validate_audio_content(temp_path)
        if not is_valid_audio:
            cleanup_temp_file(temp_path)
            raise HTTPException(status_code=400, detail=audio_error)
        
        # Run analysis pipeline in thread pool with timeout
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(
            _analysis_pool,
            lambda: run_analysis_pipeline(
                filepath=temp_path,
                original_filename=file.filename or "unknown",
                file_size=file_size,
                profile_name=profile,
                mode=mode,
            )
        )
        try:
            result = await asyncio.wait_for(future, timeout=ANALYSIS_TIMEOUT)
        except asyncio.TimeoutError:
            timed_out = True
            raise HTTPException(
                status_code=504,
                detail=f"Analysis timed out after {ANALYSIS_TIMEOUT} seconds. Try a smaller file."
            )
        
        # Save upload if user consented
        if retain:
            save_upload(temp_path, file.filename or "unknown", file_size)
        
        result.processing_time_seconds = round(time.time() - start_time, 2)
        return result
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)[:200]}"
        )
    finally:
        # Don't cleanup temp files on timeout — the analysis thread may still be reading them.
        # Orphaned temp files are acceptable; they'll be cleaned on next restart.
        if temp_path and not timed_out:
            cleanup_temp_file(temp_path)
            converted = temp_path.with_suffix(".converted.wav")
            cleanup_temp_file(converted)


@router.post("/analyze-batch")
@limiter.limit("5/minute")  # 5 batch analyses per minute per IP
async def analyze_batch(
    request: Request,  # Required for rate limiting
    files: list[UploadFile] = File(...),
    profile: str = Form("default"),
    mode: str = Form("quick"),
    key_info: dict = Depends(optional_api_key),
):
    """
    Analyze multiple audio files in parallel. Returns a summary + individual results.
    Max 20 files per batch.
    
    mode: "quick" (fast, essential metrics) or "deep" (full AI analysis). Default: quick.
    profile: Compliance profile to check against. Default: default.
    """
    # Validate mode parameter
    if not is_valid_mode(mode):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode '{mode}'. Must be one of: {', '.join(VALID_MODES)}"
        )
    
    # Validate profile parameter
    if not is_valid_profile(profile):
        valid_profiles = list(PROFILES.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Invalid profile '{profile}'. Must be one of: {', '.join(valid_profiles)}"
        )
    
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 files per batch.")
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided.")

    start_time = time.time()
    loop = asyncio.get_event_loop()

    # Pre-read all files and save to temp
    file_jobs = []  # list of (filename, temp_path, file_size) or (filename, None, error)
    for f in files:
        try:
            content = await f.read()
            file_size = len(content)
            is_valid, error_msg = validate_file(f.filename or "unknown", file_size)
            if not is_valid:
                file_jobs.append((f.filename, None, file_size, error_msg))
            else:
                temp_path = save_temp_file(content, f.filename or "upload.wav")
                del content
                file_jobs.append((f.filename, temp_path, file_size, None))
        except Exception as e:
            file_jobs.append((f.filename, None, 0, str(e)[:200]))

    # Launch all valid files in parallel (max 2 concurrent to avoid OOM)
    _batch_sem = asyncio.Semaphore(2)

    async def analyze_one(filename, temp_path, file_size):
        async with _batch_sem:
            file_start = time.time()
            try:
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        _analysis_pool,
                        lambda p=temp_path, fn=filename, fs=file_size, m=mode: run_analysis_pipeline(
                            filepath=p, original_filename=fn or "unknown",
                            file_size=fs, profile_name=profile, mode=m,
                        )
                    ),
                    timeout=ANALYSIS_TIMEOUT,
                )
                result.processing_time_seconds = round(time.time() - file_start, 2)
                result.visualizations = None  # Strip visualizations from batch
                return {"filename": filename, "success": True, "result": result}
            except asyncio.TimeoutError:
                return {"filename": filename, "success": False, "error": "Analysis timed out"}
            except Exception as e:
                return {"filename": filename, "success": False, "error": str(e)[:200]}
            finally:
                if temp_path:
                    cleanup_temp_file(temp_path)
                    cleanup_temp_file(temp_path.with_suffix(".converted.wav"))

    # Run all in parallel
    tasks = []
    error_results = []
    for filename, temp_path, file_size, error in file_jobs:
        if error:
            error_results.append({"filename": filename, "success": False, "error": error})
        else:
            tasks.append(analyze_one(filename, temp_path, file_size))

    parallel_results = await asyncio.gather(*tasks) if tasks else []

    # Build response
    results = []
    summary = {"total": len(files), "success": 0, "failed": 0, "avg_score": 0, "files": []}

    for er in error_results:
        results.append(er)
        summary["failed"] += 1

    for pr in parallel_results:
        if pr["success"]:
            result = pr["result"]
            file_summary = {
                "filename": pr["filename"],
                "success": True,
                "score": result.quality.score if result.quality else None,
                "grade": result.quality.grade if result.quality else None,
                "duration": result.file_info.duration_formatted if result.file_info else None,
                "language": result.ai_analysis.language.name if result.ai_analysis and result.ai_analysis.language else None,
                "mos": result.ai_analysis.speech_quality.mos if result.ai_analysis and result.ai_analysis.speech_quality else None,
                "compliance": result.compliance.overall if result.compliance else None,
                "time": result.processing_time_seconds,
            }
            summary["files"].append(file_summary)
            summary["success"] += 1
            results.append(result.model_dump())
        else:
            results.append({"filename": pr["filename"], "success": False, "error": pr["error"]})
            summary["failed"] += 1

    scores = [f["score"] for f in summary["files"] if f.get("score") is not None]
    summary["avg_score"] = round(sum(scores) / len(scores), 1) if scores else 0
    summary["processing_time_seconds"] = round(time.time() - start_time, 2)

    return {"summary": summary, "results": results}
