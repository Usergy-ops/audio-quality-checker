# Audio Quality Checker - Backend

Python FastAPI backend for audio analysis.

## Setup
```bash
cd tools/audio-quality-checker/backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Project Structure
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              ← FastAPI entry point
│   ├── config.py            ← Configuration & constants
│   ├── routes/
│   │   ├── __init__.py
│   │   └── analyze.py       ← /api/analyze endpoint
│   ├── analyzers/
│   │   ├── __init__.py
│   │   ├── metadata.py      ← ffprobe file info
│   │   ├── signal.py        ← librosa signal analysis
│   │   ├── clipping.py      ← Clipping detection
│   │   ├── silence.py       ← Silence analysis
│   │   ├── snr.py           ← SNR calculation
│   │   ├── language.py      ← Whisper language detection
│   │   ├── speakers.py      ← pyannote speaker diarization
│   │   ├── vad.py           ← Silero VAD speech activity
│   │   └── pipeline.py      ← Orchestrates all analyzers
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py       ← Pydantic response models
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── audio.py         ← Audio file loading & conversion
│   │   ├── scoring.py       ← Quality score calculation
│   │   └── visualizations.py ← Chart generation
│   └── routes/
│       ├── __init__.py
│       └── analyze.py
├── temp/                     ← Temporary upload storage (auto-cleaned)
├── tests/
├── requirements.txt
└── README.md
```
