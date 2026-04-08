/**
 * Audio Quality Checker - Frontend Application
 * Handles file upload, API communication, and results rendering
 */

// API Configuration
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : window.location.origin;

// DOM Elements
const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');
const progressSection = document.getElementById('progress-section');
const progressFilename = document.getElementById('progress-filename');
const progressPercent = document.getElementById('progress-percent');
const progressFill = document.getElementById('progress-fill');
const progressStatus = document.getElementById('progress-status');
const resultsSection = document.getElementById('results-section');
const btnDownloadJson = document.getElementById('btn-download-json');
const btnNewAnalysis = document.getElementById('btn-new-analysis');

// State
let currentResult = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupUploadZone();
    setupButtons();
    addSVGGradient();
});

// Add SVG gradient for score ring
function addSVGGradient() {
    const svg = document.querySelector('.score-ring');
    if (!svg) return;
    
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    defs.innerHTML = `
        <linearGradient id="score-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:#00BFA6"/>
            <stop offset="100%" style="stop-color:#F5A623"/>
        </linearGradient>
    `;
    svg.insertBefore(defs, svg.firstChild);
}

// Upload Zone Setup
function setupUploadZone() {
    // Click to browse
    uploadZone.addEventListener('click', () => fileInput.click());
    
    // File selection
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });
    
    // Drag and drop
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });
    
    uploadZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
    });
    
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFile(e.dataTransfer.files[0]);
        }
    });
}

// Button Setup
function setupButtons() {
    btnDownloadJson.addEventListener('click', downloadJson);
    btnNewAnalysis.addEventListener('click', resetUI);
}

// Handle file upload
async function handleFile(file) {
    // Validate file type
    const validExtensions = ['.wav', '.mp3', '.flac', '.ogg', '.aac', '.m4a', '.aiff', '.aif', '.opus', '.webm', '.wma', '.amr'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!validExtensions.includes(ext)) {
        showError(`Unsupported file format: ${ext}. Supported: ${validExtensions.join(', ')}`);
        return;
    }
    
    // Check file size (1 GB limit)
    if (file.size > 1024 * 1024 * 1024) {
        showError('File too large. Maximum size is 1 GB.');
        return;
    }
    
    // Show progress
    uploadZone.classList.add('hidden');
    progressSection.classList.remove('hidden');
    progressFilename.textContent = file.name;
    progressPercent.textContent = '0%';
    progressFill.style.width = '0%';
    progressStatus.textContent = 'Uploading...';
    
    try {
        // Upload file
        const formData = new FormData();
        formData.append('file', file);
        
        const xhr = new XMLHttpRequest();
        
        // Track upload progress
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                progressPercent.textContent = `${percent}%`;
                progressFill.style.width = `${percent}%`;
                
                if (percent === 100) {
                    progressStatus.innerHTML = '<span class="spinner"></span>Analyzing... This may take a moment.';
                }
            }
        });
        
        // Handle response
        xhr.addEventListener('load', () => {
            if (xhr.status === 200) {
                try {
                    const result = JSON.parse(xhr.responseText);
                    currentResult = result;
                    displayResults(result);
                } catch (e) {
                    showError('Failed to parse server response.');
                }
            } else {
                try {
                    const error = JSON.parse(xhr.responseText);
                    showError(error.detail || 'Analysis failed.');
                } catch (e) {
                    showError(`Server error: ${xhr.status}`);
                }
            }
        });
        
        xhr.addEventListener('error', () => {
            showError('Network error. Please check your connection.');
        });
        
        xhr.open('POST', `${API_BASE}/api/analyze`);
        xhr.send(formData);
        
    } catch (error) {
        showError(`Upload failed: ${error.message}`);
    }
}

