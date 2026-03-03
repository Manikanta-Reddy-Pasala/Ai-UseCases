"""Spectral analysis of IQ data - FFT, PSD, signal detection, bandwidth estimation."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
from scipy import signal as scipy_signal

logger = logging.getLogger(__name__)


@dataclass
class DetectedSignal:
    """A signal detected in the spectrum."""
    center_freq_offset_hz: float  # Offset from tuned center freq
    bandwidth_hz: float
    power_db: float
    snr_db: float
    freq_start_hz: float  # Relative to center
    freq_end_hz: float
    peak_freq_hz: float
    # Set after band identification
    absolute_center_freq_hz: float = 0
    technology: str = ""
    band_info: dict = field(default_factory=dict)


@dataclass
class SpectrumAnalysis:
    """Complete spectral analysis result."""
    freq_axis_hz: np.ndarray = field(default_factory=lambda: np.array([]))
    psd_db: np.ndarray = field(default_factory=lambda: np.array([]))
    noise_floor_db: float = 0
    detected_signals: list[DetectedSignal] = field(default_factory=list)
    sample_rate_hz: float = 0
    center_freq_hz: float = 0
    fft_size: int = 0
    num_averages: int = 0


def compute_psd(
    samples: np.ndarray,
    sample_rate: float,
    fft_size: int = 4096,
    window: str = "hann",
    num_averages: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute Power Spectral Density using Welch's method.

    Returns (freq_axis_hz, psd_db).
    """
    if num_averages <= 0:
        num_averages = max(1, len(samples) // fft_size)

    # Use scipy Welch PSD estimation
    freqs, psd = scipy_signal.welch(
        samples,
        fs=sample_rate,
        window=window,
        nperseg=min(fft_size, len(samples)),
        noverlap=fft_size // 2,
        nfft=fft_size,
        return_onesided=False,
        detrend=False,
    )

    # Shift so DC is center (like SDR display)
    freqs = np.fft.fftshift(freqs)
    psd = np.fft.fftshift(psd)

    # Convert to dB
    psd_db = 10 * np.log10(np.maximum(psd, 1e-20))

    return freqs, psd_db


def estimate_noise_floor(psd_db: np.ndarray, percentile: float = 25) -> float:
    """Estimate noise floor as lower percentile of PSD."""
    return float(np.percentile(psd_db, percentile))


def detect_signals(
    freq_axis: np.ndarray,
    psd_db: np.ndarray,
    sample_rate: float,
    center_freq: float = 0,
    threshold_above_noise_db: float = 6,
    min_bandwidth_hz: float = 50e3,
    max_signals: int = 20,
) -> list[DetectedSignal]:
    """Detect individual signals in the spectrum.

    Algorithm:
    1. Estimate noise floor
    2. Find regions above threshold
    3. For each region, measure center freq, bandwidth, power, SNR
    4. Merge close signals
    """
    noise_floor = estimate_noise_floor(psd_db)
    threshold = noise_floor + threshold_above_noise_db

    # Find bins above threshold
    above = psd_db > threshold
    freq_resolution = freq_axis[1] - freq_axis[0] if len(freq_axis) > 1 else 1

    # Find contiguous regions above threshold
    signals = []
    in_signal = False
    start_idx = 0

    for i in range(len(above)):
        if above[i] and not in_signal:
            start_idx = i
            in_signal = True
        elif not above[i] and in_signal:
            in_signal = False
            _add_signal(signals, freq_axis, psd_db, start_idx, i,
                       noise_floor, min_bandwidth_hz, center_freq)

    # Handle signal at end
    if in_signal:
        _add_signal(signals, freq_axis, psd_db, start_idx, len(above),
                   noise_floor, min_bandwidth_hz, center_freq)

    # Sort by power (strongest first)
    signals.sort(key=lambda s: s.power_db, reverse=True)

    # Merge signals that are very close (< min_bandwidth gap)
    merged = _merge_close_signals(signals, min_bandwidth_hz)

    return merged[:max_signals]


def _add_signal(
    signals: list,
    freq_axis: np.ndarray,
    psd_db: np.ndarray,
    start_idx: int,
    end_idx: int,
    noise_floor: float,
    min_bandwidth_hz: float,
    center_freq: float,
):
    """Create a DetectedSignal from a contiguous region."""
    region_freqs = freq_axis[start_idx:end_idx]
    region_psd = psd_db[start_idx:end_idx]

    if len(region_freqs) < 2:
        return

    bandwidth = float(region_freqs[-1] - region_freqs[0])
    if bandwidth < min_bandwidth_hz:
        return

    peak_idx = np.argmax(region_psd)
    peak_freq = float(region_freqs[peak_idx])
    peak_power = float(region_psd[peak_idx])
    avg_power = float(np.mean(region_psd))

    # Center frequency: power-weighted centroid
    weights = 10 ** (region_psd / 10)  # Linear power
    center_offset = float(np.average(region_freqs, weights=weights))

    signals.append(DetectedSignal(
        center_freq_offset_hz=float(center_offset),
        bandwidth_hz=float(bandwidth),
        power_db=float(peak_power),
        snr_db=round(float(peak_power - noise_floor), 1),
        freq_start_hz=float(region_freqs[0]),
        freq_end_hz=float(region_freqs[-1]),
        peak_freq_hz=float(peak_freq),
        absolute_center_freq_hz=float(center_freq + center_offset) if center_freq > 0 else 0,
    ))


def _merge_close_signals(signals: list[DetectedSignal], gap_hz: float) -> list[DetectedSignal]:
    """Merge signals separated by less than gap_hz."""
    if len(signals) <= 1:
        return signals

    # Sort by frequency
    signals.sort(key=lambda s: s.freq_start_hz)
    merged = [signals[0]]

    for sig in signals[1:]:
        prev = merged[-1]
        if sig.freq_start_hz - prev.freq_end_hz < gap_hz:
            # Merge: extend the previous signal
            merged[-1] = DetectedSignal(
                center_freq_offset_hz=(prev.center_freq_offset_hz + sig.center_freq_offset_hz) / 2,
                bandwidth_hz=sig.freq_end_hz - prev.freq_start_hz,
                power_db=max(prev.power_db, sig.power_db),
                snr_db=max(prev.snr_db, sig.snr_db),
                freq_start_hz=prev.freq_start_hz,
                freq_end_hz=sig.freq_end_hz,
                peak_freq_hz=prev.peak_freq_hz if prev.power_db >= sig.power_db else sig.peak_freq_hz,
                absolute_center_freq_hz=prev.absolute_center_freq_hz,
            )
        else:
            merged.append(sig)

    return merged


def analyze_spectrum(
    samples: np.ndarray,
    sample_rate: float,
    center_freq: float = 0,
    fft_size: int = 4096,
    threshold_db: float = 6,
) -> SpectrumAnalysis:
    """Full spectral analysis pipeline."""
    freqs, psd_db = compute_psd(samples, sample_rate, fft_size)
    noise_floor = estimate_noise_floor(psd_db)
    detected = detect_signals(freqs, psd_db, sample_rate, center_freq, threshold_db)

    return SpectrumAnalysis(
        freq_axis_hz=freqs,
        psd_db=psd_db,
        noise_floor_db=noise_floor,
        detected_signals=detected,
        sample_rate_hz=sample_rate,
        center_freq_hz=center_freq,
        fft_size=fft_size,
        num_averages=max(1, len(samples) // fft_size),
    )
