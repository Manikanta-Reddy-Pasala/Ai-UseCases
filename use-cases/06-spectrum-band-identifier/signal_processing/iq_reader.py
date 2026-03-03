"""IQ data reader - supports common SDR file formats.

Supported formats:
  - Raw IQ: interleaved float32 (I,Q,I,Q,...) or complex64
  - Raw IQ: interleaved int16 (RTL-SDR), int8 (HackRF), uint8 (RTL-SDR raw)
  - NumPy: .npy complex64/complex128 arrays
  - CSV: two columns (I, Q) or single column complex
  - WAV: 2-channel audio (I=ch1, Q=ch2) from SDR# etc.
"""

from __future__ import annotations

import io
import logging
import struct

import numpy as np

logger = logging.getLogger(__name__)


def read_iq_data(
    data: bytes,
    fmt: str = "auto",
    sample_rate: float = 0,
    center_freq: float = 0,
    max_samples: int = 2_000_000,
) -> dict:
    """Read IQ data from bytes and return complex numpy array + metadata.

    Args:
        data: Raw bytes of IQ file
        fmt: Format hint - 'complex64', 'float32', 'int16', 'int8', 'uint8',
             'npy', 'csv', 'auto'
        sample_rate: Sample rate in Hz (0 = unknown)
        center_freq: Center frequency in Hz (0 = unknown)
        max_samples: Maximum samples to load
    """
    if fmt == "auto":
        fmt = _detect_format(data)
        logger.info("Auto-detected format: %s", fmt)

    samples = _parse_samples(data, fmt, max_samples)
    if samples is None or len(samples) == 0:
        raise ValueError("No valid IQ samples found")

    return {
        "samples": samples,
        "num_samples": len(samples),
        "sample_rate_hz": sample_rate,
        "center_freq_hz": center_freq,
        "format": fmt,
        "duration_sec": len(samples) / sample_rate if sample_rate > 0 else 0,
    }


def _detect_format(data: bytes) -> str:
    """Auto-detect IQ file format from header/content."""
    # NumPy .npy file magic
    if data[:6] == b"\x93NUMPY":
        return "npy"

    # WAV file
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "wav"

    # CSV-like (starts with digits, comma, or minus)
    try:
        head = data[:200].decode("ascii", errors="ignore")
        if "," in head and any(c.isdigit() for c in head[:20]):
            return "csv"
    except Exception:
        pass

    # Binary: guess from file size
    size = len(data)
    if size % 8 == 0:
        return "complex64"  # 4 bytes I + 4 bytes Q
    if size % 4 == 0:
        return "int16"  # 2 bytes I + 2 bytes Q (RTL-SDR)
    if size % 2 == 0:
        return "int8"  # 1 byte I + 1 byte Q (HackRF)
    return "uint8"


