"""
Audio Quality Checker - Analysis Pipeline
Orchestrates all analyzers to produce a complete report.
"""
import traceback
from pathlib import Path

from app.models.schemas import (
    AnalysisResponse, FileInfo, SignalAnalysis,
    AIAnalysis, QualityScore, ComplianceSummary, Visualizations
)
from app.analyzers.metadata import extract_metadata
from app.analyzers.signal import analyze_signal
from app.analyzers.clipping import detect_clipping
from app.analyzers.silence import analyze_silence
from app.analyzers.snr import calculate_snr
from app.analyzers.language import detect_language
from app.analyzers.vad import detect_speech_activity
from app.analyzers.speakers import count_speakers
from app.analyzers.nisqa import assess_speech_quality
from app.analyzers.noise import analyze_noise_types
from app.analyzers.transcription import transcribe_preview
from app.utils.audio import convert_to_wav
from app.utils.scoring import calculate_quality_score, calculate_compliance
from app.utils.visualizations import generate_all_visualizations


def run_analysis_pipeline(
    filepath: Path,
    original_filename: str,
    file_size: int,
    profile_name: str = "default",
) -> AnalysisResponse:
    """
    Run the complete analysis pipeline on an audio file.
    Each analyzer is called in sequence, errors in one don't stop the rest.
    """
    errors = []
    file_info = None
    signal_analysis = None
    ai_analysis = None
    quality = None
    compliance = None
    visualizations = None
    
    # ── Step 1: Extract metadata (ffprobe) ──
    try:
        file_info = extract_metadata(filepath, original_filename, file_size)
    except Exception as e:
        errors.append(f"Metadata extraction failed: {str(e)[:200]}")
        traceback.print_exc()
    
    # ── Step 2: Convert to WAV for processing ──
    wav_path = filepath
    try:
        wav_path = convert_to_wav(filepath)
    except Exception as e:
        errors.append(f"Audio conversion failed: {str(e)[:200]}")
        traceback.print_exc()
    
    # ── Step 3: Signal analysis (librosa) ──
    # This loads the audio ONCE — all subsequent analyzers reuse this data
    audio_data = None
    sr = None
    try:
        signal_result = analyze_signal(wav_path)
        audio_data = signal_result.pop("audio_data")
        sr = signal_result.pop("sr")
        # Remove extra keys not needed downstream
        signal_result.pop("sample_rate", None)
        signal_result.pop("num_samples", None)
        signal_result.pop("peak_amplitude_linear", None)
        signal_result.pop("rms_level_linear", None)
        
        # Step 3a: Clipping detection
        try:
            clipping_info = detect_clipping(audio_data, sr)
        except Exception as e:
            errors.append(f"Clipping detection failed: {str(e)[:200]}")
            from app.models.schemas import ClippingInfo
            clipping_info = ClippingInfo(
                detected=False, percentage=0, clipped_samples=0,
                total_samples=len(audio_data), regions=[]
            )
        
        # Step 3b: Silence analysis
        try:
            silence_info = analyze_silence(audio_data, sr)
        except Exception as e:
            errors.append(f"Silence analysis failed: {str(e)[:200]}")
            from app.models.schemas import SilenceInfo
            silence_info = SilenceInfo(
                percentage=0, total_silence_seconds=0,
                regions=[], longest_silence_seconds=0
            )
        
        # Step 3c: SNR calculation
        snr_result = {"snr_db": None, "noise_floor_db": None}
        try:
            snr_result = calculate_snr(audio_data, sr)
        except Exception as e:
            errors.append(f"SNR calculation failed: {str(e)[:200]}")
        
        signal_analysis = SignalAnalysis(
            peak_amplitude_db=signal_result["peak_amplitude_db"],
            rms_level_db=signal_result["rms_level_db"],
            dynamic_range_db=signal_result["dynamic_range_db"],
            dc_offset=signal_result["dc_offset"],
            clipping=clipping_info,
            silence=silence_info,
            snr_db=snr_result.get("snr_db"),
            noise_floor_db=snr_result.get("noise_floor_db"),
        )
        
    except Exception as e:
        errors.append(f"Signal analysis failed: {str(e)[:200]}")
        traceback.print_exc()
    
    # ── Step 4: AI Analysis (parallel) ──
    # Run language, VAD, and speakers concurrently for speed
    from concurrent.futures import ThreadPoolExecutor, as_completed
    language_info = None
    speech_activity_info = None
    speaker_info = None
    speech_quality_info = None
    noise_classification_info = None
    transcription_info = None
    
    ai_tasks = {}
    with ThreadPoolExecutor(max_workers=4, thread_name_prefix="ai") as ai_pool:
        if audio_data is not None:
            ai_tasks['language'] = ai_pool.submit(detect_language, audio_data=audio_data, sample_rate=sr)
            ai_tasks['vad'] = ai_pool.submit(detect_speech_activity, audio_data=audio_data, sample_rate=sr)
            ai_tasks['speakers'] = ai_pool.submit(count_speakers, audio_data=audio_data, sample_rate=sr)
            ai_tasks['nisqa'] = ai_pool.submit(assess_speech_quality, audio_data=audio_data, sample_rate=sr)
            ai_tasks['noise'] = ai_pool.submit(analyze_noise_types, audio=audio_data, sr=sr)
            ai_tasks['transcription'] = ai_pool.submit(transcribe_preview, audio_data=audio_data, sample_rate=sr)
        else:
            ai_tasks['language'] = ai_pool.submit(detect_language, filepath=wav_path)
            ai_tasks['vad'] = ai_pool.submit(detect_speech_activity, filepath=wav_path)
            ai_tasks['speakers'] = ai_pool.submit(count_speakers, filepath=wav_path)
            ai_tasks['nisqa'] = ai_pool.submit(assess_speech_quality, filepath=wav_path)
    
    # Collect results
    for name, future in ai_tasks.items():
        try:
            result = future.result()
            if name == 'language':
                language_info = result
            elif name == 'vad':
                speech_activity_info = result
            elif name == 'speakers':
                speaker_info = result
            elif name == 'nisqa':
                speech_quality_info = result
            elif name == 'noise':
                if result and isinstance(result, dict):
                    from app.models.schemas import NoiseClassification
                    noise_classification_info = NoiseClassification(**result)
            elif name == 'transcription':
                if result and isinstance(result, dict):
                    from app.models.schemas import TranscriptionPreview
                    transcription_info = TranscriptionPreview(**result)
        except Exception as e:
            errors.append(f"{name} failed: {str(e)[:200]}")
            traceback.print_exc()
    
    # Build AI analysis object
    if language_info or speech_activity_info or speaker_info or speech_quality_info or noise_classification_info or transcription_info:
        ai_analysis = AIAnalysis(
            language=language_info,
            speech_activity=speech_activity_info,
            speakers=speaker_info,
            speech_quality=speech_quality_info,
            noise_classification=noise_classification_info,
            transcription=transcription_info,
        )
    
    # ── Step 5: Quality Scoring ──
    try:
        quality = calculate_quality_score(file_info, signal_analysis, ai_analysis)
    except Exception as e:
        errors.append(f"Quality scoring failed: {str(e)[:200]}")
        traceback.print_exc()
    
    # ── Step 5b: Compliance Check ──
    try:
        compliance = calculate_compliance(file_info, signal_analysis, ai_analysis, profile_name)
    except Exception as e:
        errors.append(f"Compliance check failed: {str(e)[:200]}")
        traceback.print_exc()
    
    # ── Step 6: Visualizations ──
    if audio_data is not None and sr is not None:
        try:
            speech_act = ai_analysis.speech_activity if ai_analysis else None
            spk_info = ai_analysis.speakers if ai_analysis else None
            duration = file_info.duration_seconds if file_info else len(audio_data) / sr
            visualizations = generate_all_visualizations(
                audio_data, sr, speech_act, spk_info, duration
            )
        except Exception as e:
            errors.append(f"Visualization generation failed: {str(e)[:200]}")
            traceback.print_exc()
    
    # Cleanup converted file if different from original
    if wav_path != filepath:
        from app.utils.audio import cleanup_temp_file
        cleanup_temp_file(wav_path)
    
    return AnalysisResponse(
        success=len(errors) == 0 or file_info is not None,
        file_info=file_info,
        signal_analysis=signal_analysis,
        ai_analysis=ai_analysis,
        quality=quality,
        compliance=compliance,
        visualizations=visualizations,
        errors=errors,
    )
