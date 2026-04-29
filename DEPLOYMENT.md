# Audio Quality Checker — Deployment Documentation

**Last Updated:** 2026-04-28
**Version:** 4.6.0
**Status:** ✅ PRODUCTION LIVE

---

## Quick Reference

| Item | Value |
|------|-------|
| **Live URL** | https://tools.usergy.ai/audio-checker |
| **Health Check** | https://tools.usergy.ai/audio-checker/health |
| **Server** | AWS EC2 (16.112.59.183), Hyderabad, India |
| **Domain** | tools.usergy.ai |
| **SSL** | Let's Encrypt (expires Jul 8, 2026) |
| **Service** | `audio-checker.service` (systemd) |
| **Port** | 8000 (localhost only, nginx proxies) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        INTERNET                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  AWS EC2 (Ubuntu 24.04)                      │
│                   16.112.59.183                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │              NGINX (ports 80, 443)                   │   │
│   │   - SSL termination (Let's Encrypt)                  │   │
│   │   - Security headers                                 │   │
│   │   - Gzip compression                                 │   │
│   │   - Reverse proxy to :8000                           │   │
│   └─────────────────────────┬───────────────────────────┘   │
│                             │                                │
│                             ▼                                │
│   ┌─────────────────────────────────────────────────────┐   │
│   │           UVICORN + FASTAPI (port 8000)              │   │
│   │   - Audio analysis API                               │   │
│   │   - Static file serving                              │   │
│   │   - Rate limiting (slowapi)                          │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                 AI/ML MODELS                         │   │
│   │   - Whisper tiny (language detection)                │   │
│   │   - Silero VAD (speech activity)                     │   │
│   │   - pyannote 3.1 (speaker diarization)               │   │
│   │   - YAMNet (noise classification)                    │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## File Locations

### Application Code
```
/home/ubuntu/.openclaw/workspace/tools/audio-quality-checker/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Configuration
│   │   ├── routes/analyze.py    # API endpoints
│   │   ├── analyzers/           # Analysis modules
│   │   │   ├── clipping.py
│   │   │   ├── language.py      # Whisper
│   │   │   ├── noise.py         # YAMNet
│   │   │   ├── signal.py        # SNR, RMS
│   │   │   ├── silence.py
│   │   │   ├── speakers.py      # pyannote
│   │   │   ├── vad.py           # Silero VAD
│   │   │   └── ...
│   │   ├── models/schemas.py    # Pydantic models (SOURCE OF TRUTH)
│   │   └── utils/
│   │       ├── audio.py         # File validation
│   │       ├── profiles.py      # Quality profiles
│   │       └── scoring.py       # Quality scoring
│   ├── temp/                    # Temporary uploads (auto-cleaned)
│   ├── venv/                    # Python virtual environment
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── docs/
├── tests/
└── scripts/
    └── setup-hf-token.sh
```

### System Configuration
```
/etc/systemd/system/audio-checker.service   # Systemd service
/etc/nginx/sites-available/tools.usergy.ai  # Nginx config
/etc/nginx/sites-enabled/tools.usergy.ai    # Symlink
/etc/letsencrypt/live/tools.usergy.ai/      # SSL certificates
/usr/local/bin/audio-checker-monitor.sh     # Health monitor
/usr/local/bin/cleanup-audio-checker-temp.sh # Temp cleanup
/var/log/audio-checker-monitor.log          # Monitor logs
/var/log/audio-checker-cleanup.log          # Cleanup logs
```

---

## Service Management

### Basic Commands
```bash
# Check status
sudo systemctl status audio-checker

# Restart service
sudo systemctl restart audio-checker

# View logs
sudo journalctl -u audio-checker -f

# Reload nginx
sudo systemctl reload nginx
```

### Systemd Service Configuration
```ini
[Unit]
Description=Audio Quality Checker API
After=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/.openclaw/workspace/tools/audio-quality-checker/backend
Environment="PATH=/home/ubuntu/.openclaw/workspace/tools/audio-quality-checker/backend/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="HF_TOKEN=<your-huggingface-token>"
# Native malloc + thread caps (added 2026-04-28)
Environment="MALLOC_ARENA_MAX=2"
Environment="OMP_NUM_THREADS=2"
Environment="MKL_NUM_THREADS=2"
Environment="OPENBLAS_NUM_THREADS=2"
Environment="NUMEXPR_NUM_THREADS=2"
ExecStart=/home/ubuntu/.openclaw/workspace/tools/audio-quality-checker/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
# Memory guardrails
MemoryHigh=10G
MemoryMax=12G
TimeoutStopSec=120
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

---

## Cron Jobs

```bash
# Health monitor (every 5 minutes)
*/5 * * * * /usr/local/bin/audio-checker-monitor.sh

# Temp file cleanup (every hour)
0 * * * * /usr/local/bin/cleanup-audio-checker-temp.sh
```

### Monitor Script Features
- Checks if service is running → restarts if not
- Checks health endpoint → restarts if not responding
- Monitors memory usage → restarts if > 10 GB sustained for 2 consecutive checks AND no active connections on :8000
- Logs all checks to `/var/log/audio-checker-monitor.log`

---

## API Endpoints

| Endpoint | Method | Rate Limit | Description |
|----------|--------|------------|-------------|
| `/api/analyze` | POST | 10/min | Single file analysis |
| `/api/analyze-batch` | POST | 5/min | Multiple files |
| `/api/profiles` | GET | - | List quality profiles |
| `/api/limits` | GET | - | Show rate limits |
| `/health` | GET | - | Health check |

### Analysis Modes
- **Quick Mode:** Basic metadata + signal analysis (~1-2 seconds)
- **Deep Mode:** Full AI analysis including language, VAD, speaker diarization (~10-30 seconds)

### Quality Profiles
- `default` — General AI training data
- `defined_ai` — Defined.ai specifications
- `appen` — Appen requirements
- `common_voice` — Mozilla Common Voice
- `telephony` — Call center/8kHz audio
- `broadcast` — Broadcast quality

---

## Supported Audio Formats

WAV, MP3, FLAC, OGG, M4A, AAC, OPUS, WebM, AIFF, WMA, AMR

**Max file size:** 1 GB

---

## Security Configuration

### Nginx Security Headers
```
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

### Firewall (UFW)
```bash
sudo ufw status
# 22/tcp (SSH)
# 80/tcp (HTTP → redirect to HTTPS)
# 443/tcp (HTTPS)
```

### SSL/TLS
- Certificate: Let's Encrypt
- Protocol: TLS 1.3
- Cipher: TLS_AES_256_GCM_SHA384
- Auto-renewal: Certbot timer

---

## Environment Variables

| Variable | Description | Current Value |
|----------|-------------|---------------|
| `HF_TOKEN` | HuggingFace token for pyannote | `hf_aQsDMMh...` (set in systemd) |
| `ALLOWED_ORIGINS` | CORS origins (optional) | Not set (allows all) |

---

## Monitoring

### Internal Monitoring
- **Health check:** Every 5 minutes via cron
- **Auto-restart:** On failure or high memory
- **Logs:** `/var/log/audio-checker-monitor.log`

### External Monitoring (UptimeRobot)
- **URL:** `https://tools.usergy.ai/audio-checker/health`
- **Type:** HTTP(s) - Keyword
- **Keyword:** `healthy`
- **Interval:** 5 minutes

**Note:** Use Keyword monitoring, not HTTP(s) HEAD — FastAPI returns 405 for HEAD requests.

---

## Troubleshooting

### Service won't start
```bash
# Check logs
sudo journalctl -u audio-checker -n 50

# Check if port is in use
ss -tlnp | grep 8000

# Manual start for debugging
cd /home/ubuntu/.openclaw/workspace/tools/audio-quality-checker/backend
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 502 Bad Gateway
```bash
# Check if backend is running
curl http://127.0.0.1:8000/health

# Restart service
sudo systemctl restart audio-checker
```

### Static files 404
```bash
# Check nginx config
sudo nginx -t

# Check if paths are correct
curl -I https://tools.usergy.ai/audio-checker/style.css
```

### High memory usage
```bash
# Check current memory
systemctl show audio-checker --property=MemoryCurrent

# Restart service
sudo systemctl restart audio-checker
```

---

## Deployment History

| Date | Version | Changes |
|------|---------|---------|
| 2026-04-28 | 4.6.0 | UsergyAI rebrand (Root & Ember); monitor threshold raised to 10 GB with in-flight guard; MALLOC_ARENA_MAX + thread caps; PDF report rebranded; CF unproxy on tools.usergy.ai |
| 2026-04-09 | 4.6.0 | Production deployment, SSL, monitoring |
| 2026-04-09 | 4.5.0 | Bug fixes, batch mode |
| 2026-04-09 | 4.4.0 | Quick/Deep analysis modes |
| 2026-04-08 | 4.0.0 | Initial development |

---

## Backup & Recovery

### Code Backup
```bash
# Git repository
https://github.com/Usergy-ops/audio-quality-checker

# Local backups
/home/ubuntu/.openclaw/workspace/backups/audio-quality-checker-*.tar.gz
```

### Configuration Backup
```bash
# Backup configs
sudo cp /etc/systemd/system/audio-checker.service ~/backup/
sudo cp /etc/nginx/sites-available/tools.usergy.ai ~/backup/
```

### Recovery Steps
1. Clone repo: `git clone https://github.com/Usergy-ops/audio-quality-checker.git`
2. Install deps: `pip install -r requirements.txt`
3. Restore systemd service
4. Restore nginx config
5. Restart services

---

## Cost

| Resource | Cost |
|----------|------|
| AWS EC2 | Existing instance (no extra cost) |
| SSL Certificate | Free (Let's Encrypt) |
| Domain | Existing (tools.usergy.ai) |
| AI Models | Free (open source) |
| **Total** | **$0/month** |

---

## Future Improvements

1. **CDN Setup** — Cloudflare for global performance (see `docs/CDN-SETUP.md`)
2. **API Keys** — Rate limiting per user
3. **Batch Processing** — Queue system for large batches
4. **Custom Profiles** — User-defined quality profiles
5. **Webhooks** — Callback on analysis complete

---

## Contacts

- **Repository:** https://github.com/Usergy-ops/audio-quality-checker
- **Live Site:** https://tools.usergy.ai/audio-checker
- **Owner:** Swaroop (swaroop@usergy.ai)

---

## 2026-04-28 Session Docs

For the full story of today's UI rebrand, bug fix pack, and infrastructure
hardening, see:

`/home/ubuntu/.openclaw/workspace/projects/audio-checker-rebrand-2026-04-28/`

Contains:
- `SESSION-SUMMARY.md` — the whole day
- `COMMITS.md` — 14 commits with detail
- `REBRAND.md` — UI/UX before/after
- `FIX-PACK.md` — the 2.5-min bug investigation + fix
- `BRAND-PDF-REPORT.md` — downloadable report template rewrite
- `MALLOC-MITIGATION.md` — native crash Phase 2 details (embedded in FIX-PACK.md)
- `CF-524-FIX.md` — Cloudflare proxy timeout fix
- `AUDIT-REPORT.md` — 7-phase final validation
- `KNOWN-LIMITATIONS.md` — remaining concurrent-burst crash + fix options
