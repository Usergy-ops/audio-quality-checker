"""
Audio Quality Checker - Quality Scoring Engine
Calculates overall quality score (0-100) with letter grade.
"""
from app.config import QUALITY_WEIGHTS, GRADE_MAP
from app.models.schemas import (
    QualityScore, ScoreBreakdown, FileInfo, SignalAnalysis, AIAnalysis,
    ComplianceSummary, ComplianceCheck
)


def calculate_quality_score(
    file_info: FileInfo | None,
    signal_analysis: SignalAnalysis | None,
    ai_analysis: AIAnalysis | None,
) -> QualityScore:
    """
    Calculate overall audio quality score from all analysis data.
    Returns QualityScore with 0-100 score, letter grade, and breakdown.
    """
    breakdown = []
    
    # ── SNR Score (25%) ──
    snr_score = 50  # default if unavailable
    snr_detail = "N/A"
    if signal_analysis and signal_analysis.snr_db is not None:
        snr = signal_analysis.snr_db
        if snr >= 30:
            snr_score = 100
        elif snr >= 25:
            snr_score = 85
        elif snr >= 20:
            snr_score = 70
        elif snr >= 15:
            snr_score = 50
        elif snr >= 10:
            snr_score = 30
        else:
            snr_score = max(0, int(snr * 3))
        snr_detail = f"{snr:.1f} dB"
    
    breakdown.append(ScoreBreakdown(
        component="SNR (Signal-to-Noise)",
        score=snr_score,
        weight=QUALITY_WEIGHTS["snr"],
        weighted_score=round(snr_score * QUALITY_WEIGHTS["snr"], 2),
        status=_score_status(snr_score),
        detail=snr_detail,
    ))
    
    # ── Clipping Score (15%) ──
    clip_score = 100
    clip_detail = "No clipping"
    if signal_analysis and signal_analysis.clipping:
        pct = signal_analysis.clipping.percentage
        if pct == 0:
            clip_score = 100
        elif pct < 0.01:
            clip_score = 85
        elif pct < 0.1:
            clip_score = 60
        elif pct < 0.5:
            clip_score = 30
        elif pct < 1.0:
            clip_score = 10
        else:
            clip_score = 0
        clip_detail = f"{pct:.4f}% clipped" if pct > 0 else "No clipping"
    
    breakdown.append(ScoreBreakdown(
        component="Clipping",
        score=clip_score,
        weight=QUALITY_WEIGHTS["clipping"],
        weighted_score=round(clip_score * QUALITY_WEIGHTS["clipping"], 2),
        status=_score_status(clip_score),
        detail=clip_detail,
    ))
    
    # ── Silence Ratio Score (10%) ──
    silence_score = 100
    silence_detail = "N/A"
    if signal_analysis and signal_analysis.silence:
        sil_pct = signal_analysis.silence.percentage
        if sil_pct <= 5:
            silence_score = 100
        elif sil_pct <= 10:
            silence_score = 85
        elif sil_pct <= 20:
            silence_score = 60
        elif sil_pct <= 30:
            silence_score = 40
        elif sil_pct <= 50:
            silence_score = 20
        else:
            silence_score = 0
        silence_detail = f"{sil_pct:.1f}% silence"
    
    # Also factor in VAD if available
    if ai_analysis and ai_analysis.speech_activity:
        vad_speech = ai_analysis.speech_activity.speech_percentage
        if vad_speech > 0:  # Only use VAD if it detected speech
            if vad_speech >= 80:
                silence_score = max(silence_score, 90)
            elif vad_speech >= 60:
                silence_score = max(silence_score, 70)
            silence_detail = f"{100 - vad_speech:.1f}% non-speech (VAD)"
    
    breakdown.append(ScoreBreakdown(
        component="Silence Ratio",
        score=silence_score,
        weight=QUALITY_WEIGHTS["silence_ratio"],
        weighted_score=round(silence_score * QUALITY_WEIGHTS["silence_ratio"], 2),
        status=_score_status(silence_score),
        detail=silence_detail,
    ))
    
    # ── Sample Rate Score (10%) ──
    sr_score = 50
    sr_detail = "N/A"
    if file_info and file_info.sample_rate:
        sr = file_info.sample_rate
        if sr >= 48000:
            sr_score = 100
        elif sr >= 44100:
            sr_score = 90
        elif sr >= 22050:
            sr_score = 70
        elif sr >= 16000:
            sr_score = 50
        elif sr >= 8000:
            sr_score = 30
        else:
            sr_score = 10
        sr_detail = f"{sr:,} Hz"
    
    breakdown.append(ScoreBreakdown(
        component="Sample Rate",
        score=sr_score,
        weight=QUALITY_WEIGHTS["sample_rate"],
        weighted_score=round(sr_score * QUALITY_WEIGHTS["sample_rate"], 2),
        status=_score_status(sr_score),
        detail=sr_detail,
    ))
    
    # ── Bit Depth Score (5%) ──
    bd_score = 70  # Default for lossy formats (no bit depth)
    bd_detail = "N/A (lossy format)"
    if file_info and file_info.bit_depth:
        bd = file_info.bit_depth
        if bd >= 24:
            bd_score = 100
        elif bd >= 16:
            bd_score = 80
        elif bd >= 8:
            bd_score = 30
        else:
            bd_score = 10
        bd_detail = f"{bd}-bit"
    
    breakdown.append(ScoreBreakdown(
        component="Bit Depth",
        score=bd_score,
        weight=QUALITY_WEIGHTS["bit_depth"],
        weighted_score=round(bd_score * QUALITY_WEIGHTS["bit_depth"], 2),
        status=_score_status(bd_score),
        detail=bd_detail,
    ))
    
    # ── Dynamic Range Score (10%) ──
    dr_score = 50
    dr_detail = "N/A"
    if signal_analysis:
        dr = signal_analysis.dynamic_range_db
        if dr >= 20:
            dr_score = 100
        elif dr >= 15:
            dr_score = 85
        elif dr >= 10:
            dr_score = 65
        elif dr >= 6:
            dr_score = 40
        elif dr >= 3:
            dr_score = 20
        else:
            dr_score = 10
        dr_detail = f"{dr:.1f} dB"
    
    breakdown.append(ScoreBreakdown(
        component="Dynamic Range",
        score=dr_score,
        weight=QUALITY_WEIGHTS["dynamic_range"],
        weighted_score=round(dr_score * QUALITY_WEIGHTS["dynamic_range"], 2),
        status=_score_status(dr_score),
        detail=dr_detail,
    ))
    
    # ── DC Offset Score (5%) ──
    dc_score = 100
    dc_detail = "N/A"
    if signal_analysis:
        dc = abs(signal_analysis.dc_offset)
        if dc < 0.005:
            dc_score = 100
        elif dc < 0.01:
            dc_score = 85
        elif dc < 0.05:
            dc_score = 50
        elif dc < 0.1:
            dc_score = 25
        else:
            dc_score = 0
        dc_detail = f"{signal_analysis.dc_offset:.6f}"
    
    breakdown.append(ScoreBreakdown(
        component="DC Offset",
        score=dc_score,
        weight=QUALITY_WEIGHTS["dc_offset"],
        weighted_score=round(dc_score * QUALITY_WEIGHTS["dc_offset"], 2),
        status=_score_status(dc_score),
        detail=dc_detail,
    ))
    
    # ── Speech Clarity Score (10%) ──
    clarity_score = 50
    clarity_detail = "N/A"
    if signal_analysis and signal_analysis.snr_db is not None:
        snr = signal_analysis.snr_db
        # Clarity is a softer version of SNR + noise floor
        if snr >= 25:
            clarity_score = 100
        elif snr >= 20:
            clarity_score = 80
        elif snr >= 15:
            clarity_score = 60
        elif snr >= 10:
            clarity_score = 40
        else:
            clarity_score = 20
        clarity_detail = f"Based on SNR ({snr:.1f} dB)"
    
    breakdown.append(ScoreBreakdown(
        component="Speech Clarity",
        score=clarity_score,
        weight=QUALITY_WEIGHTS["speech_clarity"],
        weighted_score=round(clarity_score * QUALITY_WEIGHTS["speech_clarity"], 2),
        status=_score_status(clarity_score),
        detail=clarity_detail,
    ))
    
    # ── Format Quality Score (10%) ──
    fmt_score = 50
    fmt_detail = "N/A"
    if file_info:
        codec = (file_info.codec or "").lower()
        br = file_info.bit_rate or 0
        
        # Lossless formats
        if any(x in codec for x in ["pcm", "flac", "aiff", "alac"]):
            fmt_score = 100
            fmt_detail = "Lossless"
        # Lossy but high quality
        elif br >= 256000:
            fmt_score = 80
            fmt_detail = f"Lossy, high bitrate ({br // 1000}kbps)"
        elif br >= 128000:
            fmt_score = 60
            fmt_detail = f"Lossy, medium bitrate ({br // 1000}kbps)"
        elif br >= 64000:
            fmt_score = 40
            fmt_detail = f"Lossy, low bitrate ({br // 1000}kbps)"
        elif br > 0:
            fmt_score = 20
            fmt_detail = f"Lossy, very low bitrate ({br // 1000}kbps)"
        else:
            fmt_score = 50
            fmt_detail = "Unknown bitrate"
    
    breakdown.append(ScoreBreakdown(
        component="Format Quality",
        score=fmt_score,
        weight=QUALITY_WEIGHTS["format_quality"],
        weighted_score=round(fmt_score * QUALITY_WEIGHTS["format_quality"], 2),
        status=_score_status(fmt_score),
        detail=fmt_detail,
    ))
    
    # ── Calculate total weighted score ──
    total_score = sum(b.weighted_score for b in breakdown)
    total_score = max(0, min(100, int(round(total_score))))
    
    # ── Map to grade ──
    grade = "F"
    summary = "Unusable - needs re-recording"
    for threshold, g, s in GRADE_MAP:
        if total_score >= threshold:
            grade = g
            summary = s
            break
    
    return QualityScore(
        score=total_score,
        grade=grade,
        summary=summary,
        breakdown=breakdown,
    )


