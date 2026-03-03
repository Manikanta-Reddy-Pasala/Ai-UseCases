"""Spectrogram analyzer — works directly with pre-computed FFT/dBm data.

This handles the SAME input format as the YOLO scanner:
  - float32 array, reshaped to (N_rows x 2048)
  - Slice [:, 357:1691] = useful 1334 frequency bins
  - Values are power in dBm (-130 to -20 range)
  - Each column = one FFT bin = 15 kHz bandwidth
  - Each row = one time snapshot

No FFT needed — data is already in frequency domain.
"""

from __future__ import annotations

import logging

import numpy as np

from signal_processing.spectral_analyzer import DetectedSignal

logger = logging.getLogger(__name__)

FFT_SIZE = 2048
USEFUL_START = 357
USEFUL_END = 1691
KHZ_PER_BIN = 15  # 30.72 MHz / 2048 = 15 kHz per FFT bin
USEFUL_BINS = USEFUL_END - USEFUL_START  # 1334 bins


def analyze_spectrogram(
    raw_data: np.ndarray,
    center_freq_khz: float,
    bandwidth_khz: float,
    num_chunks: int = 1,
    overlap_khz: float = 10000,
    threshold_above_noise_db: float = 6,
    min_carrier_width_bins: int = 3,
) -> dict:
    """Analyze pre-computed spectrogram data (same format as YOLO scanner input).

    Args:
        raw_data: float32 array, will be reshaped to (N, 2048) and sliced
        center_freq_khz: center frequency in kHz
        bandwidth_khz: total bandwidth in kHz
        num_chunks: number of frequency chunks in the data
        threshold_above_noise_db: detection threshold above noise floor
        min_carrier_width_bins: minimum carrier width in FFT bins (1 bin = 15kHz)
    """
    n_floats = len(raw_data)
    n_rows = n_floats // FFT_SIZE
    spectrogram = raw_data.reshape(n_rows, FFT_SIZE)

    # Slice useful frequency range (same as YOLO scanner)
    spec = spectrogram[:, USEFUL_START:USEFUL_END]
    n_time, n_freq = spec.shape

    # Handle multi-chunk reassembly (same logic as scanner.py)
    if num_chunks > 1:
        rows_per_chunk = n_time // num_chunks
        parts = _reassemble_chunks(spec, num_chunks, rows_per_chunk)
        spec = parts

    # Average across time (rows) to get mean power spectrum
    mean_psd = np.mean(spec, axis=0)

    # Build frequency axis
    start_freq_khz = center_freq_khz - bandwidth_khz / 2
    freq_axis_khz = start_freq_khz + np.arange(len(mean_psd)) * KHZ_PER_BIN

    # Noise floor estimation
    noise_floor = float(np.percentile(mean_psd, 25))
    threshold = noise_floor + threshold_above_noise_db

    # --- PASS 1: Detect strong signals (3G/4G) ---
    strong_signals = _detect_from_psd(
        freq_axis_khz, mean_psd, noise_floor, threshold,
        min_width_bins=int(5000 / KHZ_PER_BIN),  # 5MHz minimum = skip 2G
        label="3G/4G",
    )

    # --- PASS 2: Detect 2G in gaps ---
    gap_mask = _compute_gap_mask(len(mean_psd), strong_signals, freq_axis_khz)
    weak_threshold = noise_floor + max(3, threshold_above_noise_db - 3)
    weak_signals = _detect_from_psd(
        freq_axis_khz, mean_psd, noise_floor, weak_threshold,
        min_width_bins=min_carrier_width_bins,
        label="2G",
        mask=gap_mask,
        is_gap=True,
    )

    all_signals = strong_signals + weak_signals

    # Classify each signal
    for sig in all_signals:
        bw_khz = sig.bandwidth_hz / 1000
        if bw_khz < 500:
            sig.technology = "GSM"
            sig.band_info = {"generation": "2G"}
        elif 3500 < bw_khz < 6500:
            # Could be UMTS (5MHz) or LTE (5MHz)
            # Use spectral flatness: CDMA is flatter
            if sig.spectral_flatness > 0.6:
                sig.technology = "UMTS"
                sig.band_info = {"generation": "3G"}
            else:
                sig.technology = "LTE"
                sig.band_info = {"generation": "4G"}
        elif bw_khz >= 6500:
            sig.technology = "LTE"
            sig.band_info = {"generation": "4G"}
        else:
            sig.technology = "LTE"
            sig.band_info = {"generation": "4G"}

    return {
        "signals": all_signals,
        "noise_floor_db": noise_floor,
        "n_time_rows": n_time,
        "n_freq_bins": n_freq,
        "freq_range_khz": (float(freq_axis_khz[0]), float(freq_axis_khz[-1])),
        "psd_mean": mean_psd,
        "freq_axis_khz": freq_axis_khz,
    }


