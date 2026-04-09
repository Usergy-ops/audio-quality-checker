"""
Audio Quality Checker - Visualization Generator
Creates waveform, spectrogram, loudness, and speaker timeline images.
"""
import io
import base64
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import librosa
import librosa.display

from app.models.schemas import Visualizations, SpeechActivityInfo, SpeakerInfo

# Brand colors — light theme to match frontend
ELECTRIC_TEAL = '#00897B'
WARM_SAFFRON = '#F5A623'
SLATE_GRAY = '#888888'
BG_COLOR = '#ffffff'
GRID_COLOR = '#e8e8e8'
TITLE_COLOR = '#1c1c1c'
LABEL_COLOR = '#555555'

SPEAKER_COLORS = ['#00BFA6', '#F5A623', '#E74C3C', '#9B59B6', '#3498DB', '#2ECC71', '#E67E22', '#1ABC9C']

# Max samples to plot (downsample beyond this for performance)
# ~5 min at 22050Hz = 6.6M samples. We cap at 2M for fast plotting.
MAX_PLOT_SAMPLES = 2_000_000


def _downsample_for_plot(y: np.ndarray, max_samples: int = MAX_PLOT_SAMPLES) -> np.ndarray:
    """Downsample audio array for visualization (keeps peaks via min/max pairs)."""
    if len(y) <= max_samples:
        return y
    factor = len(y) // (max_samples // 2)
    # Trim to even multiple
    trimmed = y[:len(y) - (len(y) % factor)]
    reshaped = trimmed.reshape(-1, factor)
    # Keep min and max per chunk to preserve waveform shape
    mins = reshaped.min(axis=1)
    maxs = reshaped.max(axis=1)
    interleaved = np.empty(mins.size + maxs.size, dtype=y.dtype)
    interleaved[0::2] = mins
    interleaved[1::2] = maxs
    print(f"[Viz] Downsampled {len(y)} -> {len(interleaved)} samples for plotting")
    return interleaved


