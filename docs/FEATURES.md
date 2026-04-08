# Audio Quality Checker — Complete Feature Spec

Every metric and feature the tool will provide.

---

## File Size & Format Limits

- **Maximum file size:** 1 GB (1000 MB)
- **Supported formats:** WAV, MP3, FLAC, OGG, M4A, AAC, OPUS, WebM, AIFF, WMA, AMR
- **Processing limit:** Files longer than 30 minutes may have partial AI analysis (first 5 min sample for language/speaker detection)

---

## Section A: File Information

Instant extraction via ffprobe — no processing delay.

| Metric | Description | Example |
|--------|-------------|---------|
| **File name** | Original filename | recording_001.wav |
| **File size** | Size in bytes/KB/MB | 45.2 MB |
| **Format** | Container format | WAV |
| **Codec** | Audio codec | PCM S16 LE |
| **Duration** | Length in HH:MM:SS.ms | 00:05:32.450 |
| **Sample rate** | Samples per second (Hz) | 48000 Hz |
| **Bit rate** | Data rate (kbps) | 1536 kbps |
| **Bit depth** | Bits per sample | 16-bit |
| **Channel count** | Number of channels | 2 |
| **Channel layout** | Channel arrangement | stereo / mono / 5.1 |

---

## Section B: Signal Analysis

Computed via librosa + numpy/scipy.

| Metric | Description | Good Value | Warning | Bad |
|--------|-------------|------------|---------|-----|
| **Peak amplitude** | Maximum signal level (dBFS) | -3 to -1 dBFS | -6 to -3 or 0 dBFS | 0 dBFS (clipping) |
| **RMS level** | Average loudness (dBFS) | -20 to -14 dBFS | -25 to -20 or -14 to -10 | < -30 or > -6 |
| **Dynamic range** | Difference between loud/quiet (dB) | > 12 dB | 6-12 dB | < 6 dB (compressed) |
| **DC offset** | Waveform center bias | < 0.01 | 0.01 - 0.05 | > 0.05 |
| **Clipping %** | % of samples at max amplitude | 0% | < 0.1% | > 0.1% |
| **Clipping regions** | Timestamps where clipping occurs | — | — | List of [start, end] |
| **Silence %** | % of total duration that's silent | 0-5% | 5-15% | > 15% |
| **Silence regions** | Timestamps of silent sections | — | — | List of [start, end] |
| **SNR (Signal-to-Noise)** | Ratio of signal to noise floor (dB) | > 25 dB | 15-25 dB | < 15 dB |
| **Noise floor** | Estimated background noise level (dBFS) | < -50 dBFS | -50 to -40 dBFS | > -40 dBFS |

---

## Section C: Speech/Voice Activity

Computed via Silero VAD.

| Metric | Description | Example |
|--------|-------------|---------|
| **Speech %** | Percentage of audio containing speech | 85.3% |
| **Silence/noise %** | Percentage that is non-speech | 14.7% |
| **Speech regions** | Timestamps of speech segments | [[0.5, 30.2], [31.0, 120.5], ...] |
| **Longest speech segment** | Duration of longest continuous speech | 45.2 seconds |
| **Longest silence** | Duration of longest silent gap | 3.1 seconds |

---

## Section D: AI-Powered Analysis

### Language Detection (Whisper)

| Metric | Description | Example |
|--------|-------------|---------|
| **Detected language** | ISO 639-1 code | en |
| **Language name** | Full name | English |
| **Confidence** | Detection confidence | 95.2% |
| **Alternative languages** | Other possible languages | [("de", 3.1%), ("nl", 1.2%)] |

### Speaker Analysis (pyannote-audio)

| Metric | Description | Example |
|--------|-------------|---------|
| **Speaker count** | Number of distinct speakers | 2 |
| **Speaker timeline** | Who speaks when | [{"speaker": 1, "start": 0.5, "end": 30.0}, ...] |
| **Speaker distribution** | % of speech per speaker | {1: 55%, 2: 45%} |
| **Turn count** | Number of speaker turns | 24 |
| **Overlap %** | % of audio with overlapping speech | 2.3% |

### Noise Classification (YAMNet, v2)

| Metric | Description | Example |
|--------|-------------|---------|
| **Primary noise type** | Main background noise | Office ambient |
| **Noise types detected** | All detected noise categories | [("speech", 0.8), ("keyboard", 0.15), ("hvac", 0.05)] |

