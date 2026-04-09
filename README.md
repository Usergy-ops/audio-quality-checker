# Audio Quality Checker

A free audio analysis tool by [UsergyAI](https://usergy.ai). Upload any audio file and get a detailed quality report: scores, signal metrics, language detection, speech analysis, compliance checks, and visualizations.

## Features

| Category | What you get |
|----------|-------------|
| File info | Format, codec, duration, sample rate, bit depth, bit rate, channels, file size |
| Signal analysis | Peak amplitude, RMS level, dynamic range, SNR, DC offset |
| Clipping detection | Clipped sample count, percentage, timestamped regions |
| Silence analysis | Silent regions, percentage, longest silent stretch |
| Language detection | 99 languages with confidence scores (Whisper tiny) |
| Speech activity | Speech vs. noise regions with timestamps (Silero VAD) |
| Speaker count | Number of distinct speakers and timeline (pyannote) |
| Quality score | Weighted 0-100 across 9 components, graded A+ through F |
| Compliance | Pass / warn / fail against common AI data project specs |
| Visualizations | Waveform, mel spectrogram, loudness chart, speaker timeline |

**Supported formats:** WAV, MP3, FLAC, OGG, AAC, M4A, AIFF, OPUS, WebM, WMA, AMR (up to 1 GB)

---

## Quick Start

### Prerequisites

- Python 3.12+
- ffmpeg (`sudo apt install ffmpeg`)
- Linux (tested on Ubuntu 24.04)

### Install

```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install torch==2.6.0+cpu torchaudio==2.6.0+cpu --index-url https://download.pytorch.org/whl/cpu
```

### Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in your browser.

### Remote access (SSH tunnel)

```bash
ssh -i your-key.pem -L 8000:localhost:8000 ubuntu@YOUR_SERVER_IP
```

Then open `http://localhost:8000` locally. Port 8000 is not exposed via firewall; the server is only accessible through SSH tunnel.

---

## API

### POST /api/analyze

Upload an audio file for analysis.

**Parameters:**
- `file` (required) - Audio file (multipart form)
- `retain` (optional, default: `true`) - If `true`, file is retained for quality improvement. If `false`, file is deleted after analysis.

```bash
curl -X POST http://localhost:8000/api/analyze \
  -F "file=@recording.wav" \
  -F "retain=false"
```

**Response:** JSON with all analysis data, quality score, compliance checks, and base64-encoded visualization images.

### GET /health

```bash
curl http://localhost:8000/health
```

### Swagger docs

`http://localhost:8000/docs`

---

## Architecture

```
audio-quality-checker/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, static file serving, CORS
│   │   ├── config.py            # Settings, weights, limits, paths
│   │   ├── models/
│   │   │   └── schemas.py       # Pydantic response models
│   │   ├── routes/
│   │   │   └── analyze.py       # POST /api/analyze endpoint
│   │   ├── analyzers/
│   │   │   ├── metadata.py      # ffprobe metadata extraction
│   │   │   ├── signal.py        # Peak, RMS, dynamic range, DC offset
│   │   │   ├── clipping.py      # Clipping detection
│   │   │   ├── silence.py       # Silence regions and percentage
│   │   │   ├── snr.py           # Signal-to-noise ratio
│   │   │   ├── language.py      # Whisper language detection
│   │   │   ├── vad.py           # Silero VAD speech activity
│   │   │   ├── speakers.py      # Pyannote speaker diarization
│   │   │   └── pipeline.py      # Orchestrates all analyzers
│   │   └── utils/
│   │       ├── audio.py         # File validation, temp management, retention
│   │       ├── scoring.py       # Quality scoring engine and compliance
│   │       └── visualizations.py # Waveform, spectrogram, loudness, speakers
│   ├── requirements.txt
│   ├── temp/                    # Temporary files (auto-cleaned)
│   └── uploads/                 # Retained files (gitignored)
├── frontend/
│   ├── index.html               # Single page app
│   ├── style.css                # Minimal light theme
│   └── app.js                   # Upload, progress, results rendering
├── tests/
│   └── samples/                 # Test audio files
├── docs/
│   ├── PLAN.md                  # Build plan (all 45 steps complete)
│   ├── FEATURES.md              # Feature specification
│   ├── TECH-STACK.md            # Technology decisions
│   ├── DECISIONS.md             # Architecture decisions
│   └── ROADMAP.md               # Future enhancements
├── backups/                     # Versioned tar.gz archives (in parent)
├── .gitignore
└── README.md
```

## Quality Scoring

9 weighted components:

| Component | Weight | What it measures |
|-----------|--------|-----------------|
| SNR | 25% | Signal-to-noise ratio |
| Clipping | 15% | Audio clipping percentage |
| Silence Ratio | 10% | Excessive silence |
| Sample Rate | 10% | Recording quality (Hz) |
| Bit Depth | 5% | Audio resolution (bits) |
| Dynamic Range | 10% | Volume variation (dB) |
| DC Offset | 5% | Signal centering bias |
| Speech Clarity | 10% | Derived from SNR + speech activity |
| Format Quality | 10% | Lossless vs. lossy encoding |

**Grades:** A+ (95+), A (90+), B (70+), C (60+), D (40+), F (<40)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, uvicorn |
| Audio processing | librosa, scipy, soundfile, ffmpeg (ffprobe) |
| AI models | Whisper tiny (language), Silero VAD (speech), pyannote (speakers) |
| Visualizations | matplotlib |
| Frontend | Vanilla HTML / CSS / JS (no framework) |
| Inference | CPU-only, no GPU required |

## Data Retention

- By default, uploaded files are retained in `backend/uploads/` with metadata for quality improvement
- Users can uncheck the consent checkbox to opt out; their file is deleted immediately after analysis
- Temporary files are always deleted in a `finally` block regardless of success or failure
- `uploads/` is gitignored and never committed

## Speaker Diarization (optional)

Full speaker diarization requires a HuggingFace token:

1. Accept terms at https://huggingface.co/pyannote/speaker-diarization-3.1
2. `export HF_TOKEN=your_token_here`
3. Restart the server

Without the token, speaker count returns 0 (everything else works).

---

## Security

- Port 8000 is **not exposed** via firewall; access only through SSH tunnel
- CORS set to allow all origins (suitable for dev/internal use)
- File uploads validated by extension and size before processing
- Temp files cleaned in `finally` blocks (guaranteed cleanup)
- `uploads/` and `temp/` are gitignored
- No authentication (internal tool); add auth before public deployment
- No secrets or API keys in source code
- All file operations use UUID-based temp names to prevent path traversal

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v2.0.0 | 2026-04-08 | Complete UI/UX redesign: light minimal theme, typography-first |
| v1.2.0 | 2026-04-08 | Bug fixes (5) + UX improvements (7): staged messages, score colors, mobile nav |
| v1.1.0 | 2026-04-08 | File retention with opt-in consent checkbox |
| v1.0.0 | 2026-04-08 | Initial release: full analysis pipeline, 6 analyzers, visualizations |

---

Built by [UsergyAI](https://usergy.ai)