// Display results
function displayResults(result) {
    progressSection.classList.add('hidden');
    resultsSection.classList.remove('hidden');
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth' });
    
    // Quality Score
    renderQualityScore(result.quality);
    
    // File Info
    renderFileInfo(result.file_info);
    
    // Signal Analysis
    renderSignalAnalysis(result);
    
    // AI Analysis
    renderAIAnalysis(result);
    
    // Quality Breakdown
    renderQualityBreakdown(result.quality);
    
    // Compliance
    renderCompliance(result.compliance);
    
    // Visualizations
    renderVisualizations(result.visualizations);
    
    // Errors/Warnings
    renderErrors(result.errors);
}

// Render Quality Score
function renderQualityScore(quality) {
    const score = quality?.score ?? 0;
    const grade = quality?.grade ?? '-';
    const summary = quality?.summary ?? 'Unable to calculate score';
    
    // Animate score number
    const scoreNumber = document.getElementById('score-number');
    animateNumber(scoreNumber, 0, score, 1000);
    
    // Animate ring
    const ring = document.getElementById('score-ring-fill');
    const circumference = 339.292;
    const offset = circumference - (score / 100) * circumference;
    setTimeout(() => {
        ring.style.strokeDashoffset = offset;
    }, 100);
    
    // Grade and summary
    document.getElementById('score-grade').textContent = grade;
    document.getElementById('score-summary').textContent = summary;
}

// Render File Info
function renderFileInfo(metadata) {
    const grid = document.getElementById('file-info-grid');
    if (!metadata) {
        grid.innerHTML = '<p class="info-value">Metadata unavailable</p>';
        return;
    }
    
    const items = [
        { label: 'Format', value: metadata.format?.toUpperCase() || '-' },
        { label: 'Codec', value: metadata.codec || '-' },
        { label: 'Duration', value: formatDuration(metadata.duration) },
        { label: 'Sample Rate', value: metadata.sample_rate ? `${metadata.sample_rate.toLocaleString()} Hz` : '-' },
        { label: 'Bit Depth', value: metadata.bit_depth ? `${metadata.bit_depth}-bit` : '-' },
        { label: 'Bit Rate', value: metadata.bit_rate ? `${Math.round(metadata.bit_rate / 1000)} kbps` : '-' },
        { label: 'Channels', value: metadata.channels ? (metadata.channels === 1 ? 'Mono' : metadata.channels === 2 ? 'Stereo' : `${metadata.channels}ch`) : '-' },
        { label: 'File Size', value: formatFileSize(metadata.file_size) },
    ];
    
    grid.innerHTML = items.map(item => `
        <div class="info-item">
            <span class="info-label">${item.label}</span>
            <span class="info-value">${item.value}</span>
        </div>
    `).join('');
}

// Render Signal Analysis
function renderSignalAnalysis(result) {
    const grid = document.getElementById('signal-grid');
    
    const signal = result.signal_analysis || {};
    const clipping = signal.clipping || {};
    const silence = signal.silence || {};
    const snr = { snr_db: signal.snr_db, noise_floor_db: signal.noise_floor_db };
    
    const items = [
        { 
            label: 'Peak Amplitude', 
            value: signal.peak_amplitude_db != null ? `${signal.peak_amplitude_db.toFixed(1)} dB` : '-',
            quality: signal.peak_amplitude_db > -3 ? 'bad' : signal.peak_amplitude_db > -6 ? 'warn' : 'good'
        },
        { 
            label: 'RMS Level', 
            value: signal.rms_level_db != null ? `${signal.rms_level_db.toFixed(1)} dB` : '-',
            quality: 'neutral'
        },
        { 
            label: 'Dynamic Range', 
            value: signal.dynamic_range_db != null ? `${signal.dynamic_range_db.toFixed(1)} dB` : '-',
            quality: signal.dynamic_range_db > 20 ? 'good' : signal.dynamic_range_db > 10 ? 'warn' : 'bad'
        },
        { 
            label: 'DC Offset', 
            value: signal.dc_offset != null ? `${(Math.abs(signal.dc_offset) * 100).toFixed(3)}%` : '-',
            quality: Math.abs(signal.dc_offset || 0) < 0.01 ? 'good' : Math.abs(signal.dc_offset || 0) < 0.05 ? 'warn' : 'bad'
        },
        { 
            label: 'Clipping', 
            value: clipping.percentage != null ? `${clipping.percentage.toFixed(2)}%` : '-',
            quality: (clipping.percentage || 0) < 0.01 ? 'good' : (clipping.percentage || 0) < 1 ? 'warn' : 'bad'
        },
        { 
            label: 'Silence', 
            value: silence.percentage != null ? `${silence.percentage.toFixed(1)}%` : '-',
            quality: (silence.percentage || 0) < 20 ? 'good' : (silence.percentage || 0) < 40 ? 'warn' : 'bad'
        },
        { 
            label: 'SNR', 
            value: snr.snr_db != null ? `${snr.snr_db.toFixed(1)} dB` : '-',
            quality: (snr.snr_db || 0) > 30 ? 'good' : (snr.snr_db || 0) > 15 ? 'warn' : 'bad'
        },
        { 
            label: 'Noise Floor', 
            value: snr.noise_floor_db != null ? `${snr.noise_floor_db.toFixed(1)} dB` : '-',
            quality: 'neutral'
        },
    ];
    
    grid.innerHTML = items.map(item => `
        <div class="info-item">
            <span class="info-label">${item.label}</span>
            <span class="info-value ${item.quality}">${item.value}</span>
        </div>
    `).join('');
}