---

## Section E: Quality Score

Single 0-100 score with letter grade.

### Scoring Algorithm

| Component | Weight | Scoring Logic |
|-----------|--------|---------------|
| **SNR** | 25% | 30+ dB = 100, 25 dB = 80, 20 dB = 60, 15 dB = 40, <10 dB = 0 |
| **Clipping** | 15% | 0% = 100, <0.01% = 80, <0.1% = 50, <1% = 20, >1% = 0 |
| **Silence ratio** | 10% | <5% = 100, <10% = 80, <20% = 50, <30% = 20, >30% = 0 |
| **Sample rate** | 10% | ≥48kHz = 100, ≥44.1kHz = 90, ≥22kHz = 70, ≥16kHz = 50, <16kHz = 20 |
| **Bit depth** | 5% | 24-bit = 100, 16-bit = 80, 8-bit = 20 |
| **Dynamic range** | 10% | >20dB = 100, >15dB = 80, >10dB = 50, >6dB = 30, <6dB = 0 |
| **DC offset** | 5% | <0.005 = 100, <0.01 = 80, <0.05 = 50, >0.05 = 0 |
| **Speech clarity** | 10% | Derived from SNR + spectral flatness |
| **Format quality** | 10% | Lossless = 100, High bitrate lossy = 70, Low bitrate = 30 |

### Grade Mapping

| Score | Grade | Description |
|-------|-------|-------------|
| 90-100 | A+ | Excellent — ready for any project |
| 80-89 | A | Great quality — minor issues at most |
| 70-79 | B | Good — usable for most projects |
| 60-69 | C | Acceptable — has notable issues |
| 40-59 | D | Poor — significant quality problems |
| 0-39 | F | Unusable — needs re-recording |

---

## Section F: Compliance Summary

Quick pass/warn/fail checks against common AI data specs.

| Check | Good | Warning | Fail |
|-------|------|---------|------|
| **Sample rate** | ≥ 16 kHz | 8-16 kHz | < 8 kHz |
| **Bit depth** | ≥ 16-bit | 8-bit | — |
| **Channels** | Mono (if required) | Stereo | — |
| **Clipping** | None | < 0.1% | ≥ 0.1% |
| **SNR** | ≥ 20 dB | 15-20 dB | < 15 dB |
| **Silence %** | ≤ 10% | 10-20% | > 20% |
| **Duration** | — | — | (depends on project) |
| **Format** | WAV/FLAC | MP3 ≥256kbps | MP3 <128kbps |

---

## Section G: Visualizations

All returned as base64-encoded PNG images.

| Visualization | Description | Dimensions |
|---------------|-------------|------------|
| **Waveform** | Full audio waveform with silence/speech regions highlighted | 1200 x 300 px |
| **Spectrogram** | Frequency content over time (mel spectrogram) | 1200 x 400 px |
| **Loudness over time** | RMS energy graph showing volume consistency | 1200 x 200 px |
| **Speaker timeline** | Color-coded timeline of who speaks when | 1200 x 150 px |

---

## User Flow

1. **Landing page** — Hero, how it works, supported formats, upload CTA
2. **Upload** — Drag & drop or click, format validation, 1GB limit check
3. **Processing** — Animated progress: "Extracting metadata..." → "Analyzing signal..." → "Detecting language..." → "Counting speakers..." → "Generating report..."
4. **Report** — All sections displayed beautifully, quality score prominent
5. **Actions** — "Analyze another file", "Download PDF" (v2), lead capture CTA

---

## v2 Features (Post-MVP)

| Feature | Description |
|---------|-------------|
| **Spec Checker mode** | User inputs required specs, tool validates compliance |
| **PDF report download** | Export full report as PDF |
| **Batch upload** | Upload up to 10 files at once |
| **API endpoint** | Programmatic access for integrations |
| **Noise type classification** | YAMNet integration |
| **Spectrogram zoom** | Interactive spectrogram |

---

## v3 Features (Future)

| Feature | Description |
|---------|-------------|
| **Batch upload (large)** | 100+ files via ZIP |
| **Comparison mode** | Compare 2 files side by side |
| **Account system** | Save analysis history |
| **API keys** | Enterprise API access |
| **Custom scoring profiles** | Different weights per project type |
| **Webhooks** | Notifications for batch processing |
