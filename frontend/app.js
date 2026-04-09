/* ── Audio Quality Checker — Frontend Logic ────────
   All backend integration intact. New DOM structure.
───────────────────────────────────────────────────── */

const API_BASE = window.location.origin;

// Nav scroll effect
const nav = document.querySelector('.nav');
window.addEventListener('scroll', () => {
    if (window.scrollY > 60) nav.classList.add('scrolled');
    else nav.classList.remove('scrolled');
}, { passive: true });

// DOM
const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');
const retainLabel = document.getElementById('retain-label');
const progressSection = document.getElementById('progress-section');
const progressFilename = document.getElementById('progress-filename');
const progressPercent = document.getElementById('progress-percent');
const progressFill = document.getElementById('progress-fill');
const progressStatus = document.getElementById('progress-status');
const resultsSection = document.getElementById('results-section');

// State
let currentResult = null;
let uploadedFileBlob = null;
let wavesurferInstance = null;
let stageInterval = null;

// ── Toast Notification System ──
const toastContainer = document.getElementById('toast-container');
const TOAST_ICONS = {
    error: '❌',
    success: '✅',
    warning: '⚠️',
    info: 'ℹ️'
};

function showToast(message, type = 'error', title = null, duration = 6000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const defaultTitles = {
        error: 'Error',
        success: 'Success',
        warning: 'Warning',
        info: 'Info'
    };
    const displayTitle = title || defaultTitles[type] || 'Notice';
    
    toast.innerHTML = `
        <span class="toast-icon">${TOAST_ICONS[type] || 'ℹ️'}</span>
        <div class="toast-content">
            <div class="toast-title">${displayTitle}</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" aria-label="Close">&times;</button>
    `;
    
    toastContainer.appendChild(toast);
    
    const close = () => {
        toast.classList.add('toast-hiding');
        setTimeout(() => toast.remove(), 250);
    };
    
    toast.querySelector('.toast-close').addEventListener('click', close);
    
    if (duration > 0) {
        setTimeout(close, duration);
    }
    
    return toast;
}

const STAGES_QUICK = [
    'Extracting file metadata...',
    'Analyzing signal quality...',
    'Checking for clipping and silence...',
    'Calculating signal-to-noise ratio...',
    'Running language detection...',
    'Detecting speech activity...',
    'Computing quality score...',
    'Generating visualizations...',
    'Finalizing report...',
];

const STAGES_DEEP = [
    'Extracting file metadata...',
    'Analyzing signal quality...',
    'Checking for clipping and silence...',
    'Calculating signal-to-noise ratio...',
    'Running language detection...',
    'Detecting speech activity...',
    'Counting speakers (this takes time)...',
    'Analyzing speech quality (MOS)...',
    'Classifying noise types...',
    'Generating transcription preview...',
    'Analyzing reverb and room acoustics...',
    'Detecting emotion and tone...',
    'Computing quality score...',
    'Generating visualizations...',
    'Finalizing report...',
];

const WAIT_MESSAGES = [
    'Still processing — larger files take longer...',
    'Deep analysis in progress...',
    'Running speaker diarization (CPU-intensive)...',
    'Crunching the numbers...',
    'Hang tight — almost there...',
    'Generating detailed visualizations...',
    'Still working — quality takes time...',
];

let stageStart = 0;
let currentAnalysisMode = 'quick';

function startStages(mode = 'quick') {
    currentAnalysisMode = mode;
    const stages = mode === 'deep' ? STAGES_DEEP : STAGES_QUICK;
    let i = 0;
    let waitIdx = 0;
    stageStart = Date.now();
    if (stageInterval) clearInterval(stageInterval);
    stageInterval = setInterval(() => {
        const elapsed = Math.round((Date.now() - stageStart) / 1000);
        const timer = `<span style="color:#888;font-size:0.85em;margin-left:8px">${elapsed}s</span>`;
        if (i < stages.length) {
            progressStatus.innerHTML = `<span class="spinner"></span>${stages[i]}${timer}`;
            i++;
        } else {
            // Cycle through wait messages so it never looks stuck
            const msg = WAIT_MESSAGES[waitIdx % WAIT_MESSAGES.length];
            progressStatus.innerHTML = `<span class="spinner"></span>${msg}${timer}`;
            waitIdx++;
        }
    }, mode === 'deep' ? 4000 : 2000);  // Slower intervals for deep mode
}

function stopStages() {
    if (stageInterval) { clearInterval(stageInterval); stageInterval = null; }
}


// ── Mobile Nav ──────────────────────────────────────

function setupMobileNav() {
    const toggle = document.getElementById('nav-toggle');
    const links = document.getElementById('nav-links');
    if (!toggle || !links) return;

    toggle.addEventListener('click', () => links.classList.toggle('open'));
    links.querySelectorAll('a').forEach(a =>
        a.addEventListener('click', () => links.classList.remove('open'))
    );
}


// ── Upload ──────────────────────────────────────────

function setupUpload() {
    uploadZone.addEventListener('click', () => fileInput.click());

    uploadZone.addEventListener('dragover', e => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });

    uploadZone.addEventListener('dragleave', () =>
        uploadZone.classList.remove('dragover')
    );

    uploadZone.addEventListener('drop', e => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) handleFile(fileInput.files[0]);
    });
}


function handleFile(file) {
    // Validate size
    if (file.size > 1073741824) {
        showToast('File too large. Maximum file size is 1 GB.', 'error', 'File Too Large');
        return;
    }
    uploadedFileBlob = file;

    const retain = document.getElementById('retain-checkbox').checked;
    const analysisMode = document.querySelector('input[name="analysis-mode"]:checked')?.value || 'quick';
    const formData = new FormData();
    formData.append('file', file);
    formData.append('retain', retain.toString());
    formData.append('profile', document.getElementById('profile-select').value);
    formData.append('mode', analysisMode);

    // Show progress
    uploadZone.classList.add('hidden');
    retainLabel.classList.add('hidden');
    document.getElementById('analysis-mode').classList.add('hidden');
    document.getElementById('profile-selector').classList.add('hidden');
    progressSection.classList.remove('hidden');
    progressFilename.textContent = `${file.name} (${fmtSize(file.size)})`;
    progressPercent.textContent = '0%';
    progressFill.style.width = '0%';
    progressStatus.textContent = 'Uploading...';

    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener('progress', e => {
        if (!e.lengthComputable) return;
        const pct = Math.round((e.loaded / e.total) * 100);
        progressPercent.textContent = pct + '%';
        progressFill.style.width = pct + '%';
        if (pct === 100) {
            progressStatus.innerHTML = '<span class="spinner"></span>Analyzing...';
            startStages(analysisMode);
        }
    });

    xhr.addEventListener('load', () => {
        stopStages();
        if (xhr.status === 200) {
            try {
                currentResult = JSON.parse(xhr.responseText);
                showResults(currentResult);
            } catch { showError('Invalid response from server.'); }
        } else {
            try {
                const err = JSON.parse(xhr.responseText);
                showError(err.detail || err.error || 'Analysis failed.');
            } catch { showError(`Server error (${xhr.status}).`); }
        }
    });

    xhr.addEventListener('error', () => showError('Network error. Check your connection.'));
    xhr.addEventListener('timeout', () => showError('Analysis timed out. The file may be too large for CPU processing. This will be much faster on GPU.'));

    xhr.open('POST', `${API_BASE}/api/analyze`);
    xhr.timeout = 600000; // 10 minutes — large files on CPU take time
    xhr.send(formData);
}


// ── Results ─────────────────────────────────────────

