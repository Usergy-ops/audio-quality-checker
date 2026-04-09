<div align="center">

# 🎵 Audio Quality Checker

**Deep audio analysis tool for the AI data industry**

[![Version](https://img.shields.io/badge/version-4.6.0-blue.svg)](https://github.com/Usergy-ops/audio-quality-checker/releases)
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)

[Features](#features) • [Quick Start](#quick-start) • [API Reference](#api-reference) • [Deployment](#deployment) • [Contributing](#contributing)

---

*Upload any audio file and get instant quality analysis: signal metrics, language detection, speaker count, speech quality (MOS), noise classification, and compliance checks against industry standards.*

</div>

## ✨ Features

### Analysis Modes

| Mode | Time | What's Included |
|------|------|-----------------|
| **Quick** | ~30 sec | Metadata, signal analysis, language detection, VAD, visualizations |
| **Deep** | ~2-3 min | Everything above + speakers, MOS, noise classification, transcription, emotion |

### What It Analyzes

<table>
<tr>
<td width="50%">

**📊 Signal Analysis**
- Peak/RMS levels
- Dynamic range
- DC offset
- Signal-to-Noise Ratio (SNR)
- Clipping detection
- Silence analysis

</td>
<td width="50%">

**🤖 AI Analysis**
- Language detection (Whisper)
- Speech activity detection (Silero VAD)
- Speaker diarization (pyannote)
- Speech quality MOS (NISQA)
- Noise classification (YAMNet)
- Transcription (Whisper)

</td>
</tr>
</table>

### Quality Score

0-100 score with letter grade (A/B/C/D/F) based on weighted metrics:

```
SNR (25%) + Clipping (15%) + Silence (10%) + Sample Rate (10%) +
Bit Depth (5%) + Dynamic Range (10%) + DC Offset (5%) +
Speech Clarity (10%) + Format Quality (10%) = Total Score
```

### Compliance Profiles

Check audio against industry standards:

| Profile | Sample Rate | Bit Depth | SNR | Use Case |
|---------|-------------|-----------|-----|----------|
| General AI Data | ≥16 kHz | ≥16-bit | ≥20 dB | Common requirements |
| AI Data Platform | ≥48 kHz | ≥24-bit | ≥25 dB | High-quality collection |
| Crowd Platform | ≥16 kHz | ≥16-bit | ≥15 dB | Crowd-sourced data |
| Telephony | ≥8 kHz | ≥16-bit | ≥10 dB | Call center audio |
| Broadcast | ≥44.1 kHz | ≥16-bit | ≥30 dB | Podcast/radio |

### Supported Formats

`WAV` `MP3` `FLAC` `OGG` `M4A` `AAC` `OPUS` `WebM` `AIFF` `WMA` `AMR`

**Limits:** Max 1 GB file size • Max 4 hours duration

---

## 🚀 Quick Start

### Requirements

- Python 3.11+
- FFmpeg
- 4GB RAM (8GB recommended for Deep mode)

### Installation

```bash
# Clone repository
git clone https://github.com/Usergy-ops/audio-quality-checker.git
cd audio-quality-checker

# Setup backend
cd backend
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Install AI models (optional, for Deep mode)
pip install torch torchaudio openai-whisper pyannote.audio

# Run server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 in your browser.

### Environment Variables

```bash
# Production CORS (comma-separated)
ALLOWED_ORIGINS=https://yourdomain.com

# Rate limiting (default: true)
RATE_LIMIT_ENABLED=true

# HuggingFace token (for speaker diarization)
HF_TOKEN=your_token_here
```

---

## 📡 API Reference

### Analyze Single File

```http
POST /api/analyze
Content-Type: multipart/form-data
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file` | file | required | Audio file to analyze |
| `mode` | string | `quick` | `quick` or `deep` |
| `profile` | string | `default` | Compliance profile |
| `retain` | boolean | `true` | Consent to keep file |

**Response:** Full analysis with quality score, signal metrics, AI analysis, and compliance results.

### Batch Analyze

```http
POST /api/analyze-batch
Content-Type: multipart/form-data
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `files` | files | required | Up to 20 audio files |
| `mode` | string | `quick` | `quick` or `deep` |
| `profile` | string | `default` | Compliance profile |

### Other Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/profiles` | GET | List compliance profiles |
| `/api/limits` | GET | Show rate limits |
| `/health` | GET | Health check |

### Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/api/analyze` | 10/minute per IP |
| `/api/analyze-batch` | 5/minute per IP |
| `/api/keys/generate` | 2/hour per IP |

---

## 🌐 Deployment

### Production Checklist

- [ ] Set `ALLOWED_ORIGINS` environment variable
- [ ] Configure SSL/HTTPS (nginx + Let's Encrypt)
- [ ] Set up systemd service
- [ ] Configure log rotation
- [ ] Set `HF_TOKEN` for speaker diarization
- [ ] Configure firewall

### Example nginx Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name audio.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/audio.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/audio.yourdomain.com/privkey.pem;
    
    client_max_body_size 1G;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 600s;
    }
}
```

### Systemd Service

```ini
# /etc/systemd/system/audio-checker.service
[Unit]
Description=Audio Quality Checker
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/audio-quality-checker/backend
Environment="ALLOWED_ORIGINS=https://yourdomain.com"
ExecStart=/opt/audio-quality-checker/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 📁 Project Structure

```
audio-quality-checker/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Configuration
│   │   ├── routes/
│   │   │   └── analyze.py       # API endpoints
│   │   ├── analyzers/
│   │   │   ├── pipeline.py      # Analysis orchestration
│   │   │   ├── metadata.py      # File info (ffprobe)
│   │   │   ├── signal.py        # Signal analysis
│   │   │   ├── language.py      # Language detection
│   │   │   ├── speakers.py      # Speaker diarization
│   │   │   ├── nisqa.py         # MOS scoring
│   │   │   └── ...
│   │   ├── models/
│   │   │   └── schemas.py       # Pydantic models
│   │   └── utils/
│   │       ├── audio.py         # Audio utilities
│   │       ├── scoring.py       # Quality scoring
│   │       └── profiles.py      # Compliance profiles
│   └── requirements.txt
├── frontend/
│   ├── index.html               # Main UI
│   ├── style.css                # Styles
│   └── app.js                   # Frontend logic
├── tests/
│   └── samples/                 # Test audio files
├── .github/
│   └── ISSUE_TEMPLATE/          # Issue templates
├── README.md
├── CONTRIBUTING.md
├── SECURITY.md
└── .gitignore
```

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 🔒 Security

Found a vulnerability? Please read [SECURITY.md](SECURITY.md) for responsible disclosure.

## 📄 License

Proprietary — © 2026 [UsergyAI](https://usergy.ai). All rights reserved.

---

<div align="center">

**Built with ❤️ by [UsergyAI](https://usergy.ai)**

[Website](https://usergy.ai) • [Twitter](https://twitter.com/UsergyAI) • [Email](mailto:connect@usergy.ai)

</div>
