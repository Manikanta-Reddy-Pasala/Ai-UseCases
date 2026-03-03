"""Technology classifier - identifies 2G/3G/4G/5G from signal characteristics.

Classification is based on:
  1. Bandwidth (primary indicator)
  2. Spectral shape (OFDM vs CDMA vs single-carrier)
  3. Subcarrier spacing detection (LTE vs NR)
  4. Known band database matching
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from signal_processing.spectral_analyzer import DetectedSignal
from bands.spectrum_db import identify_band_by_frequency

logger = logging.getLogger(__name__)


# Technology bandwidth signatures
TECH_SIGNATURES = {
    "GSM": {
        "bandwidths_khz": [200],
        "bw_tolerance": 0.5,  # ±50%
        "spectral_type": "single_carrier",
        "subcarrier_spacing_khz": None,
        "description": "200kHz GMSK single carrier",
    },
    "UMTS": {
        "bandwidths_khz": [5000],
        "bw_tolerance": 0.3,
        "spectral_type": "cdma",
        "subcarrier_spacing_khz": None,
        "description": "5MHz WCDMA spread spectrum",
    },
    "LTE": {
        "bandwidths_khz": [1400, 3000, 5000, 10000, 15000, 20000],
        "bw_tolerance": 0.2,
        "spectral_type": "ofdm",
        "subcarrier_spacing_khz": 15,
        "description": "OFDM with 15kHz subcarrier spacing",
    },
    "5G_NR_FR1": {
        "bandwidths_khz": [5000, 10000, 15000, 20000, 25000, 30000, 40000, 50000, 60000, 80000, 100000],
        "bw_tolerance": 0.2,
        "spectral_type": "ofdm",
        "subcarrier_spacing_khz": 30,  # Common SCS for FR1
        "description": "OFDM with 15/30/60kHz SCS, up to 100MHz",
    },
    "5G_NR_FR2": {
        "bandwidths_khz": [50000, 100000, 200000, 400000],
        "bw_tolerance": 0.25,
        "spectral_type": "ofdm",
        "subcarrier_spacing_khz": 120,
        "description": "mmWave OFDM with 60/120kHz SCS, up to 400MHz",
    },
}


@dataclass
class ClassificationResult:
    technology: str  # GSM, UMTS, LTE, 5G_NR_FR1, 5G_NR_FR2
    generation: str  # 2G, 3G, 4G, 5G
    confidence: float  # 0.0 - 1.0
    bandwidth_khz: float
    center_freq_hz: float
    center_freq_mhz: float
    spectral_type: str
    matched_standard_bw_khz: float = 0
    band_matches: list = None
    reasoning: list = None
    decoding_hint: str = ""

    def __post_init__(self):
        if self.band_matches is None:
            self.band_matches = []
        if self.reasoning is None:
            self.reasoning = []


def classify_signal(
    sig: DetectedSignal,
    samples: np.ndarray = None,
    sample_rate: float = 0,
) -> ClassificationResult:
    """Classify a detected signal into a cellular technology.

    Uses bandwidth matching + spectral analysis + band database.
    """
    bw_khz = sig.bandwidth_hz / 1000
    abs_center_hz = sig.absolute_center_freq_hz
    abs_center_mhz = abs_center_hz / 1e6 if abs_center_hz > 0 else 0

    reasoning = []
    scores = {}

    # --- Step 1: Bandwidth matching ---
    for tech, sig_info in TECH_SIGNATURES.items():
        best_match = 0
        best_bw = 0
        for std_bw in sig_info["bandwidths_khz"]:
            ratio = bw_khz / std_bw if std_bw > 0 else 0
            if abs(ratio - 1.0) <= sig_info["bw_tolerance"]:
                match_score = 1.0 - abs(ratio - 1.0)
                if match_score > best_match:
                    best_match = match_score
                    best_bw = std_bw
        if best_match > 0:
            scores[tech] = {"bw_score": best_match, "matched_bw_khz": best_bw}
            reasoning.append("BW %.0fkHz matches %s standard %dkHz (%.0f%%)" %
                           (bw_khz, tech, best_bw, best_match * 100))

    # --- Step 2: Spectral shape analysis (OFDM detection) ---
    if samples is not None and sample_rate > 0 and len(samples) >= 1024:
        is_ofdm, ofdm_confidence, scs_estimate = _detect_ofdm(samples, sample_rate)
        reasoning.append("OFDM detection: %s (confidence: %.0f%%, SCS est: %s kHz)" %
                        (is_ofdm, ofdm_confidence * 100,
                         "%.1f" % (scs_estimate / 1000) if scs_estimate else "N/A"))

        for tech in scores:
            sig_info = TECH_SIGNATURES[tech]
            if sig_info["spectral_type"] == "ofdm" and is_ofdm:
                scores[tech]["ofdm_score"] = ofdm_confidence
                # SCS matching for LTE vs NR
                if scs_estimate and sig_info["subcarrier_spacing_khz"]:
                    scs_ratio = scs_estimate / (sig_info["subcarrier_spacing_khz"] * 1000)
                    if 0.7 < scs_ratio < 1.3:
                        scores[tech]["scs_score"] = 1.0 - abs(scs_ratio - 1.0)
            elif sig_info["spectral_type"] != "ofdm" and not is_ofdm:
                scores[tech]["ofdm_score"] = 0.5  # Slight bonus for non-OFDM match

    # --- Step 3: Band database lookup ---
    if abs_center_mhz > 0:
        band_matches = identify_band_by_frequency(abs_center_mhz)
        if band_matches:
            reasoning.append("Freq %.1f MHz matches %d bands in database" %
                           (abs_center_mhz, len(band_matches)))
            for bm in band_matches:
                gen = bm["generation"]
                tech_from_gen = {"2G": "GSM", "3G": "UMTS", "4G": "LTE", "5G": "5G_NR_FR1"}
                tech = tech_from_gen.get(gen)
                if tech and tech in scores:
                    scores[tech]["band_score"] = 0.8
                    reasoning.append("Band match: %s %s (Band %s)" %
                                   (gen, bm["name"], bm["band_number"]))
    else:
        band_matches = []

    # --- Step 4: Calculate final scores ---
    if not scores:
        # No matches - try to guess from bandwidth alone
        if bw_khz < 500:
            tech_guess = "GSM"
        elif bw_khz < 6000:
            tech_guess = "UMTS" if bw_khz > 3000 else "LTE"
        elif bw_khz < 25000:
            tech_guess = "LTE"
        else:
            tech_guess = "5G_NR_FR1"
        reasoning.append("No strong match; guessing %s from BW=%.0fkHz" % (tech_guess, bw_khz))
        return _build_result(tech_guess, 0.3, bw_khz, abs_center_hz, 0, band_matches, reasoning)

    best_tech = None
    best_score = 0
    best_bw = 0
    for tech, tech_scores in scores.items():
        total = (tech_scores.get("bw_score", 0) * 0.4 +
                tech_scores.get("ofdm_score", 0) * 0.25 +
                tech_scores.get("scs_score", 0) * 0.15 +
                tech_scores.get("band_score", 0) * 0.2)
        if total > best_score:
            best_score = total
            best_tech = tech
            best_bw = tech_scores.get("matched_bw_khz", 0)

    return _build_result(best_tech, min(best_score, 0.99), bw_khz, abs_center_hz,
                        best_bw, band_matches, reasoning)


def _build_result(tech, confidence, bw_khz, center_hz, matched_bw, band_matches, reasoning):
    gen_map = {"GSM": "2G", "UMTS": "3G", "LTE": "4G", "5G_NR_FR1": "5G", "5G_NR_FR2": "5G"}
    gen = gen_map.get(tech, "Unknown")
    center_mhz = center_hz / 1e6 if center_hz > 0 else 0

    # Decoding hints
    hints = {
        "GSM": "Decode with: grgsm_livemon -f %.6fM | wireshark" % (center_mhz),
        "UMTS": "Decode with: srsUE or use UMTS cell scanner at %.3f MHz, SF=5MHz" % center_mhz,
        "LTE": "Decode with: srsLTE / srsRAN at fc=%.3f MHz, bw=%dkHz, SCS=15kHz"
               % (center_mhz, bw_khz),
        "5G_NR_FR1": "Decode with: srsRAN 5G at fc=%.3f MHz, bw=%dkHz, SCS=30kHz, SSB"
                     % (center_mhz, bw_khz),
        "5G_NR_FR2": "Decode: mmWave NR at fc=%.3f MHz, bw=%dMHz, SCS=120kHz"
                     % (center_mhz, bw_khz / 1000),
    }

    return ClassificationResult(
        technology=tech,
        generation=gen,
        confidence=round(confidence, 3),
        bandwidth_khz=round(bw_khz, 1),
        center_freq_hz=center_hz,
        center_freq_mhz=round(center_mhz, 3),
        spectral_type=TECH_SIGNATURES.get(tech, {}).get("spectral_type", "unknown"),
        matched_standard_bw_khz=matched_bw,
        band_matches=band_matches[:5],
        reasoning=reasoning,
        decoding_hint=hints.get(tech, ""),
    )


def _detect_ofdm(samples: np.ndarray, sample_rate: float) -> tuple[bool, float, float]:
    """Fast OFDM detection via vectorized CP autocorrelation. Target: <2ms.

    Uses vectorized sliding correlation instead of per-symbol loop.
    """
    n = min(len(samples), 20000)  # Only need ~1ms of data
    x = samples[:n].astype(np.complex64)

    best_corr = 0.0
    best_fft = 0

    # Only test the most likely FFT sizes for the sample rate
    for fft_size in [128, 256, 512, 1024, 2048]:
        if fft_size >= n // 3:
            continue
        cp_len = max(4, int(fft_size * 72 / 2048))  # Normal CP ratio
        symbol_len = fft_size + cp_len

        num_syms = min(n // symbol_len, 10)  # Only check 10 symbols
        if num_syms < 2:
            continue

        # Vectorized: extract all CP and tail segments at once
        offsets = np.arange(num_syms) * symbol_len
        valid = offsets + symbol_len <= n
        offsets = offsets[valid]

        if len(offsets) < 2:
            continue

        total_corr = 0.0
        count = 0
        for off in offsets:
            cp = x[off:off + cp_len]
            tail = x[off + fft_size:off + fft_size + cp_len]
            num = np.abs(np.vdot(cp, tail))
            denom = np.sqrt(np.vdot(cp, cp).real * np.vdot(tail, tail).real) + 1e-10
            total_corr += num / denom
            count += 1

        avg_corr = total_corr / count if count > 0 else 0
        if avg_corr > best_corr:
            best_corr = float(avg_corr)
            best_fft = fft_size

    is_ofdm = best_corr > 0.3
    confidence = min(best_corr * 1.5, 1.0)
    scs = sample_rate / best_fft if best_fft > 0 else 0

    return is_ofdm, round(confidence, 3), round(scs, 0)