def _detect_from_psd(
    freq_axis_khz, psd_db, noise_floor, threshold,
    min_width_bins=3, label="", mask=None, is_gap=False,
):
    """Detect signals from a 1D PSD array."""
    if mask is not None:
        scan = np.where(mask, psd_db, noise_floor - 10)
    else:
        scan = psd_db

    above = scan > threshold
    diff = np.diff(above.astype(np.int8))
    starts = np.where(diff == 1)[0] + 1
    ends = np.where(diff == -1)[0] + 1

    if above[0]:
        starts = np.concatenate([[0], starts])
    if above[-1]:
        ends = np.concatenate([ends, [len(above)]])

    min_len = min(len(starts), len(ends))
    if min_len == 0:
        return []
    starts, ends = starts[:min_len], ends[:min_len]

    signals = []
    for s, e in zip(starts, ends):
        width_bins = e - s
        if width_bins < min_width_bins:
            continue

        region_p = psd_db[s:e]
        region_f = freq_axis_khz[s:e]

        peak_idx = np.argmax(region_p)
        peak_power = float(region_p[peak_idx])

        # Power-weighted centroid for center frequency
        linear_p = 10.0 ** (region_p / 10.0)
        center_khz = float(np.dot(region_f, linear_p) / np.sum(linear_p))
        center_mhz = center_khz / 1000.0

        bw_khz = float(region_f[-1] - region_f[0])

        # Spectral flatness
        geo = np.exp(np.mean(np.log(np.maximum(linear_p, 1e-20))))
        arith = np.mean(linear_p)
        flatness = float(geo / arith) if arith > 0 else 0.5

        signals.append(DetectedSignal(
            center_freq_offset_hz=center_khz * 1000,
            bandwidth_hz=bw_khz * 1000,
            power_db=peak_power,
            snr_db=round(peak_power - noise_floor, 1),
            freq_start_hz=float(region_f[0]) * 1000,
            freq_end_hz=float(region_f[-1]) * 1000,
            peak_freq_hz=float(region_f[peak_idx]) * 1000,
            absolute_center_freq_hz=center_khz * 1000,
            is_2g_gap_detection=is_gap,
            spectral_flatness=round(flatness, 3),
        ))

    signals.sort(key=lambda s: s.power_db, reverse=True)
    return signals


def _compute_gap_mask(n_bins, strong_signals, freq_axis_khz):
    """Compute boolean mask where gaps exist between strong signals."""
    mask = np.ones(n_bins, dtype=bool)
    for sig in strong_signals:
        start_khz = sig.freq_start_hz / 1000
        end_khz = sig.freq_end_hz / 1000
        # Mask occupied region + some guard
        for i in range(n_bins):
            if start_khz - 500 <= freq_axis_khz[i] <= end_khz + 500:
                mask[i] = False
    return mask


def _reassemble_chunks(spec, num_chunks, rows_per_chunk):
    """Reassemble multi-chunk spectrogram (same logic as scanner.py)."""
    fifteen_mhz_points = int(15000 / KHZ_PER_BIN)  # 1000
    five_mhz_points = int(5000 / KHZ_PER_BIN)      # 333

    parts = []
    if num_chunks == 2:
        parts.append(spec[0:rows_per_chunk - 1, :fifteen_mhz_points])
        parts.append(spec[rows_per_chunk:rows_per_chunk * 2 - 1, five_mhz_points:])
    else:
        for i in range(1, num_chunks):
            if i == 1:
                parts.append(spec[0:rows_per_chunk - 1, :fifteen_mhz_points])
                parts.append(spec[rows_per_chunk:rows_per_chunk * 2 - 1, five_mhz_points:fifteen_mhz_points])
            elif i == num_chunks - 1:
                parts.append(spec[rows_per_chunk * i:rows_per_chunk * (i + 1) - 1, five_mhz_points:])
            else:
                parts.append(spec[rows_per_chunk * i:rows_per_chunk * (i + 1) - 1, five_mhz_points:fifteen_mhz_points])

    if parts:
        return np.concatenate(parts, axis=1)
    return spec
