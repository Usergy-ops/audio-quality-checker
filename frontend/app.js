/* ── Audio Quality Checker — Frontend Logic ────────
   All backend integration intact. New DOM structure.
───────────────────────────────────────────────────── */

const API_BASE = window.location.origin;

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
let stageInterval = null;

const ANALYSIS_STAGES = [
    'Extracting file metadata...',
    'Analyzing signal quality...',
    'Checking for clipping and silence...',
    'Calculating signal-to-noise ratio...',
    'Running language detection...',
    'Detecting speech activity...',
    'Counting speakers...',
    'Computing quality score...',
    'Generating visualizations...',
    'Almost done...',
];

function startStages() {
    let i = 0;
    if (stageInterval) clearInterval(stageInterval);
    stageInterval = setInterval(() => {
        if (i < ANALYSIS_STAGES.length) {
            progressStatus.innerHTML = `<span class="spinner"></span>${ANALYSIS_STAGES[i]}`;
            i++;
        }
    }, 1500);
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
        alert('File too large. Maximum is 1 GB.');
        return;
    }

    const retain = document.getElementById('retain-checkbox').checked;
    const formData = new FormData();
    formData.append('file', file);
    formData.append('retain', retain.toString());

    // Show progress
    uploadZone.classList.add('hidden');
    retainLabel.classList.add('hidden');
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
            startStages();
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
    xhr.addEventListener('timeout', () => showError('Analysis timed out. Try a smaller file.'));

    xhr.open('POST', `${API_BASE}/api/analyze`);
    xhr.timeout = 300000;
    xhr.send(formData);
}


// ── Results ─────────────────────────────────────────

function showResults(r) {
    progressSection.classList.add('hidden');
    resultsSection.classList.remove('hidden');

    const safe = (fn, name) => { try { fn(); } catch(e) { console.error(`Render ${name} failed:`, e); } };

    safe(() => renderScore(r.quality), 'score');
    safe(() => renderFileInfo(r.file_info), 'fileInfo');
    safe(() => renderSignal(r.signal_analysis), 'signal');
    safe(() => renderAI(r.ai_analysis), 'ai');
    safe(() => renderBreakdown(r.quality), 'breakdown');
    safe(() => renderCompliance(r.compliance), 'compliance');
    safe(() => renderViz(r.visualizations), 'viz');
    safe(() => renderErrors(r.errors), 'errors');

    // Show processing time if available
    const timeEl = document.getElementById('score-time');
    if (timeEl && r.processing_time_seconds) {
        timeEl.textContent = `Analyzed in ${r.processing_time_seconds}s`;
    }
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
            ['Confidence', l.confidence != null ? `${(l.confidence * 100).toFixed(0)}%` : '-'],
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
}

function reset() {
    resultsSection.classList.add('hidden');
    progressSection.classList.add('hidden');
    uploadZone.classList.remove('hidden');
    retainLabel.classList.remove('hidden');
    fileInput.value = '';
    currentResult = null;

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


// ── Helpers ─────────────────────────────────────────

function showError(msg) {
    stopStages();
    progressSection.classList.add('hidden');
    uploadZone.classList.remove('hidden');
    retainLabel.classList.remove('hidden');
    alert(msg);
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


// ── Init ────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    setupMobileNav();
    setupUpload();
    setupButtons();
});
