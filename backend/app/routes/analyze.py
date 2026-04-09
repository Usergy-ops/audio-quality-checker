"""
Audio Quality Checker - Analysis endpoint
"""
import time
import asyncio
import traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.config import MAX_FILE_SIZE_BYTES
from app.models.schemas import AnalysisResponse, ErrorResponse
from app.utils.audio import validate_file, save_temp_file, cleanup_temp_file, save_upload
from app.analyzers.pipeline import run_analysis_pipeline

router = APIRouter()

# Dedicated thread pool for analysis (prevents exhausting default pool)
_analysis_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="analysis")

# Server-side analysis timeout (seconds)
ANALYSIS_TIMEOUT = 180  # 3 minutes


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_audio(
    file: UploadFile = File(...),
    retain: bool = Form(True),
):
    """
    Upload an audio file and get a detailed quality analysis report.
    
    Supported formats: WAV, MP3, FLAC, OGG, M4A, AAC, OPUS, WebM, AIFF, WMA, AMR
    Maximum file size: 1 GB
    
    retain: If true, file is kept for improving the tool. Default: true.
    """
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
        
        # Run analysis pipeline in thread pool with timeout
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(
            _analysis_pool,
            lambda: run_analysis_pipeline(
                filepath=temp_path,
                original_filename=file.filename or "unknown",
                file_size=file_size,
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
