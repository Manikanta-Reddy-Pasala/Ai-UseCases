"""Technology classifier v3 — fixes UMTS vs LTE vs LTE-TDD distinction.

Improvements:
  1. Spectral flatness: UMTS (CDMA ~0.7-0.9) vs LTE (OFDM ~0.3-0.6) vs GSM (<0.2)
  2. TDD detection: power variance across time frames
  3. Bandwidth precision: uses -3dB measurement, matches closer to 3GPP standards
  4. 2G gap detection: lower confidence threshold for gap-detected signals
  5. Band DB cross-validation: generation from band must match BW-based guess
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from signal_processing.spectral_analyzer import DetectedSignal, detect_tdd_pattern
from bands.spectrum_db import identify_band_by_frequency

logger = logging.getLogger(__name__)


TECH_SIGNATURES = {
    "GSM": {
        "bandwidths_khz": [200],
        "bw_tolerance": 1.0,  # Wide tolerance — 2G can appear 100-400kHz
        "spectral_type": "single_carrier",
        "flatness_range": (0.0, 0.35),  # Peaked, narrow
        "subcarrier_spacing_khz": None,
    },
    "UMTS": {
        "bandwidths_khz": [5000],
        "bw_tolerance": 0.25,
        "spectral_type": "cdma",
        "flatness_range": (0.55, 1.0),  # Flat, noise-like (CDMA spread)
        "subcarrier_spacing_khz": None,
    },
    "LTE_FDD": {
        "bandwidths_khz": [1400, 3000, 5000, 10000, 15000, 20000],
        "bw_tolerance": 0.25,
        "spectral_type": "ofdm",
        "flatness_range": (0.25, 0.65),  # OFDM: flatter than GSM, less flat than CDMA
        "subcarrier_spacing_khz": 15,
    },
    "LTE_TDD": {
        "bandwidths_khz": [5000, 10000, 15000, 20000],
        "bw_tolerance": 0.25,
        "spectral_type": "ofdm",
        "flatness_range": (0.25, 0.65),
        "subcarrier_spacing_khz": 15,
    },
    "5G_NR_FR1": {
        "bandwidths_khz": [5000, 10000, 15000, 20000, 25000, 30000, 40000, 50000, 60000, 80000, 100000],
        "bw_tolerance": 0.25,
        "spectral_type": "ofdm",
        "flatness_range": (0.25, 0.65),
        "subcarrier_spacing_khz": 30,
    },
    "5G_NR_FR2": {
        "bandwidths_khz": [50000, 100000, 200000, 400000],
        "bw_tolerance": 0.3,
        "spectral_type": "ofdm",
        "flatness_range": (0.25, 0.65),
        "subcarrier_spacing_khz": 120,
    },
}

# Bands known to be TDD (from 3GPP)
TDD_BANDS_4G = {38, 39, 40, 41, 42, 43, 46, 48}
TDD_BANDS_5G = {"n38", "n40", "n41", "n46", "n48", "n77", "n78", "n79", "n257", "n258", "n260", "n261"}


@dataclass
class ClassificationResult:
    technology: str
    generation: str
    confidence: float
    bandwidth_khz: float
    center_freq_hz: float
    center_freq_mhz: float
    spectral_type: str
    matched_standard_bw_khz: float = 0
    band_matches: list = None
    reasoning: list = None
    decoding_hint: str = ""
    is_tdd: bool = False
    spectral_flatness: float = 0.0
    is_gap_detected: bool = False

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
    """Classify with all 4 fixes applied."""
    bw_khz = sig.bandwidth_hz / 1000
    abs_center_hz = sig.absolute_center_freq_hz
    abs_center_mhz = abs_center_hz / 1e6 if abs_center_hz > 0 else 0
    flatness = sig.spectral_flatness

    reasoning = []
    scores = {}

    # --- Step 1: Bandwidth matching ---
    for tech, info in TECH_SIGNATURES.items():
        best_match = 0
        best_bw = 0
        for std_bw in info["bandwidths_khz"]:
            ratio = bw_khz / std_bw if std_bw > 0 else 0
            if abs(ratio - 1.0) <= info["bw_tolerance"]:
                match_score = 1.0 - abs(ratio - 1.0)
                if match_score > best_match:
                    best_match = match_score
                    best_bw = std_bw
        if best_match > 0:
            scores[tech] = {"bw_score": best_match, "matched_bw_khz": best_bw}

    # --- FIX #4: Spectral flatness scoring (UMTS vs LTE vs GSM) ---
    reasoning.append("Spectral flatness: %.3f" % flatness)
    for tech in list(scores.keys()):
        fmin, fmax = TECH_SIGNATURES[tech]["flatness_range"]
        if fmin <= flatness <= fmax:
            # In range — boost
            mid = (fmin + fmax) / 2
            dist = abs(flatness - mid) / ((fmax - fmin) / 2 + 0.01)
            scores[tech]["flatness_score"] = 1.0 - dist * 0.5
            reasoning.append("Flatness %.3f in %s range [%.2f-%.2f] -> boost" % (flatness, tech, fmin, fmax))
        else:
            # Out of range — penalize
            scores[tech]["flatness_score"] = 0.1
            reasoning.append("Flatness %.3f outside %s range [%.2f-%.2f] -> penalize" % (flatness, tech, fmin, fmax))

    # --- Step 2: OFDM CP detection ---
    if samples is not None and sample_rate > 0 and len(samples) >= 1024:
        is_ofdm, ofdm_conf, scs_est = _detect_ofdm(samples, sample_rate)
        reasoning.append("OFDM: %s conf=%.0f%% SCS=%.0fkHz" %
                        (is_ofdm, ofdm_conf * 100, scs_est / 1000 if scs_est else 0))

        for tech in scores:
            info = TECH_SIGNATURES[tech]
            if info["spectral_type"] == "ofdm" and is_ofdm:
                scores[tech]["ofdm_score"] = ofdm_conf
                if scs_est and info["subcarrier_spacing_khz"]:
                    scs_ratio = scs_est / (info["subcarrier_spacing_khz"] * 1000)
                    if 0.7 < scs_ratio < 1.3:
                        scores[tech]["scs_score"] = 1.0 - abs(scs_ratio - 1.0)
            elif info["spectral_type"] == "ofdm" and not is_ofdm:
                scores[tech]["ofdm_score"] = 0.1  # Strong penalty: OFDM expected but not found
            elif info["spectral_type"] != "ofdm" and not is_ofdm:
                scores[tech]["ofdm_score"] = 0.6  # Bonus: correctly non-OFDM
            elif info["spectral_type"] != "ofdm" and is_ofdm:
                scores[tech]["ofdm_score"] = 0.15  # Penalty: shouldn't be OFDM

        # --- FIX #4: TDD detection ---
        is_tdd, tdd_conf = detect_tdd_pattern(samples, sample_rate)
        if is_tdd:
            reasoning.append("TDD pattern detected (conf=%.0f%%)" % (tdd_conf * 100))
            # Boost TDD variants, penalize FDD
            if "LTE_TDD" in scores:
                scores["LTE_TDD"]["tdd_score"] = tdd_conf
            if "LTE_FDD" in scores:
                scores["LTE_FDD"]["tdd_score"] = 0.1  # Penalize FDD if TDD detected
        else:
            reasoning.append("No TDD pattern (continuous power = FDD)")
            if "LTE_FDD" in scores:
                scores["LTE_FDD"]["tdd_score"] = 0.5
            if "LTE_TDD" in scores:
                scores["LTE_TDD"]["tdd_score"] = 0.1
    else:
        is_tdd = False

    # --- Step 3: Band database lookup ---
    band_matches = []
    if abs_center_mhz > 0:
        band_matches = identify_band_by_frequency(abs_center_mhz)
        if band_matches:
            reasoning.append("Freq %.1f MHz -> %d band matches" % (abs_center_mhz, len(band_matches)))
            for bm in band_matches[:3]:
                gen = bm["generation"]
                band_num = bm["band_number"]
                # Cross-validate: if band is TDD-only, boost TDD variant
                is_tdd_band = (band_num in TDD_BANDS_4G or str(band_num) in TDD_BANDS_5G)
                tech_from_gen = {"2G": "GSM", "3G": "UMTS", "4G": "LTE_FDD", "5G": "5G_NR_FR1"}
                if is_tdd_band and gen == "4G":
                    tech_from_gen["4G"] = "LTE_TDD"
                tech = tech_from_gen.get(gen)
                if tech and tech in scores:
                    scores[tech]["band_score"] = 0.8
                    reasoning.append("Band match: %s %s Band %s%s" % (
                        gen, bm["name"], band_num, " (TDD)" if is_tdd_band else ""))

    # --- FIX: 2G gap detection bonus ---
    if sig.is_2g_gap_detection and "GSM" in scores:
        scores["GSM"]["gap_bonus"] = 0.3
        reasoning.append("2G gap detection bonus applied")

    # --- Step 4: Final scoring ---
    if not scores:
        if bw_khz < 500:
            tech_guess = "GSM"
        elif flatness > 0.6 and bw_khz > 3000:
            tech_guess = "UMTS"
        elif bw_khz < 25000:
            tech_guess = "LTE_FDD"
        else:
            tech_guess = "5G_NR_FR1"
        reasoning.append("No strong match; guess %s from BW=%.0fkHz flatness=%.2f" % (tech_guess, bw_khz, flatness))
        return _build_result(tech_guess, 0.3, bw_khz, abs_center_hz, 0, band_matches,
                           reasoning, is_tdd, flatness, sig.is_2g_gap_detection)

    best_tech = None
    best_score = 0
    best_bw = 0
    for tech, ts in scores.items():
        total = (ts.get("bw_score", 0) * 0.25 +
                ts.get("flatness_score", 0) * 0.20 +
                ts.get("ofdm_score", 0) * 0.20 +
                ts.get("scs_score", 0) * 0.10 +
                ts.get("band_score", 0) * 0.10 +
                ts.get("tdd_score", 0) * 0.10 +
                ts.get("gap_bonus", 0) * 0.05)
        reasoning.append("Score %s: %.3f (bw=%.2f flat=%.2f ofdm=%.2f scs=%.2f band=%.2f tdd=%.2f)" % (
            tech, total, ts.get("bw_score", 0), ts.get("flatness_score", 0),
            ts.get("ofdm_score", 0), ts.get("scs_score", 0),
            ts.get("band_score", 0), ts.get("tdd_score", 0)))
        if total > best_score:
            best_score = total
            best_tech = tech
            best_bw = ts.get("matched_bw_khz", 0)

    return _build_result(best_tech, min(best_score, 0.99), bw_khz, abs_center_hz,
                        best_bw, band_matches, reasoning, is_tdd, flatness, sig.is_2g_gap_detection)


def _build_result(tech, confidence, bw_khz, center_hz, matched_bw, band_matches,
                 reasoning, is_tdd=False, flatness=0, is_gap=False):
    gen_map = {"GSM": "2G", "UMTS": "3G", "LTE_FDD": "4G", "LTE_TDD": "4G",
               "5G_NR_FR1": "5G", "5G_NR_FR2": "5G"}
    gen = gen_map.get(tech, "Unknown")
    center_mhz = center_hz / 1e6 if center_hz > 0 else 0

    duplex = "TDD" if (is_tdd or tech == "LTE_TDD") else "FDD"
    tech_display = tech
    if tech in ("LTE_FDD", "LTE_TDD"):
        tech_display = "LTE-%s" % duplex

    hints = {
        "GSM": "grgsm_livemon -f %.6fM | wireshark" % center_mhz,
        "UMTS": "srsUE at fc=%.3f MHz, BW=5MHz, UARFCN lookup needed" % center_mhz,
        "LTE_FDD": "srsRAN fc=%.3f MHz bw=%.0fkHz SCS=15kHz duplex=FDD" % (center_mhz, matched_bw or bw_khz),
        "LTE_TDD": "srsRAN fc=%.3f MHz bw=%.0fkHz SCS=15kHz duplex=TDD" % (center_mhz, matched_bw or bw_khz),
        "5G_NR_FR1": "srsRAN-5G fc=%.3f MHz bw=%.0fkHz SCS=30kHz SSB" % (center_mhz, matched_bw or bw_khz),
        "5G_NR_FR2": "mmWave NR fc=%.3f MHz bw=%.0fMHz SCS=120kHz" % (center_mhz, bw_khz / 1000),
    }

    return ClassificationResult(
        technology=tech_display,
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
        is_tdd=is_tdd or tech == "LTE_TDD",
        spectral_flatness=round(flatness, 3),
        is_gap_detected=is_gap,
    )


def _detect_ofdm(samples, sample_rate):
    """Fast OFDM CP autocorrelation. ~0.3ms."""
    n = min(len(samples), 20000)
    x = samples[:n].astype(np.complex64)

    best_corr = 0.0
    best_fft = 0

    for fft_size in [128, 256, 512, 1024, 2048]:
        if fft_size >= n // 3:
            continue
        cp_len = max(4, int(fft_size * 72 / 2048))
        symbol_len = fft_size + cp_len

        num_syms = min(n // symbol_len, 10)
        if num_syms < 2:
            continue

        offsets = np.arange(num_syms) * symbol_len
        offsets = offsets[offsets + symbol_len <= n]
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