function showResults(r) {
    //console.log('[AQC] showResults called, response:', r);
    progressSection.classList.add('hidden');
    resultsSection.classList.remove('hidden');

    const safe = (fn, name) => {
        try {
            fn();
            //console.log(`[AQC] render ${name} OK`);
        } catch(e) {
            //console.error(`[AQC] Render ${name} failed:`, e);
        }
    };

    safe(() => renderScore(r.quality), 'score');
    safe(() => renderFileInfo(r.file_info), 'fileInfo');
    safe(() => renderSignal(r.signal_analysis), 'signal');
    safe(() => renderAI(r.ai_analysis), 'ai');
    safe(() => renderMOS(r.ai_analysis), 'mos');
    safe(() => renderNoise(r.ai_analysis), 'noise');
    safe(() => renderTranscription(r.ai_analysis), 'transcription');
    safe(() => renderReverb(r.ai_analysis), 'reverb');
    safe(() => renderEmotion(r.ai_analysis), 'emotion');
    safe(() => renderBreakdown(r.quality), 'breakdown');
    safe(() => renderCompliance(r.compliance), 'compliance');
    safe(() => renderViz(r.visualizations), 'viz');
    safe(() => renderErrors(r.errors), 'errors');
    safe(() => initWaveform(), 'waveform');

    // Show processing time if available
    const timeEl = document.getElementById('score-time');
    if (timeEl && r.processing_time_seconds) {
        timeEl.textContent = `Analyzed in ${r.processing_time_seconds}s`;
    }

    // Trigger reveal animations for newly visible cards
    setTimeout(() => setupReveal(), 50);
}


// Score

function renderScore(q) {
    if (!q) return;
    const score = q.score ?? 0;
    const grade = q.grade ?? '-';

    // Ring color by score
    let color;
    if (score >= 80) color = '#2e7d32';
    else if (score >= 70) color = '#00897B';
    else if (score >= 60) color = '#e65100';
    else color = '#c62828';

    const ring = document.getElementById('score-ring-fill');
    ring.style.stroke = color;

    const circ = 2 * Math.PI * 52; // r=52
    setTimeout(() => { ring.style.strokeDashoffset = circ - (score / 100) * circ; }, 80);

    animateNum(document.getElementById('score-number'), 0, score, 900);

    const gradeEl = document.getElementById('score-grade');
    gradeEl.textContent = grade;
    gradeEl.style.color = color;

    document.getElementById('score-summary').textContent = q.summary || '';
}

