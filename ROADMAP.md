# Audio Quality Checker — Enhancement Roadmap

## Completed ✅

### v2.x — Stability & Performance
- v2.0.0: Complete UI/UX redesign
- v2.1.0: Fix frontend-backend field mismatches
- v2.2.0: Fix speaker diarization for pyannote 4.x
- v2.3.0: Load audio once, pass to all analyzers
- v2.4.0: Parallel AI analyzers + parallel viz + startup preload
- v2.4.1: 10min timeout, rotating progress messages, speaker cap 60s

### v3.0 — Industry-Standard Metrics
- v3.0.0: NISQA MOS score (non-intrusive speech quality 1-5)
- v3.0.1: Custom spec profiles (Defined.ai, Appen, Common Voice, Telephony, Broadcast)
- v3.0.2: PDF report export (browser print-to-PDF)

### v3.1 — Batch & Business
- v3.1.0: Batch upload (up to 20 files), summary table, CSV export, mode toggle

### v3.2-3.4 — Analysis Features
- v3.2.0: Noise type classification (spectral: hum, broadband, impulse, tonal, rumble)
- v3.3.0: Transcription preview (first 30s via Whisper, segments, word count)
- v3.4.0: Interactive waveform (Wavesurfer.js: play, pause, zoom, timeline)

### v3.5-3.8 — Advanced Analysis & API
- v3.5.0: Reverb & echo detection (RT60, C50 clarity, autocorrelation echo, environment)
- v3.6.0: REST API with API keys (generate/validate/info), rate limiting
- v3.7.0: Compare mode (side-by-side 2 files, winner highlight)
- v3.8.0: Emotion/tone analysis (prosody: valence, arousal, VA space visualization)

### v4.0-4.6 — Polish + Production
- v4.0.0: UI/UX overhaul (Vanta.js clouds hero, Space Grotesk font)
- v4.1.0: Waveform HTML5 fallback, PDF auto-download
- v4.2.0: Report redesign with colored accent bars, section nav
- v4.3.x: PDF styling polish (Space Grotesk, score box, badges)
- v4.4.0: Quick/Deep analysis modes with localStorage preference
- v4.5.0: Bug fixes (batch mode param, unused imports)
- v4.6.0: Production-ready (validation, rate limiting, toast notifications)

### 2026-04-28 — UsergyAI Brand Foundation v2 rebrand + fix pack

**UI/UX rebrand (9 phases, 9 commits)**
- Phase 1: Foundation tokens — Root & Ember palette, JetBrains Mono added
- Phase 2: Nav + footer + brand assets + favicon (Brand Kit v2)
- Phase 3: Hero rebuild on Warm Paper with ember bracket frame; Vanta.js dropped
- Phase 4: Upload zone + mode toggle + buttons rebrand (pills, ember corners)
- Phase 5: Quality score card — ember-framed score block in brand display
- Phase 6 + 6b: Spec blocks for all metrics + sweep 50+ hardcoded colors
- Phase 7: Content scrub — brackets, triple-beats, kill em-dashes
- Phase 8: Accessibility + 44px touch targets + focus-visible rings
- Phases 1b + 1c: Finish color sweep (score/MOS/waveform/noise/reverb/batch)

**Bug fix pack (2.5-min deep analysis issue)**
- Phase A: Monitor script rewrite — 10 GB threshold, consecutive checks, active-conn skip, systemd MemoryHigh/Max/TimeoutStopSec
- Phase B: Persistent failure UX with retry button (replaces toast-only)
- Phase C: Real-time server-side progress + client polling endpoint

**Native malloc mitigation**
- MALLOC_ARENA_MAX=2 + OMP/MKL/OPENBLAS/NUMEXPR_NUM_THREADS=2
- ThreadPoolExecutor max_workers 4 → 2

**Downloadable report rewrite**
- Full UsergyAI Brand Foundation v2 template (inline brand mark, mono kickers, spec tables, zero gradients)
- Filename: UsergyAI-Audio-Report-{name}.html

**Infrastructure**
- Cloudflare DNS: tools.usergy.ai unproxied (direct to origin) — bypasses 100s CF Free plan proxy timeout

## Next up (priority order)

### 🔴 Short-term (worth doing soon)

- **Serialize deep mode** (max_workers=1) to eliminate remaining concurrent-burst native crash (documented in `projects/audio-checker-rebrand-2026-04-28/KNOWN-LIMITATIONS.md`)
- **Uploads retention cron** — delete files in `backend/uploads/` older than 30 days
- **Tidy the last 2 cosmetic brand leftovers**: `.accent-*` card-top bars + dead `#score-gradient` SVG

### 🟡 Medium-term

- Async job-queue API (POST returns job_id → worker processes → client polls /result)
- Auth on `/api/keys/generate` (currently only rate-limited)
- Lighthouse 100 across the board (should already be there after rebrand, but verify)
- GPU support — deep mode is 2-5 min on CPU, would be ~10x faster on GPU

### 🟢 Low-priority / future

- Audio repair suggestions ("Remove hum at 60Hz", "Normalize to -16 LUFS")
- Full transcription (not just 30s preview)
- Public dataset-card downloads for individual analyses
- Webhook callbacks for batch completion
- Mobile-native experience (currently responsive HTML works but not app-like)
- White-label version for embedding

## Version history

| Date | Version | Notes |
|---|---|---|
| 2026-04-08 | 4.0.0 | Initial development |
| 2026-04-09 | 4.4.0 | Quick/Deep modes |
| 2026-04-09 | 4.5.0 | Bug fixes |
| 2026-04-09 | 4.6.0 | Production deployment, SSL, monitoring |
| 2026-04-28 | 4.6.0 | UsergyAI rebrand + fix pack (no backend logic change, version unchanged) |