def _parse_samples(data: bytes, fmt: str, max_samples: int) -> np.ndarray:
    """Parse raw bytes into complex64 numpy array."""

    if fmt == "complex64":
        # Interleaved float32: I0,Q0,I1,Q1,...
        floats = np.frombuffer(data[:max_samples * 8], dtype=np.float32)
        return (floats[0::2] + 1j * floats[1::2]).astype(np.complex64)[:max_samples]

    if fmt == "float32":
        # Same as complex64 but explicitly float32 interleaved
        floats = np.frombuffer(data[:max_samples * 8], dtype=np.float32)
        return (floats[0::2] + 1j * floats[1::2]).astype(np.complex64)[:max_samples]

    if fmt == "int16":
        # RTL-SDR format: interleaved int16
        shorts = np.frombuffer(data[:max_samples * 4], dtype=np.int16)
        i_data = shorts[0::2].astype(np.float32) / 32768.0
        q_data = shorts[1::2].astype(np.float32) / 32768.0
        return (i_data + 1j * q_data).astype(np.complex64)[:max_samples]

    if fmt == "int8":
        # HackRF format: interleaved int8
        signed = np.frombuffer(data[:max_samples * 2], dtype=np.int8)
        i_data = signed[0::2].astype(np.float32) / 128.0
        q_data = signed[1::2].astype(np.float32) / 128.0
        return (i_data + 1j * q_data).astype(np.complex64)[:max_samples]

    if fmt == "uint8":
        # RTL-SDR raw: interleaved uint8, centered at 127.5
        raw = np.frombuffer(data[:max_samples * 2], dtype=np.uint8)
        i_data = (raw[0::2].astype(np.float32) - 127.5) / 127.5
        q_data = (raw[1::2].astype(np.float32) - 127.5) / 127.5
        return (i_data + 1j * q_data).astype(np.complex64)[:max_samples]

    if fmt == "npy":
        arr = np.load(io.BytesIO(data))
        if np.isrealobj(arr):
            # Interleaved real: treat as I,Q pairs
            return (arr[0::2] + 1j * arr[1::2]).astype(np.complex64)[:max_samples]
        return arr.astype(np.complex64)[:max_samples]

    if fmt == "csv":
        text = data.decode("utf-8", errors="replace")
        lines = [l.strip() for l in text.strip().split("\n") if l.strip() and not l.startswith("#")]
        samples = []
        for line in lines[:max_samples]:
            parts = line.split(",")
            if len(parts) >= 2:
                try:
                    samples.append(complex(float(parts[0]), float(parts[1])))
                except ValueError:
                    continue
        return np.array(samples, dtype=np.complex64)

    if fmt == "wav":
        import wave
        with wave.open(io.BytesIO(data)) as wf:
            n = min(wf.getnframes(), max_samples)
            raw = wf.readframes(n)
            width = wf.getsampwidth()
            channels = wf.getnchannels()
            if width == 2:
                arr = np.frombuffer(raw, dtype=np.int16).reshape(-1, channels)
            else:
                arr = np.frombuffer(raw, dtype=np.float32).reshape(-1, channels)
            if channels >= 2:
                return (arr[:, 0].astype(np.float32) / 32768.0 +
                        1j * arr[:, 1].astype(np.float32) / 32768.0).astype(np.complex64)
            return arr[:, 0].astype(np.complex64)

    raise ValueError("Unsupported format: %s" % fmt)