function animateNum(el, from, to, ms) {
    const start = performance.now();
    const step = t => {
        const p = Math.min((t - start) / ms, 1);
        el.textContent = Math.round(from + (to - from) * p);
        if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
}


// File info

function renderFileInfo(m) {
    if (!m) return;
    const items = [
        ['Format', m.format || '-'],
        ['Codec', m.codec || '-'],
        ['Duration', m.duration_formatted || fmtDur(m.duration_seconds)],
        ['Sample Rate', m.sample_rate ? `${m.sample_rate.toLocaleString()} Hz` : '-'],
        ['Bit Depth', m.bit_depth ? `${m.bit_depth}-bit` : '-'],
        ['Bit Rate', m.bit_rate ? `${Math.round(m.bit_rate / 1000)} kbps` : '-'],
        ['Channels', m.channels ? (m.channels === 1 ? 'Mono' : m.channels === 2 ? 'Stereo' : `${m.channels}ch`) : '-'],
        ['File Size', m.file_size_formatted || fmtSize(m.file_size_bytes)],
    ];
    document.getElementById('file-info-grid').innerHTML = items.map(toDataItem).join('');
}


// Signal

function renderSignal(s) {
    if (!s) return;
    const items = [];

    // Signal levels are top-level fields, not nested
    items.push(
        ['Peak Level', s.peak_amplitude_db != null ? `${s.peak_amplitude_db.toFixed(1)} dB` : '-'],
        ['RMS Level', s.rms_level_db != null ? `${s.rms_level_db.toFixed(1)} dB` : '-'],
        ['Dynamic Range', s.dynamic_range_db != null ? `${s.dynamic_range_db.toFixed(1)} dB` : '-'],
    );

    // SNR is a top-level field
    if (s.snr_db != null) {
        items.push(['SNR', `${s.snr_db.toFixed(1)} dB`]);
    }

    // Noise floor
    if (s.noise_floor_db != null) {
        items.push(['Noise Floor', `${s.noise_floor_db.toFixed(1)} dB`]);
    }

    if (s.clipping) {
        const c = s.clipping;
        items.push(
            ['Clipping', c.detected ? `Detected (${c.percentage.toFixed(2)}%)` : 'None', c.detected ? 'bad' : 'good'],
            ['Clipped Samples', c.clipped_samples != null ? c.clipped_samples.toLocaleString() : '-'],
        );
    }

    if (s.silence) {
        items.push(
            ['Silence', `${(s.silence.percentage ?? 0).toFixed(1)}%`],
            ['Longest Silent', s.silence.longest_silence_seconds != null ? `${s.silence.longest_silence_seconds.toFixed(1)}s` : '-'],
        );
    }

    if (s.dc_offset != null) {
        items.push(['DC Offset', s.dc_offset.toFixed(4)]);
    }

    document.getElementById('signal-grid').innerHTML = items.map(i => toDataItem(i)).join('');
}


// AI analysis

function renderAI(a) {
    if (!a) return;
    const items = [];

    if (a.language) {
        const l = a.language;
        const langDisplay = l.name || l.detected || '-';
        items.push(
            ['Language', langDisplay],
            ['Confidence', l.confidence != null ? `${l.confidence.toFixed(0)}%` : '-'],
        );
        if (l.alternatives && l.alternatives.length > 0) {
            const alt = l.alternatives.slice(0, 2).map(a => a.name || a.language).join(', ');
            items.push(['Alternatives', alt || '-']);
        }
    }

    if (a.speech_activity) {
        const sa = a.speech_activity;
        items.push(
            ['Speech', `${(sa.speech_percentage ?? 0).toFixed(1)}%`],
            ['Regions', sa.speech_regions ? sa.speech_regions.length : '-'],
            ['Longest Speech', sa.longest_speech_seconds != null ? `${sa.longest_speech_seconds.toFixed(1)}s` : '-'],
        );
    }

    if (a.speakers) {
        items.push(['Speakers', a.speakers.count != null ? a.speakers.count : '-']);
        if (a.speakers.turn_count) {
            items.push(['Turns', a.speakers.turn_count]);
        }
    }

    document.getElementById('ai-grid').innerHTML = items.map(toDataItem).join('');
}


// MOS Speech Quality

function renderMOS(a) {
    const card = document.getElementById('speech-quality-card');
    if (!a || !a.speech_quality) {
        if (card) card.style.display = 'none';
        return;
    }
    if (card) card.style.display = '';

    const sq = a.speech_quality;
    const mos = sq.mos;

    // Color based on MOS
    let color = '#E74C3C'; // red
    if (mos >= 4.0) color = '#27ae60';
    else if (mos >= 3.5) color = '#00897B';
    else if (mos >= 3.0) color = '#F5A623';
    else if (mos >= 2.5) color = '#e67e22';

    const subs = [
        ['Noisiness', sq.noisiness, 'How clean the signal is (5 = no noise)'],
        ['Coloration', sq.coloration, 'Spectral naturalness (5 = natural)'],
        ['Discontinuity', sq.discontinuity, 'Temporal smoothness (5 = smooth)'],
        ['Loudness', sq.loudness, 'Appropriate level (5 = good)'],
    ];

    function subColor(v) {
        if (v >= 4.0) return '#27ae60';
        if (v >= 3.0) return '#00897B';
        if (v >= 2.5) return '#F5A623';
        return '#E74C3C';
    }

    const barsHtml = subs.map(([label, val, tip]) => {
        const pct = Math.max(0, Math.min(100, ((val - 1) / 4) * 100));
        return `<div class="mos-sub-row" title="${tip}">
            <span class="mos-sub-label">${label}</span>
            <div class="mos-sub-bar"><div class="mos-sub-fill" style="width:${pct}%;background:${subColor(val)}"></div></div>
            <span class="mos-sub-val" style="color:${subColor(val)}">${val.toFixed(1)}</span>
        </div>`;
    }).join('');

    document.getElementById('mos-display').innerHTML = `
        <div>
            <div class="mos-score-big" style="color:${color}">${mos.toFixed(1)}</div>
            <div class="mos-scale" style="text-align:center">out of 5.0</div>
        </div>
        <div style="flex:1">
            <div class="mos-rating" style="color:${color}">${sq.mos_rating} Speech Quality</div>
            <div class="mos-scale" style="margin-bottom:10px">NISQA MOS (Industry Standard)</div>
            ${barsHtml}
        </div>
    `;
}


// Noise Classification

function renderNoise(a) {
    const card = document.getElementById('noise-card');
    if (!a || !a.noise_classification) {
        card.classList.add('hidden');
        return;
    }
    card.classList.remove('hidden');
    const nc = a.noise_classification;
    const display = document.getElementById('noise-display');

    // Primary noise type
    let html = `<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
        <span style="font-size:2rem">${nc.noise_types[0]?.icon || ''}</span>
        <div>
            <div style="font-weight:600;font-size:1.1rem">${nc.primary_label}</div>
            <div style="color:var(--text-3);font-size:0.85rem">${nc.noise_types[0]?.description || ''}</div>
        </div>
    </div>`;

    // All detected noise types
    if (nc.noise_types.length > 0) {
        html += '<div style="margin-bottom:12px">';
        nc.noise_types.forEach(nt => {
            const barWidth = Math.max(nt.confidence, 5);
            const barColor = nt.confidence >= 70 ? 'var(--accent)' : nt.confidence >= 40 ? '#F5A623' : 'var(--text-3)';
            html += `<div style="margin-bottom:8px">
                <div style="display:flex;justify-content:space-between;font-size:0.85rem;margin-bottom:3px">
                    <span>${nt.icon} ${nt.label}</span>
                    <span style="color:var(--text-3)">${nt.confidence}%</span>
                </div>
                <div style="height:6px;background:var(--bg-2);border-radius:3px;overflow:hidden">
                    <div style="width:${barWidth}%;height:100%;background:${barColor};border-radius:3px;transition:width 0.5s"></div>
                </div>
            </div>`;
        });
        html += '</div>';
    }

    // Spectral profile
    const sp = nc.spectral_profile;
    if (sp && Object.keys(sp).length > 0) {
        html += `<div style="font-size:0.85rem;color:var(--text-2);margin-top:12px">
            <div style="font-weight:600;margin-bottom:6px">Frequency Band Energy</div>`;
        const bandLabels = {
            sub_bass: 'Sub Bass (0-60 Hz)',
            bass: 'Bass (60-250 Hz)',
            low_mid: 'Low Mid (250-500 Hz)',
            mid: 'Mid (500-2k Hz)',
            upper_mid: 'Upper Mid (2k-4k Hz)',
            high: 'High (4k-8k Hz)',
            ultra_high: 'Ultra High (8k+ Hz)',
        };
        const maxVal = Math.max(...Object.values(sp), 1);
        for (const [key, val] of Object.entries(sp)) {
            const pct = (val / maxVal) * 100;
            html += `<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
                <span style="width:150px;flex-shrink:0;font-size:0.8rem">${bandLabels[key] || key}</span>
                <div style="flex:1;height:5px;background:var(--bg-2);border-radius:3px;overflow:hidden">
                    <div style="width:${pct}%;height:100%;background:var(--accent);border-radius:3px"></div>
                </div>
                <span style="width:40px;text-align:right;font-size:0.8rem">${val}%</span>
            </div>`;
        }
        html += '</div>';
    }

    // Noise floor
    html += `<div style="margin-top:10px;font-size:0.85rem;color:var(--text-3)">Noise Floor: ${nc.noise_floor_db} dB</div>`;

    display.innerHTML = html;
}

// Transcription Preview

function renderTranscription(a) {
    const card = document.getElementById('transcription-card');
    if (!a || !a.transcription || !a.transcription.text) {
        card.classList.add('hidden');
        return;
    }
    card.classList.remove('hidden');
    const t = a.transcription;
    const display = document.getElementById('transcription-display');

    let html = `<div style="margin-bottom:12px;display:flex;gap:16px;flex-wrap:wrap;font-size:0.85rem;color:var(--text-3)">
        <span>First ${t.duration_transcribed}s</span>
        <span>${t.word_count} words</span>
        <span>Language: ${t.language_used}</span>
    </div>`;

    // Full text
    html += `<div style="background:var(--bg-2);padding:16px;border-radius:10px;font-size:0.95rem;line-height:1.7;max-height:300px;overflow-y:auto;white-space:pre-wrap">${escHtml(t.text)}</div>`;

    // Segments timeline
    if (t.segments && t.segments.length > 0) {
        html += `<details style="margin-top:12px"><summary style="cursor:pointer;font-size:0.85rem;color:var(--text-2);font-weight:500">Timestamps (${t.segments.length} segments)</summary>
        <div style="margin-top:8px;max-height:250px;overflow-y:auto">`;
        t.segments.forEach(seg => {
            const startMin = Math.floor(seg.start / 60);
            const startSec = (seg.start % 60).toFixed(1);
            html += `<div style="display:flex;gap:10px;padding:4px 0;border-bottom:1px solid var(--border);font-size:0.85rem">
                <span style="color:var(--accent);font-family:monospace;min-width:60px">${startMin}:${startSec.padStart(4,'0')}</span>
                <span>${escHtml(seg.text)}</span>
            </div>`;
        });
        html += '</div></details>';
    }

    display.innerHTML = html;
}

// Interactive Waveform (Wavesurfer.js)

function initWaveform() {
    const card = document.getElementById('waveform-card');
    if (!uploadedFileBlob || typeof WaveSurfer === 'undefined') {
        card.classList.add('hidden');
        return;
    }
    card.classList.remove('hidden');

    // Destroy previous instance
    if (wavesurferInstance) {
        try { wavesurferInstance.destroy(); } catch (e) {}
        wavesurferInstance = null;
    }

    const container = document.getElementById('waveform-container');
    container.innerHTML = '';

    const blobUrl = URL.createObjectURL(uploadedFileBlob);

    // Check file duration from analysis result - use fallback for large files
    const duration = currentResult && currentResult.file_info ? currentResult.file_info.duration_seconds : 0;
    const MAX_WAVEFORM_DURATION = 300; // 5 minutes

    if (duration > MAX_WAVEFORM_DURATION) {
        // Use HTML5 audio player for large files
        container.classList.add('hidden');
        document.getElementById('waveform-controls').classList.add('hidden');
        const fallback = document.getElementById('audio-fallback');
        fallback.classList.remove('hidden');
        const audioEl = document.getElementById('audio-fallback-player');
        audioEl.src = blobUrl;
        return;
    }

    // WaveSurfer for short files
    container.classList.remove('hidden');
    document.getElementById('waveform-controls').classList.remove('hidden');
    document.getElementById('audio-fallback').classList.add('hidden');

    // Detect dark mode
    const isDark = getComputedStyle(document.documentElement).getPropertyValue('--bg-1').trim().startsWith('#1');

    wavesurferInstance = WaveSurfer.create({
        container: '#waveform-container',
        waveColor: isDark ? '#4a9d8f' : '#00897B',
        progressColor: isDark ? '#80cbc4' : '#26a69a',
        cursorColor: isDark ? '#fff' : '#333',
        barWidth: 2,
        barGap: 1,
        barRadius: 2,
        height: 120,
        responsive: true,
        normalize: true,
        backend: 'WebAudio',
    });

    wavesurferInstance.load(blobUrl);

    const playBtn = document.getElementById('waveform-play');
    const timeEl = document.getElementById('waveform-time');
    const zoomSlider = document.getElementById('waveform-zoom');

    wavesurferInstance.on('play', () => { playBtn.textContent = '\u23F8 Pause'; });
    wavesurferInstance.on('pause', () => { playBtn.textContent = '\u25B6 Play'; });
    wavesurferInstance.on('finish', () => { playBtn.textContent = '\u25B6 Play'; });

    wavesurferInstance.on('timeupdate', (currentTime) => {
        const dur = wavesurferInstance.getDuration();
        timeEl.textContent = `${fmtTime(currentTime)} / ${fmtTime(dur)}`;
    });

    wavesurferInstance.on('ready', () => {
        const dur = wavesurferInstance.getDuration();
        timeEl.textContent = `0:00 / ${fmtTime(dur)}`;
    });

    playBtn.onclick = () => wavesurferInstance.playPause();

    zoomSlider.oninput = () => {
        const val = Number(zoomSlider.value);
        wavesurferInstance.zoom(val);
    };
}

function fmtTime(sec) {
    if (!sec || isNaN(sec)) return '0:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

// Reverb & Echo

function renderReverb(a) {
    const card = document.getElementById('reverb-card');
    if (!a || !a.reverb) {
        card.classList.add('hidden');
        return;
    }
    card.classList.remove('hidden');
    const rv = a.reverb;
    const display = document.getElementById('reverb-display');

    const envIcons = {
        'Recording booth / Anechoic': '🎙️',
        'Treated room / Small studio': '🏠',
        'Office / Small room': '🏢',
        'Medium room / Conference room': '🏛️',
        'Untreated room with reflections': '📦',
        'Large room / Hall': '🏟️',
        'Very large space / Cathedral': '⛪',
    };
    const icon = envIcons[rv.environment] || '🔊';

    const scoreColor = rv.reverb_score < 20 ? '#27ae60' : rv.reverb_score < 50 ? '#F5A623' : '#E74C3C';

    let html = `<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
        <span style="font-size:2rem">${icon}</span>
        <div>
            <div style="font-weight:600;font-size:1.1rem">${rv.environment}</div>
            <div style="color:var(--text-3);font-size:0.85rem">Reverb score: <span style="color:${scoreColor};font-weight:600">${rv.reverb_score}</span>/100</div>
        </div>
    </div>`;

    // Metrics grid
    html += '<div class="data-grid">';

    if (rv.rt60_seconds != null) {
        const rt60Label = {'dry':'Dry','moderate':'Moderate','reverberant':'Reverberant','very_reverberant':'Very Reverberant'}[rv.rt60_rating] || rv.rt60_rating;
        html += `<div class="data-item"><span class="data-label">RT60</span><span class="data-value">${rv.rt60_seconds}s</span><span class="data-sub">${rt60Label}</span></div>`;
    }

    if (rv.c50_db != null) {
        html += `<div class="data-item"><span class="data-label">Clarity (C50)</span><span class="data-value">${rv.c50_db} dB</span><span class="data-sub">${rv.c50_db > 5 ? 'Clear' : rv.c50_db > -2 ? 'Moderate' : 'Muddy'}</span></div>`;
    }

    html += `<div class="data-item"><span class="data-label">Echo</span><span class="data-value">${rv.echo_detected ? '\u26A0\uFE0F Detected' : '\u2705 None'}</span>`;
    if (rv.echo_detected && rv.echo_delay_ms) {
        html += `<span class="data-sub">${rv.echo_delay_ms}ms delay, ${rv.echo_strength_db}dB</span>`;
    }
    html += '</div></div>';

    display.innerHTML = html;
}

// Emotion / Tone

function renderEmotion(a) {
    const card = document.getElementById('emotion-card');
    if (!a || !a.emotion) {
        card.classList.add('hidden');
        return;
    }
    card.classList.remove('hidden');
    const em = a.emotion;
    const display = document.getElementById('emotion-display');

    const toneIcons = {
        'calm': '\ud83d\ude0c', 'neutral': '\ud83d\ude10', 'warm': '\u2600\ufe0f',
        'energetic': '\u26a1', 'tense': '\ud83d\ude23', 'intense': '\ud83d\udd25',
        'flat': '\u27a1\ufe0f', 'dynamic': '\ud83c\udfb5', 'non_speech': '\ud83d\udd07',
    };
    const icon = toneIcons[em.primary_tone] || '\ud83c\udfa4';
    const toneLabel = em.primary_tone.replace('_', ' ').replace(/^\w/, c => c.toUpperCase());

    // Valence-arousal visualization
    const vx = ((em.valence + 1) / 2) * 100; // 0-100
    const vy = (1 - em.arousal) * 100; // inverted (top = high arousal)

    let html = `<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
        <span style="font-size:2rem">${icon}</span>
        <div>
            <div style="font-weight:600;font-size:1.1rem">${toneLabel}</div>
            <div style="color:var(--text-3);font-size:0.85rem">${em.description}</div>
            <div style="color:var(--text-3);font-size:0.8rem;margin-top:2px">Confidence: ${em.confidence}%</div>
        </div>
    </div>`;

    // Valence-Arousal space (mini visualization)
    html += `<div style="position:relative;width:160px;height:160px;background:var(--bg-2);border-radius:10px;margin:0 auto 12px">
        <div style="position:absolute;top:4px;left:50%;transform:translateX(-50%);font-size:0.7rem;color:var(--text-3)">Excited</div>
        <div style="position:absolute;bottom:4px;left:50%;transform:translateX(-50%);font-size:0.7rem;color:var(--text-3)">Calm</div>
        <div style="position:absolute;left:4px;top:50%;transform:translateY(-50%);font-size:0.7rem;color:var(--text-3)">-</div>
        <div style="position:absolute;right:4px;top:50%;transform:translateY(-50%);font-size:0.7rem;color:var(--text-3)">+</div>
        <div style="position:absolute;left:50%;top:0;bottom:0;width:1px;background:var(--border)"></div>
        <div style="position:absolute;top:50%;left:0;right:0;height:1px;background:var(--border)"></div>
        <div style="position:absolute;left:${vx}%;top:${vy}%;transform:translate(-50%,-50%);width:14px;height:14px;background:var(--accent);border-radius:50%;border:2px solid white"></div>
    </div>`;

    html += `<div class="data-grid">
        <div class="data-item"><span class="data-label">Valence</span><span class="data-value">${em.valence > 0 ? '+' : ''}${em.valence}</span><span class="data-sub">${em.valence > 0.1 ? 'Positive' : em.valence < -0.1 ? 'Negative' : 'Neutral'}</span></div>
        <div class="data-item"><span class="data-label">Arousal</span><span class="data-value">${em.arousal}</span><span class="data-sub">${em.arousal > 0.5 ? 'High energy' : em.arousal > 0.25 ? 'Moderate' : 'Low energy'}</span></div>
    </div>`;

    display.innerHTML = html;
}

function escHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// Breakdown

function renderBreakdown(q) {
    const list = document.getElementById('breakdown-list');
    const bd = q?.breakdown || [];
    if (!bd.length) { list.innerHTML = '<p style="color:var(--text-3)">No breakdown available</p>'; return; }

    const tips = {
        'SNR (Signal-to-Noise)': 'How loud the signal is vs. background noise',
        'Clipping': 'Whether audio is distorted from being too loud',
        'Silence Ratio': 'How much of the recording is silent',
        'Sample Rate': 'Audio samples per second (higher = better)',
        'Bit Depth': 'Resolution of each sample (higher = more detail)',
        'Dynamic Range': 'Spread between quietest and loudest parts',
        'DC Offset': 'Whether the signal is centered correctly',
        'Speech Clarity': 'How clear and intelligible speech is',
        'Format Quality': 'Whether the format is lossless or high-quality',
    };

    list.innerHTML = bd.map(b => {
        const s = b.score ?? 0;
        const level = s >= 80 ? 'excellent' : s >= 60 ? 'good' : s >= 40 ? 'fair' : 'poor';
        const tip = tips[b.component] || b.detail || '';
        return `
            <div class="breakdown-row" title="${tip}">
                <span class="breakdown-label">${b.component} (${(b.weight * 100).toFixed(0)}%)</span>
                <div class="breakdown-track"><div class="breakdown-fill ${level}" style="width:${s}%"></div></div>
                <span class="breakdown-val">${s.toFixed(0)}</span>
            </div>`;
    }).join('');
}


// Compliance

function renderCompliance(c) {
    const card = document.getElementById('compliance-card');
    const list = document.getElementById('compliance-list');
    const checks = c?.checks || [];
    if (!checks.length) { card.classList.add('hidden'); return; }
    card.classList.remove('hidden');

    list.innerHTML = checks.map(ch => `
        <div class="compliance-row">
            <span class="compliance-dot ${ch.status}"></span>
            <div class="compliance-info">
                <span class="compliance-name">${ch.metric || '-'}</span>
                <span class="compliance-detail">${ch.message || ''}</span>
                <span class="compliance-detail">${ch.value || ''} ${ch.threshold ? '(threshold: ' + ch.threshold + ')' : ''}</span>
            </div>
        </div>`).join('');
}


// Visualizations

function renderViz(v) {
    const card = document.getElementById('viz-card');
    const container = document.getElementById('viz-container');
    if (!v) { card.classList.add('hidden'); return; }

    const items = [
        ['waveform', 'Waveform'],
        ['spectrogram', 'Mel Spectrogram'],
        ['loudness', 'Loudness Over Time'],
        ['speakers', 'Speaker Timeline'],
    ].filter(([k]) => v[k]);

    if (!items.length) { card.classList.add('hidden'); return; }
    card.classList.remove('hidden');

    container.innerHTML = items.map(([k, label]) => `
        <div class="viz-item">
            <img src="data:image/png;base64,${v[k]}" alt="${label}" loading="lazy">
            <div class="viz-caption">${label}</div>
        </div>`).join('');
}


// Errors / warnings

function renderErrors(errs) {
    const card = document.getElementById('errors-card');
    const list = document.getElementById('errors-list');
    if (!errs || !errs.length) { card.classList.add('hidden'); return; }
    card.classList.remove('hidden');
    list.innerHTML = errs.map(e => `<div class="error-row">${e}</div>`).join('');
}


// ── Buttons ─────────────────────────────────────────

function setupButtons() {
    document.getElementById('btn-new-analysis').addEventListener('click', reset);
    document.getElementById('btn-download-json').addEventListener('click', downloadJson);
    document.getElementById('btn-download-pdf').addEventListener('click', downloadPdf);
}

function reset() {
    resultsSection.classList.add('hidden');
    progressSection.classList.add('hidden');
    uploadZone.classList.remove('hidden');
    retainLabel.classList.remove('hidden');
    document.getElementById('mode-toggle').classList.remove('hidden');
    document.getElementById('analysis-mode').classList.remove('hidden');
    document.getElementById('profile-selector').classList.remove('hidden');
    fileInput.value = '';
    currentResult = null;
    uploadedFileBlob = null;

    // Destroy wavesurfer
    if (wavesurferInstance) {
        try { wavesurferInstance.destroy(); } catch (e) {}
        wavesurferInstance = null;
    }

    // Reset ring
    const ring = document.getElementById('score-ring-fill');
    const circ = 2 * Math.PI * 52;
    ring.style.strokeDashoffset = circ;
    ring.style.stroke = 'var(--accent)';
}

function downloadJson() {
    if (!currentResult) return;

    const clean = JSON.parse(JSON.stringify(currentResult));
    if (clean.visualizations) {
        Object.keys(clean.visualizations).forEach(k => {
            if (clean.visualizations[k]) clean.visualizations[k] = '[base64 omitted]';
        });
    }

    const blob = new Blob([JSON.stringify(clean, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audio-quality-report-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function downloadPdf() {
    if (!currentResult) return;
    const r = currentResult;

    // Build a standalone HTML report
    const fi = r.file_info || {};
    const sig = r.signal_analysis || {};
    const ai = r.ai_analysis || {};
    const q = r.quality || {};
    const comp = r.compliance || {};
    const sq = ai.speech_quality || null;
    const viz = r.visualizations || {};

    const scoreColor = q.score >= 80 ? '#27ae60' : q.score >= 60 ? '#F5A623' : '#E74C3C';
    const mosHtml = sq ? `
        <div class="section">
            <h2>Speech Quality (NISQA MOS)</h2>
            <div style="display:flex;align-items:center;gap:20px;margin-bottom:12px">
                <div style="font-size:2.5rem;font-weight:700;color:${sq.mos >= 3.5 ? '#27ae60' : sq.mos >= 2.5 ? '#F5A623' : '#E74C3C'}">${sq.mos.toFixed(1)}<span style="font-size:1rem;color:#888">/5.0</span></div>
                <div><strong>${sq.mos_rating}</strong><br><span style="color:#888;font-size:0.85rem">Industry-standard MOS score</span></div>
            </div>
            <table><tr><th>Metric</th><th>Score</th></tr>
                <tr><td>Noisiness</td><td>${sq.noisiness.toFixed(1)}/5.0</td></tr>
                <tr><td>Coloration</td><td>${sq.coloration.toFixed(1)}/5.0</td></tr>
                <tr><td>Discontinuity</td><td>${sq.discontinuity.toFixed(1)}/5.0</td></tr>
                <tr><td>Loudness</td><td>${sq.loudness.toFixed(1)}/5.0</td></tr>
            </table>
        </div>` : '';

    const breakdownHtml = (q.breakdown || []).map(b =>
        `<tr><td>${b.component}</td><td>${b.detail}</td><td style="color:${b.score >= 70 ? '#27ae60' : b.score >= 40 ? '#F5A623' : '#E74C3C'}">${b.score}/100</td><td>${b.weight * 100}%</td></tr>`
    ).join('');

    const compHtml = (comp.checks || []).map(c => {
        const badgeClass = c.status === 'pass' ? 'badge-pass' : c.status === 'warn' ? 'badge-warn' : 'badge-fail';
        const badgeText = c.status === 'pass' ? 'PASS' : c.status === 'warn' ? 'WARN' : 'FAIL';
        return `<tr><td>${c.metric}</td><td>${c.value}</td><td>${c.threshold}</td><td><span class="badge ${badgeClass}">${badgeText}</span> ${c.message}</td></tr>`;
    }).join('');

    const vizHtml = ['waveform','spectrogram','loudness','speakers'].map(k =>
        viz[k] ? `<div><img src="data:image/png;base64,${viz[k]}" class="viz-img" alt="${k}"></div>` : ''
    ).join('');

    const html = `<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>Audio Quality Report - ${fi.filename || 'Unknown'}</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root { --accent: #00897B; --accent-light: #e0f2f1; --green: #10b981; --orange: #f59e0b; --red: #ef4444; }
  body { font-family: 'Inter', -apple-system, system-ui, sans-serif; max-width: 900px; margin: 0 auto; padding: 32px 24px; color: #1a1a1a; font-size: 14px; line-height: 1.6; background: #fff; }
  h1 { font-family: 'Space Grotesk', sans-serif; color: var(--accent); font-size: 1.75rem; font-weight: 700; margin-bottom: 4px; border: none; }
  .subtitle { color: #666; font-size: 0.85rem; margin-bottom: 32px; }
  h2 { font-family: 'Space Grotesk', sans-serif; color: #222; margin-top: 28px; margin-bottom: 12px; font-size: 1.1rem; font-weight: 600; padding-left: 12px; border-left: 3px solid var(--accent); }
  .section { margin-bottom: 24px; page-break-inside: avoid; }
  table { width: 100%; border-collapse: collapse; margin: 8px 0; }
  th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; font-size: 0.9rem; }
  th { background: #f8f9fa; font-weight: 600; color: #444; }
  tr:hover td { background: #fafafa; }
  .score-box { display: flex; align-items: center; gap: 20px; padding: 20px; background: linear-gradient(135deg, #f0fdf9 0%, #e0f7f4 100%); border-radius: 12px; margin: 12px 0; }
  .score-num { font-family: 'Space Grotesk', sans-serif; font-size: 3.5rem; font-weight: 700; line-height: 1; }
  .score-grade { font-size: 1.5rem; font-weight: 600; }
  .score-summary { color: #555; font-size: 0.9rem; margin-top: 4px; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
  .badge-pass { background: #d1fae5; color: #065f46; }
  .badge-warn { background: #fef3c7; color: #92400e; }
  .badge-fail { background: #fee2e2; color: #991b1b; }
  .meta { color: #888; font-size: 0.8rem; }
  .viz-img { width: 100%; border-radius: 8px; margin: 8px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  hr { border: none; border-top: 1px solid #eee; margin: 32px 0 16px; }
  .footer { text-align: center; color: #999; font-size: 0.8rem; }
  .footer a { color: var(--accent); text-decoration: none; }
  @media print { body { padding: 0; } .no-print { display: none; } }
</style></head><body>
<h1>Audio Quality Report</h1>
<p class="subtitle">Generated on ${new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })} at ${new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</p>

<div class="section">
  <h2>File Information</h2>
  <table><tr><th>Property</th><th>Value</th></tr>
    <tr><td>Filename</td><td>${fi.filename || '-'}</td></tr>
    <tr><td>Duration</td><td>${fi.duration_formatted || '-'}</td></tr>
    <tr><td>Format</td><td>${fi.format || '-'} / ${fi.codec || '-'}</td></tr>
    <tr><td>Sample Rate</td><td>${fi.sample_rate ? fi.sample_rate.toLocaleString() + ' Hz' : '-'}</td></tr>
    <tr><td>Bit Depth</td><td>${fi.bit_depth ? fi.bit_depth + '-bit' : 'N/A'}</td></tr>
    <tr><td>Channels</td><td>${fi.channel_layout || fi.channels || '-'}</td></tr>
    <tr><td>File Size</td><td>${fi.file_size_formatted || '-'}</td></tr>
  </table>
</div>

<div class="section">
  <h2>Quality Score</h2>
  <div class="score-box">
    <div class="score-num" style="color:${scoreColor}">${q.score || 0}</div>
    <div>
      <div class="score-grade" style="color:${scoreColor}">${q.grade || '-'}</div>
      <div class="score-summary">${q.summary || ''}</div>
    </div>
  </div>
</div>

${mosHtml}

<div class="section">
  <h2>Signal Analysis</h2>
  <table><tr><th>Metric</th><th>Value</th></tr>
    <tr><td>Peak Amplitude</td><td>${sig.peak_amplitude_db != null ? sig.peak_amplitude_db.toFixed(1) + ' dB' : '-'}</td></tr>
    <tr><td>RMS Level</td><td>${sig.rms_level_db != null ? sig.rms_level_db.toFixed(1) + ' dB' : '-'}</td></tr>
    <tr><td>SNR</td><td>${sig.snr_db != null ? sig.snr_db.toFixed(1) + ' dB' : '-'}</td></tr>
    <tr><td>Dynamic Range</td><td>${sig.dynamic_range_db != null ? sig.dynamic_range_db.toFixed(1) + ' dB' : '-'}</td></tr>
    <tr><td>DC Offset</td><td>${sig.dc_offset != null ? sig.dc_offset.toFixed(6) : '-'}</td></tr>
    <tr><td>Clipping</td><td>${sig.clipping ? sig.clipping.percentage.toFixed(4) + '%' : 'None'}</td></tr>
    <tr><td>Silence</td><td>${sig.silence ? sig.silence.percentage.toFixed(1) + '%' : '-'}</td></tr>
  </table>
</div>

<div class="section">
  <h2>AI Analysis</h2>
  <table><tr><th>Metric</th><th>Value</th></tr>
    ${ai.language ? `<tr><td>Language</td><td>${ai.language.name} (${ai.language.confidence}%)</td></tr>` : ''}
    ${ai.speech_activity ? `<tr><td>Speech</td><td>${ai.speech_activity.speech_percentage.toFixed(1)}%</td></tr>` : ''}
    ${ai.speakers ? `<tr><td>Speakers</td><td>${ai.speakers.count}</td></tr>` : ''}
  </table>
</div>

${breakdownHtml ? `<div class="section"><h2>Quality Breakdown</h2><table><tr><th>Component</th><th>Detail</th><th>Score</th><th>Weight</th></tr>${breakdownHtml}</table></div>` : ''}

${compHtml ? `<div class="section"><h2>Compliance</h2><table><tr><th>Check</th><th>Value</th><th>Threshold</th><th>Result</th></tr>${compHtml}</table></div>` : ''}

${vizHtml ? `<div class="section"><h2>Visualizations</h2>${vizHtml}</div>` : ''}

<hr>
<p class="footer">Generated by <a href="https://usergy.ai">UsergyAI Audio Quality Checker</a></p>
</body></html>`;

    // Auto-download as HTML file
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Audio-Report-${(fi.filename || 'Unknown').replace(/\.[^.]+$/, '')}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}


// ── Helpers ─────────────────────────────────────────

function showError(msg) {
    stopStages();
    progressSection.classList.add('hidden');
    uploadZone.classList.remove('hidden');
    retainLabel.classList.remove('hidden');
    document.getElementById('analysis-mode').classList.remove('hidden');
    document.getElementById('profile-selector').classList.remove('hidden');
    showToast(msg, 'error', 'Analysis Failed', 8000);
}

function toDataItem([label, value, cls]) {
    const c = cls ? ` ${cls}` : '';
    return `<div class="data-item"><span class="data-label">${label}</span><span class="data-value${c}">${value}</span></div>`;
}

function fmtDur(secs) {
    if (secs == null) return '-';
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function fmtSize(bytes) {
    if (bytes == null) return '-';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + ' MB';
    return (bytes / 1073741824).toFixed(2) + ' GB';
}


// ── Scroll Reveal ───────────────────────────────────

function setupReveal() {
    const reveals = document.querySelectorAll('.reveal');
    if (!reveals.length) return;

    // If IntersectionObserver not available, just show everything
    if (!('IntersectionObserver' in window)) {
        reveals.forEach(el => el.classList.add('in'));
        return;
    }

    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, i) => {
            if (entry.isIntersecting) {
                // Stagger the reveal slightly
                setTimeout(() => entry.target.classList.add('in'), i * 80);
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    reveals.forEach(el => observer.observe(el));
}


// ── Init ────────────────────────────────────────────

const PROFILE_DESCRIPTIONS = {
    'default': 'Common requirements for AI training data',
    'defined_ai': 'High-quality AI data platform requirements (strict)',
    'appen': 'Typical crowd-sourced speech collection specs',
    'common_voice': 'Open source speech dataset standards',
    'telephony': 'Telephony-grade audio (8kHz, low bandwidth)',
    'broadcast': 'High-quality broadcast audio standards',
};

document.addEventListener('DOMContentLoaded', () => {
    setupMobileNav();
    setupUpload();
    setupButtons();
    setupReveal();
    setupModeToggle();
    setupBatch();
    setupCompare();
    setupAnalysisMode();

    // Profile selector
    const sel = document.getElementById('profile-select');
    const desc = document.getElementById('profile-desc');
    if (sel && desc) {
        sel.addEventListener('change', () => {
            desc.textContent = PROFILE_DESCRIPTIONS[sel.value] || '';
        });
    }
});

function setupAnalysisMode() {
    // Restore saved preference
    const saved = localStorage.getItem('analysisMode');
    if (saved) {
        const radio = document.querySelector(`input[name="analysis-mode"][value="${saved}"]`);
        if (radio) radio.checked = true;
    }
    
    // Save preference on change
    document.querySelectorAll('input[name="analysis-mode"]').forEach(radio => {
        radio.addEventListener('change', () => {
            localStorage.setItem('analysisMode', radio.value);
        });
    });
}


// ── Mode Toggle ────────────────────────────────────────

let currentMode = 'single';

function setupModeToggle() {
    const btns = document.querySelectorAll('.mode-btn');
    btns.forEach(btn => {
        btn.addEventListener('click', () => {
            btns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentMode = btn.dataset.mode;

            const singleZone = document.getElementById('upload-zone');
            const batchZone = document.getElementById('batch-upload-zone');
            const batchList = document.getElementById('batch-file-list');
            const compareZone = document.getElementById('compare-zone');

            singleZone.classList.add('hidden');
            batchZone.classList.add('hidden');
            batchList.classList.add('hidden');
            compareZone.classList.add('hidden');

            if (currentMode === 'single') {
                singleZone.classList.remove('hidden');
            } else if (currentMode === 'batch') {
                batchZone.classList.remove('hidden');
            } else if (currentMode === 'compare') {
                compareZone.classList.remove('hidden');
            }
        });
    });
}


// ── Batch Upload ──────────────────────────────────────

let batchFiles = [];
let batchResult = null;

function setupBatch() {
    const batchZone = document.getElementById('batch-upload-zone');
    const batchInput = document.getElementById('batch-file-input');
    const batchBrowse = document.getElementById('batch-browse');

    batchZone.addEventListener('click', () => batchInput.click());

    batchZone.addEventListener('dragover', e => {
        e.preventDefault();
        batchZone.classList.add('dragover');
    });
    batchZone.addEventListener('dragleave', () => batchZone.classList.remove('dragover'));
    batchZone.addEventListener('drop', e => {
        e.preventDefault();
        batchZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) handleBatchFiles(e.dataTransfer.files);
    });

    batchInput.addEventListener('change', () => {
        if (batchInput.files.length) handleBatchFiles(batchInput.files);
    });

    document.getElementById('btn-batch-new').addEventListener('click', resetBatch);
    document.getElementById('btn-batch-csv').addEventListener('click', downloadBatchCsv);
}

function handleBatchFiles(fileList) {
    batchFiles = Array.from(fileList).slice(0, 20);
    const listEl = document.getElementById('batch-file-list');
    listEl.classList.remove('hidden');

    let html = `<div style="margin-bottom:8px"><strong>${batchFiles.length} file${batchFiles.length > 1 ? 's' : ''} selected</strong></div>`;
    batchFiles.forEach((f, i) => {
        html += `<div class="batch-file-item"><span>${i+1}. ${f.name}</span><span style="color:var(--text-3)">${fmtSize(f.size)}</span></div>`;
    });
    html += `<button class="btn btn--solid" style="margin-top:12px;width:100%" id="btn-batch-start">Analyze ${batchFiles.length} Files</button>`;
    listEl.innerHTML = html;

    document.getElementById('btn-batch-start').addEventListener('click', startBatchAnalysis);
}

async function startBatchAnalysis() {
    if (!batchFiles.length) return;

    const profile = document.getElementById('profile-select').value;

    // Show progress
    document.getElementById('batch-upload-zone').classList.add('hidden');
    document.getElementById('batch-file-list').classList.add('hidden');
    document.getElementById('mode-toggle').classList.add('hidden');
    retainLabel.classList.add('hidden');
    document.getElementById('analysis-mode').classList.add('hidden');
    document.getElementById('profile-selector').classList.add('hidden');
    progressSection.classList.remove('hidden');
    progressFilename.textContent = `Batch: ${batchFiles.length} files`;
    progressPercent.textContent = '0%';
    progressFill.style.width = '0%';
    progressStatus.innerHTML = '<span class="spinner"></span>Starting analysis...';

    const results = [];
    const summary = { total: batchFiles.length, success: 0, failed: 0, avg_score: 0, files: [], processing_time_seconds: 0 };
    const batchStart = Date.now();

    for (let i = 0; i < batchFiles.length; i++) {
        const f = batchFiles[i];
        const pct = Math.round((i / batchFiles.length) * 100);
        progressPercent.textContent = pct + '%';
        progressFill.style.width = pct + '%';
        progressStatus.innerHTML = `<span class="spinner"></span>Analyzing file ${i + 1}/${batchFiles.length}: ${f.name}`;

        try {
            const formData = new FormData();
            formData.append('file', f);
            formData.append('profile', profile);

            const response = await fetch(`${API_BASE}/api/analyze`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                let detail = `Server error (${response.status})`;
                try { detail = (await response.json()).detail || detail; } catch {}
                results.push({ filename: f.name, success: false, error: detail });
                summary.failed++;
                continue;
            }

            const result = await response.json();
            if (result.success) {
                const fileSummary = {
                    filename: f.name,
                    success: true,
                    score: result.quality ? result.quality.score : null,
                    grade: result.quality ? result.quality.grade : null,
                    duration: result.file_info ? result.file_info.duration_formatted : null,
                    language: result.ai_analysis && result.ai_analysis.language ? result.ai_analysis.language.name : null,
                    mos: result.ai_analysis && result.ai_analysis.speech_quality ? result.ai_analysis.speech_quality.mos : null,
                    compliance: result.compliance ? result.compliance.overall : null,
                    time: result.processing_time_seconds,
                };
                summary.files.push(fileSummary);
                summary.success++;
                result.visualizations = null;
                results.push(result);
            } else {
                results.push({ filename: f.name, success: false, error: (result.errors || []).join(', ') || 'Analysis failed' });
                summary.failed++;
            }
        } catch (err) {
            results.push({ filename: f.name, success: false, error: err.message || 'Network error' });
            summary.failed++;
        }
    }

    // Final summary
    const scores = summary.files.filter(f => f.score != null).map(f => f.score);
    summary.avg_score = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length * 10) / 10 : 0;
    summary.processing_time_seconds = Math.round((Date.now() - batchStart) / 100) / 10;

    progressPercent.textContent = '100%';
    progressFill.style.width = '100%';

    batchResult = { summary, results };
    showBatchResults(batchResult);
}

function showBatchResults(data) {
    progressSection.classList.add('hidden');
    const batchSection = document.getElementById('batch-results-section');
    batchSection.classList.remove('hidden');

    const s = data.summary;

    // Summary card
    document.getElementById('batch-summary').innerHTML = `
        <h3 class="card-heading">Batch Summary</h3>
        <div class="batch-summary-grid">
            <div class="batch-stat">
                <div class="batch-stat-value">${s.total}</div>
                <div class="batch-stat-label">Files</div>
            </div>
            <div class="batch-stat">
                <div class="batch-stat-value" style="color:#27ae60">${s.success}</div>
                <div class="batch-stat-label">Success</div>
            </div>
            <div class="batch-stat">
                <div class="batch-stat-value" style="color:${s.failed > 0 ? '#E74C3C' : '#27ae60'}">${s.failed}</div>
                <div class="batch-stat-label">Failed</div>
            </div>
            <div class="batch-stat">
                <div class="batch-stat-value">${s.avg_score}</div>
                <div class="batch-stat-label">Avg Score</div>
            </div>
            <div class="batch-stat">
                <div class="batch-stat-value">${s.processing_time_seconds}s</div>
                <div class="batch-stat-label">Total Time</div>
            </div>
        </div>
    `;

    // Results table
    const files = s.files || [];
    let tableHtml = `<h3 class="card-heading">Results</h3>
        <div style="overflow-x:auto"><table class="batch-table">
        <thead><tr><th>#</th><th>Filename</th><th>Duration</th><th>Score</th><th>Grade</th><th>MOS</th><th>Language</th><th>Compliance</th><th>Time</th></tr></thead><tbody>`;

    files.forEach((f, i) => {
        const scoreColor = f.score >= 80 ? '#27ae60' : f.score >= 60 ? '#F5A623' : '#E74C3C';
        const compIcon = f.compliance === 'pass' ? '\u2705' : f.compliance === 'warn' ? '\u26A0\uFE0F' : '\u274C';
        tableHtml += `<tr>
            <td>${i+1}</td>
            <td title="${f.filename}">${(f.filename || '-').substring(0, 30)}</td>
            <td>${f.duration || '-'}</td>
            <td style="color:${scoreColor};font-weight:600">${f.score ?? '-'}</td>
            <td>${f.grade || '-'}</td>
            <td>${f.mos != null ? f.mos.toFixed(1) : '-'}</td>
            <td>${f.language || '-'}</td>
            <td>${compIcon} ${f.compliance || '-'}</td>
            <td>${f.time}s</td>
        </tr>`;
    });

    tableHtml += '</tbody></table></div>';
    document.getElementById('batch-table-container').innerHTML = tableHtml;
}

function downloadBatchCsv() {
    if (!batchResult) return;
    const files = batchResult.summary.files || [];
    let csv = 'Filename,Duration,Score,Grade,MOS,Language,Compliance,Time(s)\n';
    files.forEach(f => {
        csv += `"${f.filename || ''}","${f.duration || ''}",${f.score ?? ''},${f.grade || ''},${f.mos != null ? f.mos.toFixed(1) : ''},"${f.language || ''}",${f.compliance || ''},${f.time}\n`;
    });
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `batch-report-${Date.now()}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function resetBatch() {
    document.getElementById('batch-results-section').classList.add('hidden');
    document.getElementById('batch-upload-zone').classList.remove('hidden');
    document.getElementById('mode-toggle').classList.remove('hidden');
    retainLabel.classList.remove('hidden');
    document.getElementById('analysis-mode').classList.remove('hidden');
    document.getElementById('profile-selector').classList.remove('hidden');
    document.getElementById('batch-file-list').classList.add('hidden');
    progressSection.classList.add('hidden');
    batchFiles = [];
    batchResult = null;
}


// ── Compare Mode ───────────────────────────────────────

let compareFileA = null;
let compareFileB = null;

function setupCompare() {
    const boxA = document.getElementById('compare-box-a');
    const boxB = document.getElementById('compare-box-b');
    const inputA = document.getElementById('compare-input-a');
    const inputB = document.getElementById('compare-input-b');
    const startBtn = document.getElementById('btn-compare-start');

    boxA.addEventListener('click', () => inputA.click());
    boxB.addEventListener('click', () => inputB.click());

    inputA.addEventListener('change', () => {
        if (inputA.files.length) {
            compareFileA = inputA.files[0];
            document.getElementById('compare-name-a').textContent = `${compareFileA.name} (${fmtSize(compareFileA.size)})`;
            boxA.classList.add('has-file');
            updateCompareButton();
        }
    });

    inputB.addEventListener('change', () => {
        if (inputB.files.length) {
            compareFileB = inputB.files[0];
            document.getElementById('compare-name-b').textContent = `${compareFileB.name} (${fmtSize(compareFileB.size)})`;
            boxB.classList.add('has-file');
            updateCompareButton();
        }
    });

    startBtn.addEventListener('click', startCompare);
    document.getElementById('btn-compare-new').addEventListener('click', resetCompare);
}

function updateCompareButton() {
    const btn = document.getElementById('btn-compare-start');
    btn.disabled = !(compareFileA && compareFileB);
}

async function startCompare() {
    if (!compareFileA || !compareFileB) return;

    const profile = document.getElementById('profile-select').value;

    // Hide UI, show progress
    document.getElementById('compare-zone').classList.add('hidden');
    document.getElementById('mode-toggle').classList.add('hidden');
    retainLabel.classList.add('hidden');
    document.getElementById('analysis-mode').classList.add('hidden');
    document.getElementById('profile-selector').classList.add('hidden');
    progressSection.classList.remove('hidden');
    progressFilename.textContent = 'Comparing 2 files...';
    progressPercent.textContent = '';
    progressFill.style.width = '0%';
    progressStatus.innerHTML = '<span class="spinner"></span>Analyzing File A...';

    try {
        // Analyze both files sequentially (to show progress)
        const resultA = await analyzeForCompare(compareFileA, profile, 'A');
        progressStatus.innerHTML = '<span class="spinner"></span>Analyzing File B...';
        progressFill.style.width = '50%';
        const resultB = await analyzeForCompare(compareFileB, profile, 'B');

        showCompareResults(resultA, resultB);
    } catch (err) {
        showError(typeof err === 'string' ? err : 'Comparison failed');
    }
}

function analyzeForCompare(file, profile, label) {
    return new Promise((resolve, reject) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('retain', 'false');
        formData.append('profile', profile);

        const xhr = new XMLHttpRequest();
        xhr.addEventListener('load', () => {
            if (xhr.status === 200) {
                try { resolve(JSON.parse(xhr.responseText)); }
                catch { reject(`Invalid response for File ${label}`); }
            } else {
                reject(`File ${label} analysis failed (${xhr.status})`);
            }
        });
        xhr.addEventListener('error', () => reject(`Network error analyzing File ${label}`));
        xhr.addEventListener('timeout', () => reject(`File ${label} timed out`));
        xhr.open('POST', `${API_BASE}/api/analyze`);
        xhr.timeout = 600000;
        xhr.send(formData);
    });
}

function showCompareResults(a, b) {
    progressSection.classList.add('hidden');
    const section = document.getElementById('compare-results-section');
    section.classList.remove('hidden');

    const fiA = a.file_info || {};
    const fiB = b.file_info || {};
    const sigA = a.signal_analysis || {};
    const sigB = b.signal_analysis || {};
    const qA = a.quality || {};
    const qB = b.quality || {};
    const aiA = a.ai_analysis || {};
    const aiB = b.ai_analysis || {};
    const compA = a.compliance || {};
    const compB = b.compliance || {};

    function cmp(valA, valB, higher_better = true) {
        if (valA == null || valB == null) return ['', ''];
        const a_better = higher_better ? valA > valB : valA < valB;
        const b_better = higher_better ? valB > valA : valB < valA;
        const clsA = a_better ? 'compare-better' : (b_better ? 'compare-worse' : '');
        const clsB = b_better ? 'compare-better' : (a_better ? 'compare-worse' : '');
        return [clsA, clsB];
    }

    function row(label, valA, valB, higher_better = true) {
        const [clsA, clsB] = (typeof valA === 'number' && typeof valB === 'number')
            ? cmp(valA, valB, higher_better) : ['', ''];
        const fmtA = typeof valA === 'number' ? (Number.isInteger(valA) ? valA : valA.toFixed(1)) : (valA || '-');
        const fmtB = typeof valB === 'number' ? (Number.isInteger(valB) ? valB : valB.toFixed(1)) : (valB || '-');
        return `<tr><td>${label}</td><td class="${clsA}">${fmtA}</td><td class="${clsB}">${fmtB}</td></tr>`;
    }

    const scoreA = qA.score || 0;
    const scoreB = qB.score || 0;
    const [scA, scB] = cmp(scoreA, scoreB);

    let html = `<h3 class="card-heading">Side-by-Side Comparison</h3>
    <table class="compare-table">
    <thead><tr><th>Metric</th><th class="${scA}">File A: ${(fiA.filename || 'A').substring(0, 25)}<br><span style="font-size:1.5rem">${scoreA}</span>/100 (${qA.grade || '-'})</th><th class="${scB}">File B: ${(fiB.filename || 'B').substring(0, 25)}<br><span style="font-size:1.5rem">${scoreB}</span>/100 (${qB.grade || '-'})</th></tr></thead><tbody>`;

    // File info
    html += row('Duration', fiA.duration_formatted, fiB.duration_formatted);
    html += row('Format', `${fiA.format || '-'} / ${fiA.codec || '-'}`, `${fiB.format || '-'} / ${fiB.codec || '-'}`);
    html += row('Sample Rate', fiA.sample_rate, fiB.sample_rate, true);
    html += row('Bit Depth', fiA.bit_depth, fiB.bit_depth, true);
    html += row('Channels', fiA.channels, fiB.channels);

    // Signal
    html += row('SNR (dB)', sigA.snr_db, sigB.snr_db, true);
    html += row('Peak (dB)', sigA.peak_amplitude_db, sigB.peak_amplitude_db);
    html += row('RMS (dB)', sigA.rms_level_db, sigB.rms_level_db);
    html += row('Clipping %', sigA.clipping?.percentage, sigB.clipping?.percentage, false);
    html += row('Silence %', sigA.silence?.percentage, sigB.silence?.percentage, false);

    // AI
    const mosA = aiA.speech_quality?.mos;
    const mosB = aiB.speech_quality?.mos;
    html += row('MOS Score', mosA, mosB, true);
    html += row('Speech %', aiA.speech_activity?.speech_percentage, aiB.speech_activity?.speech_percentage, true);
    html += row('Speakers', aiA.speakers?.count, aiB.speakers?.count);
    html += row('Language', aiA.language?.name, aiB.language?.name);

    // Noise
    html += row('Noise Type', aiA.noise_classification?.primary_label, aiB.noise_classification?.primary_label);

    // Reverb
    html += row('RT60 (s)', aiA.reverb?.rt60_seconds, aiB.reverb?.rt60_seconds, false);
    html += row('Environment', aiA.reverb?.environment, aiB.reverb?.environment);

    // Compliance
    const compIconA = compA.overall === 'pass' ? '\u2705' : compA.overall === 'warn' ? '\u26A0\uFE0F' : '\u274C';
    const compIconB = compB.overall === 'pass' ? '\u2705' : compB.overall === 'warn' ? '\u26A0\uFE0F' : '\u274C';
    html += row('Compliance', `${compIconA} ${compA.overall || '-'}`, `${compIconB} ${compB.overall || '-'}`);

    html += '</tbody></table>';

    // Winner
    if (scoreA !== scoreB) {
        const winner = scoreA > scoreB ? 'A' : 'B';
        const diff = Math.abs(scoreA - scoreB);
        html += `<div style="text-align:center;margin-top:16px;padding:12px;background:var(--bg-2);border-radius:10px">
            <span style="font-size:1.2rem;font-weight:600">\ud83c\udfc6 File ${winner} wins by ${diff} points</span>
        </div>`;
    }

    document.getElementById('compare-results').innerHTML = html;
}

function resetCompare() {
    document.getElementById('compare-results-section').classList.add('hidden');
    document.getElementById('compare-zone').classList.remove('hidden');
    document.getElementById('mode-toggle').classList.remove('hidden');
    retainLabel.classList.remove('hidden');
    document.getElementById('analysis-mode').classList.remove('hidden');
    document.getElementById('profile-selector').classList.remove('hidden');
    progressSection.classList.add('hidden');
    compareFileA = null;
    compareFileB = null;
    document.getElementById('compare-name-a').textContent = 'No file selected';
    document.getElementById('compare-name-b').textContent = 'No file selected';
    document.getElementById('compare-box-a').classList.remove('has-file');
    document.getElementById('compare-box-b').classList.remove('has-file');
    document.getElementById('compare-input-a').value = '';
    document.getElementById('compare-input-b').value = '';
    document.getElementById('btn-compare-start').disabled = true;
}
