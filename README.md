# Audio Quality Checker

**Deep audio analysis tool for the AI data industry.**

Upload any audio file and get instant quality analysis: signal metrics, language detection, speaker count, speech quality (MOS), noise classification, and compliance checks against industry standards.

![Version](https://img.shields.io/badge/version-4.6.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![License](https://img.shields.io/badge/license-Proprietary-red)

## Features

### Analysis Modes
- **Quick Mode** (~30 sec) — Essential metrics: metadata, signal analysis, language detection, VAD
- **Deep Mode** (~2-3 min) — Full AI analysis: speakers, MOS, noise classification, transcription, emotion

### What It Analyzes
| Category | Metrics |
|----------|---------|
| **File Info** | Format, codec, duration, sample rate, bit depth, channels |
| **Signal** | Peak/RMS levels, dynamic range, DC offset, SNR |
| **Clipping** | Percentage, sample count, severity |
| **Silence** | Duration, percentage, longest segment |
| **Language** | Detection with confidence score (Whisper) |
| **Speech Activity** | VAD percentage (Silero) |
| **Speakers** | Count + timeline (pyannote) |
| **Speech Quality** | MOS 1-5 score (NISQA) |
| **Noise** | Classification + confidence (YAMNet) |
| **Transcription** | Full text + word count (Whisper) |
| **Reverb** | RT60 estimation |
| **Emotion** | Primary tone detection |

### Compliance Profiles
Check audio against industry standards:
- **General AI Data** — Common requirements
- **AI Data Platform Standard** — High-quality (48kHz, 24-bit, lossless)
- **Crowd Platform Standard** — Crowd-sourced specs
- **Open Speech Dataset** — Open-source standards
- **Telephony** — Call center (8kHz)
- **Broadcast** — Podcast/radio quality

### Quality Score
0-100 score with letter grade (A/B/C/D/F) based on:
- SNR (25%)
- Clipping (15%)
- Silence ratio (10%)
- Sample rate (10%)
- Bit depth (5%)
- Dynamic range (10%)
- DC offset (5%)
- Speech clarity (10%)
- Format quality (10%)

## Supported Formats

WAV, MP3, FLAC, OGG, M4A, AAC, OPUS, WebM, AIFF, WMA, AMR

**Max file size:** 1 GB  
**Max duration:** 4 hours

## Installation

### Requirements
- Python 3.11+
- FFmpeg (for audio processing)
- ~4GB RAM (8GB recommended for deep mode)

### Setup

```bash
# Clone repo
git clone https://github.com/Usergy-ops/audio-quality-checker.git
cd audio-quality-checker

# Create virtual environment
cd backend
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install AI models (optional, for deep mode)
pip install torch torchaudio whisper pyannote.audio

# Run server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Environment Variables

```bash
# CORS (comma-separated origins for production)
ALLOWED_ORIGINS=https://yourdomain.com,https://api.yourdomain.com

# Rate limiting (default: true)
RATE_LIMIT_ENABLED=true

# HuggingFace token (for pyannote speaker diarization)
HF_TOKEN=your_token_here
```

## API Reference

### Analyze Audio
```http
POST /api/analyze
Content-Type: multipart/form-data

file: <audio file>
mode: quick | deep (default: quick)
profile: default | defined_ai | appen | common_voice | telephony | broadcast
retain: true | false (consent to keep file)
```

### Batch Analyze
```http
POST /api/analyze-batch
Content-Type: multipart/form-data

files: <multiple audio files> (max 20)
mode: quick | deep
profile: <profile name>
```

### List Profiles
```http
GET /api/profiles
```

### Health Check
```http
GET /health
```

### Rate Limits
```http
GET /api/limits
```

**Rate Limits:**
- `/api/analyze` — 10 requests/minute per IP
- `/api/analyze-batch` — 5 requests/minute per IP
- `/api/keys/generate` — 2 requests/hour per IP

## Project Structure

```
audio-quality-checker/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app
│   │   ├── config.py         # Configuration
│   │   ├── routes/
│   │   │   └── analyze.py    # API endpoints
│   │   ├── analyzers/
│   │   │   ├── pipeline.py   # Main analysis pipeline
│   │   │   ├── metadata.py   # File info extraction
│   │   │   ├── signal.py     # Signal analysis
│   │   │   ├── language.py   # Language detection
│   │   │   ├── speakers.py   # Speaker diarization
│   │   │   └── ...           # Other analyzers
│   │   ├── models/
│   │   │   └── schemas.py    # Pydantic models
│   │   └── utils/
│   │       ├── audio.py      # Audio utilities
│   │       ├── scoring.py    # Quality scoring
│   │       └── profiles.py   # Compliance profiles
│   ├── requirements.txt
│   └── venv/
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
└── tests/
    └── samples/
```

## Deployment

### Production Checklist
- [ ] Set `ALLOWED_ORIGINS` to your domain(s)
- [ ] Set up SSL/HTTPS (use nginx + Let's Encrypt)
- [ ] Configure systemd service for auto-start
- [ ] Set up log rotation
- [ ] Configure firewall (allow only 80/443)
- [ ] Set `HF_TOKEN` for speaker diarization

### Example nginx config
```nginx
server {
    listen 443 ssl;
    server_name audio.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/audio.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/audio.yourdomain.com/privkey.pem;
    
    client_max_body_size 1G;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 600s;
    }
}
```

## Development

```bash
# Run in development mode (auto-reload)
uvicorn app.main:app --reload --port 8000

# Run tests
pytest tests/
```

## License

Proprietary — © 2026 UsergyAI. All rights reserved.

## Contact

- **Website:** https://usergy.ai
- **Email:** connect@usergy.ai
- **Twitter:** @UsergyAI
