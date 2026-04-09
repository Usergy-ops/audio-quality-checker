"""
Audio Quality Checker - Pydantic Response Models
"""
from pydantic import BaseModel
from typing import Optional


class FileInfo(BaseModel):
    filename: str
    format: str
    codec: str
    duration_seconds: float
    duration_formatted: str
    sample_rate: int
    bit_rate: Optional[int] = None
    bit_depth: Optional[int] = None
    channels: int
    channel_layout: str
    file_size_bytes: int
    file_size_formatted: str


class ClippingInfo(BaseModel):
    detected: bool
    percentage: float
    clipped_samples: int
    total_samples: int
    regions: list[dict] = []


class SilenceInfo(BaseModel):
    percentage: float
    total_silence_seconds: float
    regions: list[dict] = []
    longest_silence_seconds: float


class SignalAnalysis(BaseModel):
    peak_amplitude_db: float
    rms_level_db: float
    dynamic_range_db: float
    dc_offset: float
    clipping: ClippingInfo
    silence: SilenceInfo
    snr_db: Optional[float] = None
    noise_floor_db: Optional[float] = None


class LanguageInfo(BaseModel):
    detected: str
    name: str
    confidence: float
    alternatives: list[dict] = []


class SpeechActivityInfo(BaseModel):
    speech_percentage: float
    silence_percentage: float
    speech_regions: list[dict] = []
    longest_speech_seconds: float
    longest_silence_seconds: float


class SpeakerInfo(BaseModel):
    count: int
    timeline: list[dict] = []
    distribution: dict = {}
    turn_count: int = 0
    overlap_percentage: float = 0.0


class SpeechQualityInfo(BaseModel):
    mos: float  # Mean Opinion Score (1-5)
    mos_rating: str  # Excellent/Good/Fair/Poor/Bad
    noisiness: float  # 1-5 (5=clean)
    coloration: float  # 1-5 (5=natural)
    discontinuity: float  # 1-5 (5=smooth)
    loudness: float  # 1-5 (5=appropriate)


class NoiseTypeItem(BaseModel):
    type: str
    label: str
    description: str
    icon: str
    confidence: float


class NoiseClassification(BaseModel):
    primary_noise: str
    primary_label: str
    noise_types: list[NoiseTypeItem]
    noise_floor_db: float
    spectral_profile: dict[str, float]


class TranscriptionSegment(BaseModel):
    start: float
    end: float
    text: str


class TranscriptionPreview(BaseModel):
    text: str
    segments: list[TranscriptionSegment]
    word_count: int
    duration_transcribed: float
    language_used: str


class AIAnalysis(BaseModel):
    language: Optional[LanguageInfo] = None
    speech_activity: Optional[SpeechActivityInfo] = None
    speakers: Optional[SpeakerInfo] = None
    speech_quality: Optional[SpeechQualityInfo] = None
    noise_classification: Optional[NoiseClassification] = None
    transcription: Optional[TranscriptionPreview] = None


class ScoreBreakdown(BaseModel):
    component: str
    score: float
    weight: float
    weighted_score: float
    status: str  # good, warning, bad
    detail: str


class QualityScore(BaseModel):
    score: int
    grade: str
    summary: str
    breakdown: list[ScoreBreakdown] = []


class ComplianceCheck(BaseModel):
    metric: str
    status: str  # pass, warn, fail
    value: str
    threshold: str
    message: str


class ComplianceSummary(BaseModel):
    overall: str  # pass, warn, fail
    checks: list[ComplianceCheck] = []
    pass_count: int
    warn_count: int
    fail_count: int


class Visualizations(BaseModel):
    waveform: Optional[str] = None  # base64 PNG
    spectrogram: Optional[str] = None
    loudness: Optional[str] = None
    speakers: Optional[str] = None


class AnalysisResponse(BaseModel):
    success: bool
    file_info: Optional[FileInfo] = None
    signal_analysis: Optional[SignalAnalysis] = None
    ai_analysis: Optional[AIAnalysis] = None
    quality: Optional[QualityScore] = None
    compliance: Optional[ComplianceSummary] = None
    visualizations: Optional[Visualizations] = None
    processing_time_seconds: float = 0.0
    errors: list[str] = []


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None
