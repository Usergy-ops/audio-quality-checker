# Audio Quality Checker — Enhancement Roadmap

## v3.0 — Industry-Standard Metrics (1-2 days)
- NISQA MOS score (torchmetrics, non-intrusive speech quality 1-5)
- Noise type classification (YAMNet, 521 event types)
- Transcription preview (first 30s, Whisper already loaded)

## v3.1 — Business Features (1-2 days)
- PDF report export (WeasyPrint or HTML-to-PDF)
- Custom spec profiles (Defined.ai, Appen, Common Voice, Custom)

## v3.2 — Killer Features (2-3 days)
- Batch upload / multi-file analysis with summary table
- Interactive waveform with wavesurfer.js (playable, zoomable)

## v3.3 — Differentiators (2-3 days)
- Reverb / echo detection (RT60 estimation)
- Emotion / sentiment detection (speechbrain)
- REST API with API keys and rate limiting

## v4.0 — Platform (longer term)
- Comparison mode (side-by-side 2 files)
- Audio fingerprint / duplicate detection
- History / dashboard with trends
- User accounts

## Polish
- Confidence value audit (ensure all % fields consistent)
- Better error/warning UX with icons
- Version bump + backup after each milestone
