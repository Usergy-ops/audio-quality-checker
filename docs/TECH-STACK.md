# Audio Quality Checker — Tech Stack

Complete technical details of all tools, libraries, and models used.

---

## Server Requirements

| Resource | Minimum | Current Server | Status |
|----------|---------|----------------|--------|
| RAM | 4 GB (8 GB recommended) | 16 GB (14 GB free) | ✅ Excellent |
| Disk | 10 GB free | 32 GB free | ✅ Excellent |
| CPU | 2 cores | 4 cores (Intel Xeon 2.5GHz) | ✅ Good |
| GPU | Not required | None | ✅ OK (CPU mode) |
| Python | 3.9+ | 3.12.3 | ✅ Perfect |
| ffmpeg | 4.0+ | 6.1.1 | ✅ Already installed |
| OS | Linux (Ubuntu 20.04+) | Ubuntu Linux x86_64 | ✅ Perfect |

---

## Backend Stack

### Core Framework
| Component | Package | Version | License | Purpose |
|-----------|---------|---------|---------|---------|
| Web Framework | `fastapi` | latest | MIT | REST API server |
| ASGI Server | `uvicorn` | latest | BSD | Runs FastAPI |
| File Handling | `python-multipart` | latest | Apache 2.0 | File uploads |
| Async Support | `aiofiles` | latest | Apache 2.0 | Async file I/O |

### Audio Processing
| Component | Package | Version | License | Purpose |
|-----------|---------|---------|---------|---------|
| Signal Processing | `librosa` | 0.10.x | ISC | Core audio analysis |
| Scientific Computing | `scipy` | latest | BSD | Signal processing |
| Numerical | `numpy` | latest | BSD | Array operations |
| Audio I/O | `soundfile` | latest | BSD | Read audio files |
| Format Conversion | `pydub` | latest | MIT | Format handling |
| Metadata | `ffmpeg-python` | latest | Apache 2.0 | ffprobe wrapper |

### AI Models
| Component | Package | Model | Size | License | Purpose |
|-----------|---------|-------|------|---------|---------|
| Language Detection | `openai-whisper` | tiny | ~75 MB | MIT | Detect audio language |
| Speech Recognition | `openai-whisper` | tiny | ~75 MB | MIT | Optional transcription |
| Voice Activity | `silero-vad` | v4 | ~2 MB | MIT | Speech/silence detection |
| Speaker Diarization | `pyannote-audio` | community-1 | ~200 MB | MIT | Speaker count & timeline |
| Sound Classification | `yamnet` (optional) | - | ~20 MB | Apache 2.0 | Noise type detection |

### PyTorch (CPU)
| Component | Package | Version | Notes |
|-----------|---------|---------|-------|
| Deep Learning | `torch` | 2.x | CPU-only build, ~800 MB |
| Audio Backend | `torchaudio` | 2.x | For Whisper |

### Visualization
| Component | Package | Purpose |
|-----------|---------|---------|
| Charts | `matplotlib` | Waveform, spectrogram, charts |
| Display | `librosa.display` | Audio visualization helpers |

### Output Generation
| Component | Package | Purpose |
|-----------|---------|---------|
| PDF Reports | `weasyprint` or `reportlab` | PDF export (v2) |
| JSON | built-in | API responses |

---

## Frontend Stack

### Option A: React/Next.js (Recommended)
| Component | Package | Purpose |
|-----------|---------|---------|
| Framework | Next.js 14 | React framework |
| Styling | Tailwind CSS | Utility-first CSS |
| Upload | react-dropzone | Drag & drop upload |
| Waveform | wavesurfer.js | Audio visualization |
| Charts | Chart.js or recharts | Data visualization |
| HTTP | axios or fetch | API calls |

### Option B: Plain HTML + JS (Simpler)
| Component | Tool | Purpose |
|-----------|------|---------|
| HTML | Vanilla | Structure |
| CSS | Tailwind CSS (CDN) | Styling |
| JS | Vanilla + fetch | Interactivity |
| Upload | Native drag & drop | File upload |
| Waveform | wavesurfer.js | Audio visualization |

---

## Model Details

### Whisper Tiny
- **Source:** OpenAI
- **Model:** `tiny` (smallest, fastest)
- **Size:** 75 MB
- **Languages:** 99 languages supported
- **Speed:** ~5-10s per 30s audio on CPU
- **Usage:** Language detection from first 30 seconds
- **HuggingFace:** `openai/whisper-tiny`

### Silero VAD
- **Source:** Silero Team
- **Model:** v4
- **Size:** ~2 MB
- **Speed:** Near real-time
- **Usage:** Speech activity detection, silence regions
- **GitHub:** `snakers4/silero-vad`