// Render AI Analysis
function renderAIAnalysis(result) {
    const grid = document.getElementById('ai-grid');
    
    const aiData = result.ai_analysis || {};
    const language = aiData.language || {};
    const speech = aiData.speech_activity || {};
    const speakers = aiData.speakers || {};
    
    const items = [
        { 
            label: 'Language', 
            value: language.detected ? `${language.name || language.detected} (${language.confidence?.toFixed(0)}%)` : 'Unknown'
        },
        { 
            label: 'Alt Languages', 
            value: language.alternatives?.length ? language.alternatives.slice(0, 2).map(a => a.name || a.language).join(', ') : '-'
        },
        { 
            label: 'Speech Detected', 
            value: speech.speech_percentage != null ? (speech.speech_percentage > 0 ? 'Yes' : 'No') : '-'
        },
        { 
            label: 'Speech %', 
            value: speech.speech_percentage != null ? `${speech.speech_percentage.toFixed(1)}%` : '-'
        },
        { 
            label: 'Longest Speech', 
            value: speech.longest_speech_seconds != null ? formatDuration(speech.longest_speech_seconds) : '-'
        },
        { 
            label: 'Speaker Count', 
            value: speakers.count != null ? speakers.count : '-'
        },
    ];
    
    grid.innerHTML = items.map(item => `
        <div class="info-item">
            <span class="info-label">${item.label}</span>
            <span class="info-value">${item.value}</span>
        </div>
    `).join('');
}

// Render Quality Breakdown
function renderQualityBreakdown(quality) {
    const list = document.getElementById('breakdown-list');
    const breakdown = quality?.breakdown || [];
    
    if (!Array.isArray(breakdown) || breakdown.length === 0) {
        list.innerHTML = '<p class="info-value">No breakdown available</p>';
        return;
    }
    
    list.innerHTML = breakdown.map(item => {
        const score = item.score ?? 0;
        const level = score >= 80 ? 'excellent' : score >= 60 ? 'good' : score >= 40 ? 'fair' : 'poor';
        const weight = (item.weight * 100).toFixed(0);
        return `
            <div class="breakdown-item">
                <span class="breakdown-name">${item.component} (${weight}%)</span>
                <div class="breakdown-bar-container">
                    <div class="breakdown-bar ${level}" style="width: ${score}%"></div>
                </div>
                <span class="breakdown-score">${score.toFixed(0)}</span>
            </div>
        `;
    }).join('');
}

