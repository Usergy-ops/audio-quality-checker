# 🎵 Audio Quality Checker

**AI-powered audio quality analysis tool by [UsergyAI](https://usergy.ai)**

Upload any audio file and get instant quality scores, technical metrics, AI-powered language detection, speech analysis, and beautiful visualizations.

---

## Features

- **Technical Metrics** — Sample rate, bit depth, codec, duration, channels, bit rate
- **Signal Analysis** — Peak amplitude, RMS level, dynamic range, SNR, DC offset
- **Clipping Detection** — Percentage, sample count, timestamped regions
- **Silence Analysis** — Silence percentage, regions, longest silent stretch
- **Language Detection** — AI-powered (OpenAI Whisper), 99 languages with confidence scores
- **Speech Activity** — Silero VAD detects speech vs noise with timestamps
- **Speaker Diarization** — Pyannote identifies speaker count and timeline
- **Quality Score** — Weighted 0-100 score with A+ to F grading (9 components)
- **Compliance Check** — Pass/warn/fail against AI data project specs
- **Visualizations** — Waveform, mel spectrogram, loudness chart, speaker timeline

## Supported Formats

WAV, MP3, FLAC, OGG, AAC, M4A, AIFF, OPUS, WebM, WMA, AMR — up to 1 GB

---

## Quick Start

### Prerequisites

- Python 3.12+
- ffmpeg (`sudo apt install ffmpeg`)

### Install & Run

```bash
cd backend

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install PyTorch (CPU)
pip install torch==2.6.0+cpu torchaudio==2.6.0+cpu --index-url https://download.pytorch.org/whl/cpu

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** in your browser.

### Access from Another Machine

```bash
# SSH tunnel (replace with your key and server IP)
ssh -i your-key.pem -L 8000:localhost:8000 ubuntu@YOUR_SERVER_IP
```

Then open **http://localhost:8000** locally.

---

## API

### POST /api/analyze

Upload an audio file for analysis.

```bash
curl -X POST http://localhost:8000/api/analyze \
  -F "file=@your-audio.wav"
```

**Response:** JSON with all analysis results, quality score, compliance checks, and base64-encoded visualization images.

### GET /health

```bash
curl http://localhost:8000/health
# {"status": "healthy"}
```

### Swagger Docs

Visit **http://localhost:8000/docs** for interactive API documentation.

---

## Architecture

```
audio-quality-checker/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + static file serving
│   │   ├── config.py            # Settings, weights, limits
│   │   ├── models/
│   │   │   └── schemas.py       # Pydantic response models
│   │   ├── routes/
│   │   │   └── analyze.py       # POST /api/analyze endpoint
│   │   ├── analyzers/
│   │   │   ├── metadata.py      # ffprobe metadata extraction
│   │   │   ├── signal.py        # Peak, RMS, dynamic range, DC offset
│   │   │   ├── clipping.py      # Clipping detection
│   │   │   ├── silence.py       # Silence regions + percentage
│   │   │   ├── snr.py           # Signal-to-noise ratio
│   │   │   ├── language.py      # Whisper language detection
│   │   │   ├── vad.py           # Silero VAD speech activity
│   │   │   ├── speakers.py      # Pyannote speaker diarization
│   │   │   └── pipeline.py      # Orchestrates all analyzers
│   │   └── utils/
│   │       ├── audio.py         # Audio conversion + temp files
│   │       ├── scoring.py       # Quality scoring + compliance
│   │       └── visualizations.py # Waveform, spectrogram, charts
│   └── requirements.txt
├── frontend/
│   ├── index.html               # Landing page
│   ├── style.css                # Dark theme styling
│   └── app.js                   # Upload + results rendering
├── tests/
│   └── samples/                 # Test audio files
├── docs/
│   ├── PLAN.md                  # Build plan (completed)
│   ├── FEATURES.md              # Feature specification
│   ├── TECH-STACK.md            # Technology decisions
│   ├── DECISIONS.md             # Architecture decisions
│   └── ROADMAP.md               # Future enhancements
└── README.md                    # This file
```

## Quality Scoring

9 weighted components:

| Component | Weight | What It Measures |
|-----------|--------|------------------|
| SNR | 25% | Signal-to-noise ratio |
| Clipping | 15% | Audio clipping percentage |
| Silence Ratio | 10% | Excessive silence |
| Sample Rate | 10% | Recording quality |
| Bit Depth | 5% | Audio resolution |
| Dynamic Range | 10% | Volume variation |
| DC Offset | 5% | Signal bias |
| Speech Clarity | 10% | Based on SNR + speech activity |
| Format Quality | 10% | Lossless vs lossy encoding |

**Grades:** A+ (≥95), A (≥90), B (≥70), C (≥60), D (≥40), F (<40)

---

## Tech Stack

- **Backend:** Python 3.12, FastAPI, uvicorn
- **Audio Processing:** librosa, scipy, soundfile, ffmpeg
- **AI Models:** OpenAI Whisper (tiny), Silero VAD, pyannote-audio
- **Visualization:** matplotlib (dark theme)
- **Frontend:** Vanilla HTML/CSS/JS (no framework)
- **Inference:** CPU-only (no GPU required)

## Optional: Full Speaker Diarization

Speaker diarization requires a HuggingFace token:

1. Accept model terms at https://huggingface.co/pyannote/speaker-diarization-3.1
2. Set environment variable: `export HF_TOKEN=your_token_here`
3. Restart the server

Without the token, speaker count returns 0 (all other features work fine).

---

## Brand

- **Deep Indigo:** #1B2845
- **Electric Teal:** #00BFA6
- **Warm Saffron:** #F5A623
- **Background:** #0F172A

---

Built with ❤️ by [UsergyAI](https://usergy.ai)