def generate_test_signal(
    signal_type: str = "lte",
    center_freq_hz: float = 1842.5e6,
    sample_rate_hz: float = 20e6,
    duration_sec: float = 0.01,
    snr_db: float = 20,
) -> dict:
    """Generate synthetic IQ test signal for a given technology.

    signal_type: 'gsm', 'umts', 'lte', '5g_nr', 'multi', 'noise'
    """
    n_samples = int(sample_rate_hz * duration_sec)
    t = np.arange(n_samples) / sample_rate_hz

    if signal_type == "gsm":
        # GSM: 200kHz GMSK-like signal (single carrier FM)
        bw = 200e3
        mod_idx = 0.5
        data_bits = np.random.choice([-1, 1], size=n_samples)
        phase = np.cumsum(data_bits) * mod_idx * np.pi / (sample_rate_hz / bw)
        signal = np.exp(1j * phase)
        signal *= np.exp(1j * 2 * np.pi * 50e3 * t)  # Offset from center

    elif signal_type == "umts":
        # UMTS: 5MHz CDMA-like wideband (spread spectrum, noise-like)
        bw = 5e6
        # Generate QPSK chips
        chips_i = np.random.choice([-1.0, 1.0], size=n_samples).astype(np.float64)
        chips_q = np.random.choice([-1.0, 1.0], size=n_samples).astype(np.float64)
        signal = (chips_i + 1j * chips_q).astype(np.complex128)
        # Bandlimit to 5MHz using simple frequency-domain filter
        S = np.fft.fft(signal)
        freqs = np.fft.fftfreq(n_samples, 1 / sample_rate_hz)
        S[np.abs(freqs) > bw / 2] = 0
        signal = np.fft.ifft(S).astype(np.complex64)
        signal *= 3.0  # Boost power

    elif signal_type == "lte":
        # LTE: 10MHz OFDM (many subcarriers)
        bw = 10e6
        n_subcarriers = 600  # 10MHz LTE = 600 used subcarriers
        fft_size = 1024
        symbols_needed = n_samples // fft_size + 1
        signal_parts = []
        for _ in range(symbols_needed):
            # OFDM symbol: random QPSK on each subcarrier
            freq_domain = np.zeros(fft_size, dtype=np.complex64)
            qpsk = np.exp(1j * np.pi / 4 * (2 * np.random.randint(0, 4, n_subcarriers) + 1))
            # Center subcarriers around DC
            start = (fft_size - n_subcarriers) // 2
            freq_domain[start:start + n_subcarriers] = qpsk
            ofdm_sym = np.fft.ifft(freq_domain)
            # Add cyclic prefix (72 samples for normal CP)
            cp_len = 72
            symbol_with_cp = np.concatenate([ofdm_sym[-cp_len:], ofdm_sym])
            signal_parts.append(symbol_with_cp)
        signal = np.concatenate(signal_parts)[:n_samples]
        signal *= np.sqrt(fft_size)  # Compensate IFFT normalization

    elif signal_type == "5g_nr":
        # 5G NR: 50MHz OFDM with wider subcarrier spacing (30kHz SCS)
        bw = 50e6
        n_subcarriers = 1632  # ~50MHz at 30kHz SCS
        fft_size = 4096
        symbols_needed = n_samples // fft_size + 1
        signal_parts = []
        for _ in range(symbols_needed):
            freq_domain = np.zeros(fft_size, dtype=np.complex64)
            qpsk = np.exp(1j * np.pi / 4 * (2 * np.random.randint(0, 4, n_subcarriers) + 1))
            start = (fft_size - n_subcarriers) // 2
            freq_domain[start:start + n_subcarriers] = qpsk
            ofdm_sym = np.fft.ifft(freq_domain)
            cp_len = 288  # Normal CP for 30kHz SCS
            signal_parts.append(np.concatenate([ofdm_sym[-cp_len:], ofdm_sym]))
        signal = np.concatenate(signal_parts)[:n_samples]
        signal *= np.sqrt(fft_size)  # Compensate IFFT normalization

    elif signal_type == "multi":
        # Multiple signals: GSM + LTE at different offsets
        gsm = generate_test_signal("gsm", center_freq_hz, sample_rate_hz, duration_sec, snr_db + 5)
        lte = generate_test_signal("lte", center_freq_hz, sample_rate_hz, duration_sec, snr_db)
        # Offset GSM by -5MHz, LTE centered
        gsm_shifted = gsm["samples"] * np.exp(-1j * 2 * np.pi * 5e6 * t[:len(gsm["samples"])])
        signal = lte["samples"][:n_samples] * 0.8 + gsm_shifted[:n_samples] * 0.3

    else:  # noise
        signal = np.zeros(n_samples, dtype=np.complex64)

    # Add noise
    noise_power = 10 ** (-snr_db / 10)
    noise = np.sqrt(noise_power / 2) * (np.random.randn(n_samples) + 1j * np.random.randn(n_samples))
    signal = signal.astype(np.complex64) + noise.astype(np.complex64)

    # Normalize
    signal = signal / (np.max(np.abs(signal)) + 1e-10) * 0.9

    return {
        "samples": signal.astype(np.complex64),
        "num_samples": len(signal),
        "sample_rate_hz": sample_rate_hz,
        "center_freq_hz": center_freq_hz,
        "format": "generated_%s" % signal_type,
        "duration_sec": duration_sec,
        "signal_type": signal_type,
    }