// Render Compliance
function renderCompliance(compliance) {
    const list = document.getElementById('compliance-list');
    const checks = compliance?.checks || [];
    
    if (checks.length === 0) {
        list.innerHTML = '<p class="info-value">No compliance data available</p>';
        return;
    }
    
    list.innerHTML = checks.map(check => {
        const icon = check.status === 'pass' ? '✅' : check.status === 'warn' ? '⚠️' : '❌';
        return `
            <div class="compliance-item">
                <span class="compliance-icon ${check.status}">${icon}</span>
                <div class="compliance-text">
                    <div class="compliance-name">${check.metric}</div>
                    <div class="compliance-detail">${check.message || check.value}</div>
                </div>
            </div>
        `;
    }).join('');
}

// Render Visualizations
function renderVisualizations(viz) {
    const container = document.getElementById('viz-container');
    
    if (!viz) {
        container.innerHTML = '<p class="info-value">Visualizations unavailable</p>';
        return;
    }
    
    const items = [
        { key: 'waveform', label: 'Waveform' },
        { key: 'spectrogram', label: 'Mel Spectrogram' },
        { key: 'loudness', label: 'Loudness Over Time' },
        { key: 'speakers', label: 'Speaker Timeline' },
    ];
    
    container.innerHTML = items
        .filter(item => viz[item.key])
        .map(item => `
            <div class="viz-item">
                <img src="data:image/png;base64,${viz[item.key]}" alt="${item.label}">
                <div class="viz-label">${item.label}</div>
            </div>
        `).join('');
}

// Render Errors
function renderErrors(errors) {
    const card = document.getElementById('errors-card');
    const list = document.getElementById('errors-list');
    
    if (!errors || errors.length === 0) {
        card.classList.add('hidden');
        return;
    }
    
    card.classList.remove('hidden');
    list.innerHTML = errors.map(error => `
        <div class="error-item">
            <span>⚠️</span>
            <span>${error}</span>
        </div>
    `).join('');
}

// Download JSON report
function downloadJson() {
    if (!currentResult) return;
    
    const blob = new Blob([JSON.stringify(currentResult, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audio-quality-report-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Reset UI for new analysis
function resetUI() {
    currentResult = null;
    fileInput.value = '';
    
    resultsSection.classList.add('hidden');
    progressSection.classList.add('hidden');
    uploadZone.classList.remove('hidden');
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Show error message
function showError(message) {
    progressSection.classList.add('hidden');
    uploadZone.classList.remove('hidden');
    
    // Create temporary error toast
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        bottom: 2rem;
        left: 50%;
        transform: translateX(-50%);
        background: #EF4444;
        color: white;
        padding: 1rem 2rem;
        border-radius: 8px;
        font-weight: 500;
        z-index: 1000;
        animation: fadeInUp 0.3s ease;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// Utility: Format duration
function formatDuration(seconds) {
    if (seconds == null) return '-';
    
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    const ms = Math.round((seconds % 1) * 1000);
    
    if (h > 0) {
        return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    } else if (m > 0) {
        return `${m}:${s.toString().padStart(2, '0')}`;
    } else {
        return `${s}.${ms.toString().padStart(3, '0')}s`;
    }
}

// Utility: Format file size
function formatFileSize(bytes) {
    if (bytes == null) return '-';
    
    const units = ['B', 'KB', 'MB', 'GB'];
    let i = 0;
    let size = bytes;
    
    while (size >= 1024 && i < units.length - 1) {
        size /= 1024;
        i++;
    }
    
    return `${size.toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
}

// Utility: Animate number
function animateNumber(element, from, to, duration) {
    const start = performance.now();
    const range = to - from;
    
    function update(timestamp) {
        const elapsed = timestamp - start;
        const progress = Math.min(elapsed / duration, 1);
        
        // Ease out
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = Math.round(from + range * eased);
        
        element.textContent = current;
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

// Add CSS animation for toast
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeInUp {
        from { opacity: 0; transform: translate(-50%, 20px); }
        to { opacity: 1; transform: translate(-50%, 0); }
    }
    @keyframes fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
    }
`;
document.head.appendChild(style);