def calculate_compliance(
    file_info: FileInfo | None,
    signal_analysis: SignalAnalysis | None,
    ai_analysis: AIAnalysis | None,
) -> ComplianceSummary:
    """
    Check audio against common AI data project specifications.
    Returns pass/warn/fail for each metric.
    """
    checks = []
    
    # Sample Rate
    if file_info and file_info.sample_rate:
        sr = file_info.sample_rate
        if sr >= 16000:
            checks.append(ComplianceCheck(
                metric="Sample Rate", status="pass",
                value=f"{sr:,} Hz", threshold="≥ 16,000 Hz",
                message=f"Sample rate is {sr:,} Hz"
            ))
        elif sr >= 8000:
            checks.append(ComplianceCheck(
                metric="Sample Rate", status="warn",
                value=f"{sr:,} Hz", threshold="≥ 16,000 Hz",
                message=f"Sample rate {sr:,} Hz is below recommended 16kHz"
            ))
        else:
            checks.append(ComplianceCheck(
                metric="Sample Rate", status="fail",
                value=f"{sr:,} Hz", threshold="≥ 16,000 Hz",
                message=f"Sample rate {sr:,} Hz is too low for speech"
            ))
    
    # Bit Depth
    if file_info and file_info.bit_depth:
        bd = file_info.bit_depth
        if bd >= 16:
            checks.append(ComplianceCheck(
                metric="Bit Depth", status="pass",
                value=f"{bd}-bit", threshold="≥ 16-bit",
                message=f"{bd}-bit audio"
            ))
        else:
            checks.append(ComplianceCheck(
                metric="Bit Depth", status="warn",
                value=f"{bd}-bit", threshold="≥ 16-bit",
                message=f"{bd}-bit is below standard 16-bit"
            ))
    
    # Channels
    if file_info:
        ch = file_info.channels
        if ch == 1:
            checks.append(ComplianceCheck(
                metric="Channels", status="pass",
                value="Mono", threshold="Mono preferred",
                message="Mono audio (preferred for speech)"
            ))
        elif ch == 2:
            checks.append(ComplianceCheck(
                metric="Channels", status="warn",
                value="Stereo", threshold="Mono preferred",
                message="Stereo - many projects require mono"
            ))
        else:
            checks.append(ComplianceCheck(
                metric="Channels", status="warn",
                value=f"{ch} channels", threshold="Mono preferred",
                message=f"{ch} channels - should be converted to mono"
            ))
    
    # Clipping
    if signal_analysis and signal_analysis.clipping:
        pct = signal_analysis.clipping.percentage
        if pct == 0:
            checks.append(ComplianceCheck(
                metric="Clipping", status="pass",
                value="None", threshold="0%",
                message="No clipping detected"
            ))
        elif pct < 0.1:
            checks.append(ComplianceCheck(
                metric="Clipping", status="warn",
                value=f"{pct:.4f}%", threshold="< 0.1%",
                message="Minor clipping detected"
            ))
        else:
            checks.append(ComplianceCheck(
                metric="Clipping", status="fail",
                value=f"{pct:.2f}%", threshold="< 0.1%",
                message="Significant clipping detected"
            ))
    
    # SNR
    if signal_analysis and signal_analysis.snr_db is not None:
        snr = signal_analysis.snr_db
        if snr >= 20:
            checks.append(ComplianceCheck(
                metric="SNR", status="pass",
                value=f"{snr:.1f} dB", threshold="≥ 20 dB",
                message=f"Good signal-to-noise ratio"
            ))
        elif snr >= 15:
            checks.append(ComplianceCheck(
                metric="SNR", status="warn",
                value=f"{snr:.1f} dB", threshold="≥ 20 dB",
                message=f"Acceptable but noisy"
            ))
        else:
            checks.append(ComplianceCheck(
                metric="SNR", status="fail",
                value=f"{snr:.1f} dB", threshold="≥ 20 dB",
                message=f"Too noisy for most projects"
            ))
    
    # Silence percentage
    if signal_analysis and signal_analysis.silence:
        sil = signal_analysis.silence.percentage
        if sil <= 10:
            checks.append(ComplianceCheck(
                metric="Silence", status="pass",
                value=f"{sil:.1f}%", threshold="≤ 10%",
                message="Acceptable silence level"
            ))
        elif sil <= 20:
            checks.append(ComplianceCheck(
                metric="Silence", status="warn",
                value=f"{sil:.1f}%", threshold="≤ 10%",
                message="Higher than ideal silence"
            ))
        else:
            checks.append(ComplianceCheck(
                metric="Silence", status="fail",
                value=f"{sil:.1f}%", threshold="≤ 10%",
                message="Excessive silence"
            ))
    
    # Format
    if file_info:
        codec = (file_info.codec or "").lower()
        br = file_info.bit_rate or 0
        if any(x in codec for x in ["pcm", "flac", "aiff"]):
            checks.append(ComplianceCheck(
                metric="Format", status="pass",
                value="Lossless", threshold="Lossless or ≥ 256kbps",
                message="Lossless format - ideal"
            ))
        elif br >= 256000:
            checks.append(ComplianceCheck(
                metric="Format", status="pass",
                value=f"{br // 1000}kbps", threshold="Lossless or ≥ 256kbps",
                message="High quality lossy"
            ))
        elif br >= 128000:
            checks.append(ComplianceCheck(
                metric="Format", status="warn",
                value=f"{br // 1000}kbps", threshold="Lossless or ≥ 256kbps",
                message="Medium quality - acceptable"
            ))
        elif br > 0:
            checks.append(ComplianceCheck(
                metric="Format", status="fail",
                value=f"{br // 1000}kbps", threshold="Lossless or ≥ 256kbps",
                message="Low quality - may affect analysis"
            ))
    
    # Count results
    pass_count = sum(1 for c in checks if c.status == "pass")
    warn_count = sum(1 for c in checks if c.status == "warn")
    fail_count = sum(1 for c in checks if c.status == "fail")
    
    # Overall status
    if fail_count > 0:
        overall = "fail"
    elif warn_count > 0:
        overall = "warn"
    else:
        overall = "pass"
    
    return ComplianceSummary(
        overall=overall,
        checks=checks,
        pass_count=pass_count,
        warn_count=warn_count,
        fail_count=fail_count,
    )


def _score_status(score: float) -> str:
    """Map score to status label."""
    if score >= 70:
        return "good"
    elif score >= 40:
        return "warning"
    return "bad"
