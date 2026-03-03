"""Spectral analysis — optimized for sub-5ms pipeline.

Uses raw numpy FFT (not scipy.welch) + vectorized signal detection.
Benchmark: FFT(2048) = 0.2ms, detection = 0.5ms, total pipeline < 3ms.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)

# Pre-compute windows for common FFT sizes (avoid recomputing every call)
_WINDOWS: dict[int, np.ndarray] = {}


def _get_window(n: int) -> np.ndarray:
    if n not in _WINDOWS:
        _WINDOWS[n] = np.hanning(n).astype(np.float64)
    return _WINDOWS[n]


@dataclass
class DetectedSignal:
    center_freq_offset_hz: float
    bandwidth_hz: float
    power_db: float
    snr_db: float
    freq_start_hz: float
    freq_end_hz: float
    peak_freq_hz: float
    absolute_center_freq_hz: float = 0
    technology: str = ""
    band_info: dict = field(default_factory=dict)


@dataclass
class SpectrumAnalysis:
    freq_axis_hz: np.ndarray = field(default_factory=lambda: np.array([]))
    psd_db: np.ndarray = field(default_factory=lambda: np.array([]))
    noise_floor_db: float = 0
    detected_signals: list[DetectedSignal] = field(default_factory=list)
    sample_rate_hz: float = 0
    center_freq_hz: float = 0
    fft_size: int = 0


def compute_psd(
    samples: np.ndarray,
    sample_rate: float,
    fft_size: int = 2048,
) -> tuple[np.ndarray, np.ndarray]:
    """Fast PSD: raw FFT + Hanning window + averaging. ~0.3ms for 2048."""
    N = min(fft_size, len(samples))
    window = _get_window(N)
    window_power = np.sum(window ** 2)

    # Average up to 8 frames for noise reduction
    n_frames = min(max(1, len(samples) // N), 8)
    psd_acc = np.zeros(N, dtype=np.float64)

    for i in range(n_frames):
        offset = i * N
        if offset + N > len(samples):
            break
        frame = samples[offset:offset + N].astype(np.complex128) * window
        psd_acc += np.abs(np.fft.fft(frame)) ** 2

    psd_acc /= (n_frames * window_power * sample_rate)
    psd_acc = np.fft.fftshift(psd_acc)
    psd_db = 10 * np.log10(np.maximum(psd_acc, 1e-20))
    freqs = np.fft.fftshift(np.fft.fftfreq(N, 1.0 / sample_rate))

    return freqs, psd_db


def detect_signals(
    freq_axis: np.ndarray,
    psd_db: np.ndarray,
    sample_rate: float,
    center_freq: float = 0,
    threshold_above_noise_db: float = 6,
    min_bandwidth_hz: float = 50e3,
    max_signals: int = 10,
) -> list[DetectedSignal]:
    """Vectorized signal detection. ~0.5ms."""
    noise_floor = float(np.percentile(psd_db, 25))
    threshold = noise_floor + threshold_above_noise_db

    above = psd_db > threshold
    diff = np.diff(above.astype(np.int8))
    starts = np.where(diff == 1)[0] + 1
    ends = np.where(diff == -1)[0] + 1

    if above[0]:
        starts = np.concatenate([[0], starts])
    if above[-1]:
        ends = np.concatenate([ends, [len(above)]])

    if len(starts) == 0 or len(ends) == 0:
        return []

    # Ensure pairs
    min_len = min(len(starts), len(ends))
    starts = starts[:min_len]
    ends = ends[:min_len]

    signals = []
    for s, e in zip(starts, ends):
        if e - s < 2:
            continue
        region_f = freq_axis[s:e]
        region_p = psd_db[s:e]
        bw = float(region_f[-1] - region_f[0])
        if bw < min_bandwidth_hz:
            continue

        peak_idx = np.argmax(region_p)
        peak_pwr = float(region_p[peak_idx])
        weights = 10.0 ** (region_p / 10.0)
        center_off = float(np.dot(region_f, weights) / np.sum(weights))

        signals.append(DetectedSignal(
            center_freq_offset_hz=float(center_off),
            bandwidth_hz=float(bw),
            power_db=float(peak_pwr),
            snr_db=round(float(peak_pwr - noise_floor), 1),
            freq_start_hz=float(region_f[0]),
            freq_end_hz=float(region_f[-1]),
            peak_freq_hz=float(region_f[peak_idx]),
            absolute_center_freq_hz=float(center_freq + center_off) if center_freq > 0 else 0,
        ))

    signals.sort(key=lambda s: s.power_db, reverse=True)
    return signals[:max_signals]


def analyze_spectrum(
    samples: np.ndarray,
    sample_rate: float,
    center_freq: float = 0,
    fft_size: int = 2048,
    threshold_db: float = 6,
) -> SpectrumAnalysis:
    """Full pipeline. Target: <3ms for analysis (excluding I/O)."""
    freqs, psd_db = compute_psd(samples, sample_rate, fft_size)
    noise_floor = float(np.percentile(psd_db, 25))
    detected = detect_signals(freqs, psd_db, sample_rate, center_freq, threshold_db)

    return SpectrumAnalysis(
        freq_axis_hz=freqs,
        psd_db=psd_db,
        noise_floor_db=noise_floor,
        detected_signals=detected,
        sample_rate_hz=sample_rate,
        center_freq_hz=center_freq,
        fft_size=fft_size,
    )
