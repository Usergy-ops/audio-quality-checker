"""
Audio Quality Checker - Analysis endpoint
"""
import time
import traceback
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.config import MAX_FILE_SIZE_BYTES
from app.models.schemas import AnalysisResponse, ErrorResponse
from app.utils.audio import validate_file, save_temp_file, cleanup_temp_file
from app.analyzers.pipeline import run_analysis_pipeline

router = APIRouter()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_audio(file: UploadFile = File(...)):
    """
    Upload an audio file and get a detailed quality analysis report.
    
    Supported formats: WAV, MP3, FLAC, OGG, M4A, AAC, OPUS, WebM, AIFF, WMA, AMR
    Maximum file size: 1 GB
    """
    start_time = time.time()
    temp_path = None
    converted_path = None
    
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
        
        # Run analysis pipeline
        result = await run_analysis_pipeline(
            filepath=temp_path,
            original_filename=file.filename or "unknown",
            file_size=file_size,
        )
        
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
        # Always cleanup temp files
        if temp_path:
            cleanup_temp_file(temp_path)
            # Also cleanup any converted file
            converted = temp_path.with_suffix(".converted.wav")
            cleanup_temp_file(converted)
