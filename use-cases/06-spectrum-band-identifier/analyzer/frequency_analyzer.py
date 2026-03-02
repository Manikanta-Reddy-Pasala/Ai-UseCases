"""Frequency analysis - identify bands, compare generations, find overlaps."""

from __future__ import annotations
from bands.spectrum_db import get_all_bands, get_bands_by_generation, identify_band_by_frequency


def get_generation_summary(gen: str) -> dict:
    """Get comprehensive summary of a generation's spectrum allocation."""
    bands = get_bands_by_generation(gen)
    if not bands:
        return {"error": "Unknown generation: " + gen}

    fdd_bands = [b for b in bands if b.duplex == "FDD"]
    tdd_bands = [b for b in bands if b.duplex == "TDD"]
    sdl_bands = [b for b in bands if b.duplex == "SDL"]

    all_freqs = []
    for b in bands:
        all_freqs.extend([b.downlink_low_mhz, b.downlink_high_mhz])
        if b.uplink_low_mhz > 0:
            all_freqs.extend([b.uplink_low_mhz, b.uplink_high_mhz])

    regions = set()
    for b in bands:
        regions.update(b.regions)

    return {
        "generation": gen,
        "total_bands": len(bands),
        "fdd_bands": len(fdd_bands),
        "tdd_bands": len(tdd_bands),
        "sdl_bands": len(sdl_bands),
        "frequency_range_mhz": {"min": min(all_freqs) if all_freqs else 0, "max": max(all_freqs) if all_freqs else 0},
        "regions": sorted(regions),
        "bands": [b.to_dict() for b in bands],
    }


def find_band_overlaps() -> list[dict]:
    """Find frequency overlaps between different generations."""
    all_bands = get_all_bands()
    overlaps = []

    for i, b1 in enumerate(all_bands):
        for b2 in all_bands[i + 1:]:
            if b1.generation == b2.generation:
                continue
            # Check downlink overlap
            dl_overlap = (min(b1.downlink_high_mhz, b2.downlink_high_mhz) -
                         max(b1.downlink_low_mhz, b2.downlink_low_mhz))
            if dl_overlap > 0:
                overlaps.append({
                    "band_1": "%s %s (Band %s)" % (b1.generation, b1.name, b1.band_number),
                    "band_2": "%s %s (Band %s)" % (b2.generation, b2.name, b2.band_number),
                    "overlap_type": "downlink",
                    "overlap_mhz": round(dl_overlap, 2),
                    "range_mhz": "%.1f - %.1f" % (
                        max(b1.downlink_low_mhz, b2.downlink_low_mhz),
                        min(b1.downlink_high_mhz, b2.downlink_high_mhz)),
                })

    # Deduplicate and return top overlaps
    seen = set()
    unique = []
    for o in overlaps:
        key = tuple(sorted([o["band_1"], o["band_2"]]))
        if key not in seen:
            seen.add(key)
            unique.append(o)
    return sorted(unique, key=lambda x: x["overlap_mhz"], reverse=True)[:30]


def compare_generations() -> dict:
    """Compare spectrum allocation across all generations."""
    summary = {}
    for gen in ["2G", "3G", "4G", "5G"]:
        bands = get_bands_by_generation(gen)
        total_spectrum = 0
        for b in bands:
            total_spectrum += b.downlink_bandwidth_mhz
        summary[gen] = {
            "band_count": len(bands),
            "total_downlink_spectrum_mhz": round(total_spectrum, 1),
            "lowest_freq_mhz": min(b.downlink_low_mhz for b in bands) if bands else 0,
            "highest_freq_mhz": max(b.downlink_high_mhz for b in bands) if bands else 0,
            "duplex_modes": list(set(b.duplex for b in bands)),
            "max_channel_bw_mhz": max(max(b.common_bandwidths_mhz) for b in bands if b.common_bandwidths_mhz) if bands else 0,
        }
    return summary


def get_bands_for_region(region: str) -> dict:
    """Get all bands available in a specific region."""
    region_lower = region.lower()
    result = {"2G": [], "3G": [], "4G": [], "5G": []}
    for band in get_all_bands():
        if any(region_lower in r.lower() for r in band.regions):
            result[band.generation].append(band.to_dict())
    return {
        "region": region,
        "total_bands": sum(len(v) for v in result.values()),
        "by_generation": result,
    }