def _fig_to_base64(fig) -> str:
    """Convert matplotlib figure to base64 PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight',
                facecolor=BG_COLOR, edgecolor='none', pad_inches=0.1)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


def generate_waveform(y: np.ndarray, sr: int, speech_regions: list = None) -> str:
    """
    Generate waveform image with optional speech region highlighting.
    Returns base64-encoded PNG.
    """
    fig, ax = plt.subplots(1, 1, figsize=(12, 3))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    
    # Downsample for plotting performance
    y_plot = _downsample_for_plot(y)
    
    # Time axis (recomputed for downsampled data)
    duration_secs = len(y) / sr
    times = np.linspace(0, duration_secs, len(y_plot))
    
    # Plot waveform
    ax.plot(times, y_plot, color=ELECTRIC_TEAL, linewidth=0.3, alpha=0.8)
    
    # Highlight speech regions if available
    if speech_regions:
        for region in speech_regions:
            ax.axvspan(region['start_seconds'], region['end_seconds'],
                       alpha=0.15, color=WARM_SAFFRON, zorder=0)
    
    ax.set_xlim(0, times[-1] if len(times) > 0 else 1)
    ax.set_ylim(-1, 1)
    ax.set_xlabel('Time (s)', color=SLATE_GRAY, fontsize=9)
    ax.set_ylabel('Amplitude', color=SLATE_GRAY, fontsize=9)
    ax.set_title('Waveform', color=TITLE_COLOR, fontsize=11, fontweight='bold', pad=10)
    ax.tick_params(colors=SLATE_GRAY, labelsize=8)
    ax.grid(True, alpha=0.5, color=GRID_COLOR)
    
    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)
    
    return _fig_to_base64(fig)


def generate_spectrogram(y: np.ndarray, sr: int) -> str:
    """
    Generate mel spectrogram image.
    Returns base64-encoded PNG.
    """
    fig, ax = plt.subplots(1, 1, figsize=(12, 4))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    
    # Cap audio for spectrogram (max ~5 min at 22050Hz)
    max_spec_samples = sr * 300  # 5 min
    y_spec = y[:max_spec_samples] if len(y) > max_spec_samples else y
    
    # Compute mel spectrogram
    S = librosa.feature.melspectrogram(y=y_spec, sr=sr, n_mels=128, fmax=sr // 2)
    S_dB = librosa.power_to_db(S, ref=np.max)
    
    # Custom colormap
    img = librosa.display.specshow(
        S_dB, sr=sr, x_axis='time', y_axis='mel',
        ax=ax, cmap='magma', vmin=-80, vmax=0
    )
    
    cbar = fig.colorbar(img, ax=ax, format='%+2.0f dB', pad=0.02)
    cbar.ax.yaxis.set_tick_params(color=SLATE_GRAY)
    cbar.ax.yaxis.label.set_color(SLATE_GRAY)
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color=SLATE_GRAY, fontsize=8)
    
    ax.set_xlabel('Time (s)', color=SLATE_GRAY, fontsize=9)
    ax.set_ylabel('Frequency (Hz)', color=SLATE_GRAY, fontsize=9)
    ax.set_title('Mel Spectrogram', color=TITLE_COLOR, fontsize=11, fontweight='bold', pad=10)
    ax.tick_params(colors=SLATE_GRAY, labelsize=8)
    
    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)
    
    return _fig_to_base64(fig)


def generate_loudness(y: np.ndarray, sr: int) -> str:
    """
    Generate loudness (RMS energy) over time chart.
    Returns base64-encoded PNG.
    """
    fig, ax = plt.subplots(1, 1, figsize=(12, 2.5))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    
    # Cap audio for loudness chart
    max_loud_samples = sr * 300  # 5 min
    y_loud = y[:max_loud_samples] if len(y) > max_loud_samples else y
    
    # Compute RMS
    frame_length = int(sr * 0.05)
    hop_length = frame_length // 2
    rms = librosa.feature.rms(y=y_loud, frame_length=frame_length, hop_length=hop_length)[0]
    rms_db = 20 * np.log10(rms + 1e-10)
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
    
    # Plot with gradient fill
    ax.plot(times, rms_db, color=ELECTRIC_TEAL, linewidth=1, alpha=0.9)
    ax.fill_between(times, rms_db, -80, alpha=0.3, color=ELECTRIC_TEAL)
    
    # Reference lines
    ax.axhline(y=-20, color=WARM_SAFFRON, linestyle='--', alpha=0.5, linewidth=0.8, label='-20 dB')
    ax.axhline(y=-40, color='#E74C3C', linestyle='--', alpha=0.5, linewidth=0.8, label='-40 dB')
    
    ax.set_xlim(0, times[-1] if len(times) > 0 else 1)
    ax.set_ylim(-80, 0)
    ax.set_xlabel('Time (s)', color=SLATE_GRAY, fontsize=9)
    ax.set_ylabel('Loudness (dB)', color=SLATE_GRAY, fontsize=9)
    ax.set_title('Loudness Over Time', color=TITLE_COLOR, fontsize=11, fontweight='bold', pad=10)
    ax.tick_params(colors=SLATE_GRAY, labelsize=8)
    ax.grid(True, alpha=0.5, color=GRID_COLOR)
    ax.legend(fontsize=7, loc='upper right', facecolor=BG_COLOR, edgecolor=GRID_COLOR, labelcolor=SLATE_GRAY)
    
    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)
    
    return _fig_to_base64(fig)


def generate_speaker_timeline(speaker_info: SpeakerInfo, duration: float) -> str | None:
    """
    Generate speaker timeline visualization.
    Returns base64-encoded PNG, or None if no speakers.
    """
    if not speaker_info or speaker_info.count == 0 or len(speaker_info.timeline) == 0:
        return None
    
    fig, ax = plt.subplots(1, 1, figsize=(12, 1.5 + speaker_info.count * 0.5))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    
    # Map speakers to indices
    unique_speakers = sorted(set(seg['speaker'] for seg in speaker_info.timeline))
    speaker_idx = {spk: i for i, spk in enumerate(unique_speakers)}
    
    for seg in speaker_info.timeline:
        spk_i = speaker_idx[seg['speaker']]
        color = SPEAKER_COLORS[spk_i % len(SPEAKER_COLORS)]
        ax.barh(spk_i, seg['duration_seconds'], left=seg['start_seconds'],
                height=0.6, color=color, alpha=0.8, edgecolor='none')
    
    ax.set_yticks(range(len(unique_speakers)))
    ax.set_yticklabels([f'Speaker {i+1}' for i in range(len(unique_speakers))],
                       color=LABEL_COLOR, fontsize=9)
    ax.set_xlim(0, duration)
    ax.set_xlabel('Time (s)', color=SLATE_GRAY, fontsize=9)
    ax.set_title('Speaker Timeline', color=TITLE_COLOR, fontsize=11, fontweight='bold', pad=10)
    ax.tick_params(colors=SLATE_GRAY, labelsize=8)
    ax.grid(True, axis='x', alpha=0.5, color=GRID_COLOR)
    
    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)
    
    return _fig_to_base64(fig)


def generate_all_visualizations(
    y: np.ndarray,
    sr: int,
    speech_activity: SpeechActivityInfo | None = None,
    speaker_info: SpeakerInfo | None = None,
    duration: float = 0,
) -> Visualizations:
    """Generate all visualization images in parallel."""
    from concurrent.futures import ThreadPoolExecutor

    speech_regions = []
    if speech_activity and speech_activity.speech_regions:
        speech_regions = speech_activity.speech_regions

    # matplotlib is not fully thread-safe, but separate figures are OK
    with ThreadPoolExecutor(max_workers=4, thread_name_prefix="viz") as pool:
        f_wave = pool.submit(generate_waveform, y, sr, speech_regions)
        f_spec = pool.submit(generate_spectrogram, y, sr)
        f_loud = pool.submit(generate_loudness, y, sr)
        f_spk = pool.submit(generate_speaker_timeline, speaker_info, duration)

    return Visualizations(
        waveform=f_wave.result(),
        spectrogram=f_spec.result(),
        loudness=f_loud.result(),
        speakers=f_spk.result(),
    )