### pyannote-audio
- **Source:** pyannote.ai
- **Model:** `speaker-diarization-community-1`
- **Size:** ~200 MB
- **License:** MIT (community version)
- **Speed:** ~10-30s per minute of audio on CPU
- **Usage:** Speaker count, speaker timeline
- **HuggingFace:** `pyannote/speaker-diarization-community-1`
- **Note:** Requires HuggingFace token for first download (free account)

### YAMNet (Optional, v2)
- **Source:** Google/TensorFlow
- **Model:** YAMNet
- **Size:** ~20 MB
- **Usage:** Classify background noise types (music, traffic, crowd, etc.)
- **TensorFlow Hub:** `google/yamnet`

---

## Supported Audio Formats

| Format | Extension | Codec | Notes |
|--------|-----------|-------|-------|
| WAV | .wav | PCM | Uncompressed, best quality |
| MP3 | .mp3 | MPEG-1 Layer 3 | Most common |
| FLAC | .flac | FLAC | Lossless compressed |
| OGG | .ogg | Vorbis | Open source |
| M4A | .m4a | AAC | Apple/iOS |
| AAC | .aac | AAC | Common mobile format |
| OPUS | .opus | Opus | Modern, efficient |
| WebM | .webm | Vorbis/Opus | Browser recordings |
| AIFF | .aiff, .aif | PCM | Apple uncompressed |
| WMA | .wma | WMA | Windows |
| AMR | .amr | AMR | Phone recordings |

All formats handled by ffmpeg conversion to WAV for processing.

---

## API Response Schema

```json
{
  "success": true,
  "analysis": {
    "file_info": {
      "filename": "string",
      "format": "string",
      "codec": "string",
      "duration_seconds": 0.0,
      "sample_rate": 48000,
      "bit_rate": 320000,
      "bit_depth": 16,
      "channels": 2,
      "channel_layout": "stereo",
      "file_size_bytes": 0
    },
    "signal_analysis": {
      "peak_amplitude_db": -3.0,
      "rms_level_db": -18.0,
      "dynamic_range_db": 15.0,
      "dc_offset": 0.001,
      "clipping": {
        "detected": false,
        "percentage": 0.0,
        "regions": []
      },
      "silence": {
        "percentage": 5.2,
        "regions": [{"start": 0.0, "end": 0.5}]
      },
      "snr_db": 25.0
    },
    "ai_analysis": {
      "language": {
        "detected": "en",
        "confidence": 0.95,
        "name": "English"
      },
      "speech_activity": {
        "speech_percentage": 85.0,
        "regions": [{"start": 0.5, "end": 120.0}]
      },
      "speakers": {
        "count": 2,
        "timeline": [
          {"speaker": 1, "start": 0.5, "end": 30.0},
          {"speaker": 2, "start": 30.5, "end": 60.0}
        ]
      }
    },
    "quality": {
      "score": 85,
      "grade": "A",
      "summary": "Great quality, usable for most projects",
      "breakdown": {
        "snr": {"score": 90, "weight": 0.25},
        "clipping": {"score": 100, "weight": 0.15},
        "silence": {"score": 80, "weight": 0.10},
        ...
      }
    },
    "compliance": {
      "sample_rate": {"status": "pass", "value": 48000, "threshold": ">=16000"},
      "bit_depth": {"status": "pass", "value": 16, "threshold": ">=16"},
      "channels": {"status": "warn", "value": 2, "expected": 1, "message": "Stereo (many projects require mono)"},
      "clipping": {"status": "pass"},
      "snr": {"status": "pass", "value": 25, "threshold": ">=15"},
      "silence": {"status": "warn", "value": 5.2, "threshold": "<=10"}
    },
    "visualizations": {
      "waveform": "base64...",
      "spectrogram": "base64...",
      "loudness": "base64...",
      "speakers": "base64..."
    }
  },
  "processing_time_seconds": 25.3
}
```

---

## Hosting Plan

### Development (Now)
- **Where:** Existing AWS EC2
- **Instance:** t3.xlarge equivalent (4 vCPU, 16GB RAM)
- **Cost:** Already running (OpenClaw server)

### Production (Later)
- **Where:** Azure (using $5K credits)
- **Instance:** Standard_B2ms (2 vCPU, 8GB) or Standard_D4s_v3 (4 vCPU, 16GB)
- **Region:** Central India
- **Cost:** ~$60-140/month (from credits)
- **Domain:** tools.usergy.ai or usergy.ai/tools
