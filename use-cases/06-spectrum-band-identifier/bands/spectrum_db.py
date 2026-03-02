"""Complete 2G/3G/4G/5G spectrum band database.

Comprehensive database of all cellular frequency bands worldwide including:
- Band number, name, generation (2G/3G/4G/5G)
- Uplink and Downlink frequency ranges
- Mid-frequency (center) calculations
- Duplex mode (FDD/TDD/SDL)
- Channel bandwidth
- Common regional deployments
- 3GPP specification references

Sources: 3GPP TS 36.101 (LTE), TS 38.101 (NR), TS 25.101 (UMTS), TS 45.005 (GSM)
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Band:
    band_number: int | str
    name: str
    generation: str  # 2G, 3G, 4G, 5G
    uplink_low_mhz: float
    uplink_high_mhz: float
    downlink_low_mhz: float
    downlink_high_mhz: float
    duplex: str  # FDD, TDD, SDL
    common_bandwidths_mhz: list[float] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    notes: str = ""

    @property
    def uplink_mid_mhz(self) -> float:
        return round((self.uplink_low_mhz + self.uplink_high_mhz) / 2, 2)

    @property
    def downlink_mid_mhz(self) -> float:
        return round((self.downlink_low_mhz + self.downlink_high_mhz) / 2, 2)

    @property
    def uplink_bandwidth_mhz(self) -> float:
        return round(self.uplink_high_mhz - self.uplink_low_mhz, 2)

    @property
    def downlink_bandwidth_mhz(self) -> float:
        return round(self.downlink_high_mhz - self.downlink_low_mhz, 2)

    @property
    def duplex_spacing_mhz(self) -> float:
        if self.duplex == "TDD":
            return 0
        return round(self.downlink_low_mhz - self.uplink_low_mhz, 2)

    @property
    def frequency_category(self) -> str:
        mid = self.downlink_mid_mhz
        if mid < 1000:
            return "Low Band (sub-1GHz)"
        elif mid < 3000:
            return "Mid Band (1-3GHz)"
        elif mid < 6000:
            return "High Mid Band (3-6GHz)"
        elif mid < 24000:
            return "High Band (6-24GHz)"
        else:
            return "mmWave (24GHz+)"

    def to_dict(self) -> dict:
        return {
            "band_number": self.band_number,
            "name": self.name,
            "generation": self.generation,
            "uplink_mhz": {"low": self.uplink_low_mhz, "high": self.uplink_high_mhz, "mid": self.uplink_mid_mhz, "bandwidth": self.uplink_bandwidth_mhz},
            "downlink_mhz": {"low": self.downlink_low_mhz, "high": self.downlink_high_mhz, "mid": self.downlink_mid_mhz, "bandwidth": self.downlink_bandwidth_mhz},
            "duplex": self.duplex,
            "duplex_spacing_mhz": self.duplex_spacing_mhz,
            "frequency_category": self.frequency_category,
            "common_bandwidths_mhz": self.common_bandwidths_mhz,
            "regions": self.regions,
            "notes": self.notes,
        }


# =============================================================================
# 2G (GSM) BANDS
# =============================================================================
GSM_BANDS = [
    Band(0, "GSM-450", "2G", 450.4, 457.6, 460.4, 467.6, "FDD", [0.2], ["Europe (rare)"], "Band 450 - historical"),
    Band(0, "GSM-480", "2G", 478.8, 486.0, 488.8, 496.0, "FDD", [0.2], ["Europe (rare)"], "Band 480 - historical"),
    Band(0, "GSM-710", "2G", 698.0, 716.0, 728.0, 746.0, "FDD", [0.2], ["Americas"], "Band 710"),
    Band(0, "GSM-750", "2G", 747.0, 762.0, 777.0, 792.0, "FDD", [0.2], ["Americas"], "Band 750"),
    Band(0, "GSM-850", "2G", 824.0, 849.0, 869.0, 894.0, "FDD", [0.2], ["Americas", "Asia Pacific"], "Most common 850MHz GSM"),
    Band(0, "P-GSM-900", "2G", 890.0, 915.0, 935.0, 960.0, "FDD", [0.2], ["Europe", "Asia", "Africa", "Middle East"], "Primary GSM 900"),
    Band(0, "E-GSM-900", "2G", 880.0, 915.0, 925.0, 960.0, "FDD", [0.2], ["Europe", "Asia", "Africa", "Middle East"], "Extended GSM 900"),
    Band(0, "R-GSM-900", "2G", 876.0, 915.0, 921.0, 960.0, "FDD", [0.2], ["Europe"], "Railway GSM 900"),
    Band(0, "DCS-1800", "2G", 1710.0, 1785.0, 1805.0, 1880.0, "FDD", [0.2], ["Europe", "Asia", "Africa", "Middle East"], "GSM 1800 - most widely used globally"),
    Band(0, "PCS-1900", "2G", 1850.0, 1910.0, 1930.0, 1990.0, "FDD", [0.2], ["Americas"], "GSM 1900 - Americas only"),
]

# =============================================================================
# 3G (UMTS/WCDMA) BANDS
# =============================================================================
UMTS_BANDS = [
    Band(1, "IMT", "3G", 1920.0, 1980.0, 2110.0, 2170.0, "FDD", [5], ["Global"], "Primary 3G band worldwide"),
    Band(2, "PCS", "3G", 1850.0, 1910.0, 1930.0, 1990.0, "FDD", [5], ["Americas"], "PCS 1900"),
    Band(3, "DCS", "3G", 1710.0, 1785.0, 1805.0, 1880.0, "FDD", [5], ["Europe", "Asia"], "1800MHz"),
    Band(4, "AWS-1", "3G", 1710.0, 1755.0, 2110.0, 2155.0, "FDD", [5], ["Americas"], "AWS 1700/2100"),
    Band(5, "CLR", "3G", 824.0, 849.0, 869.0, 894.0, "FDD", [5], ["Americas", "Asia Pacific"], "850MHz"),
    Band(6, "UMTS-800", "3G", 830.0, 840.0, 875.0, 885.0, "FDD", [5], ["Japan"], "Japan 800MHz"),
    Band(7, "IMT-E", "3G", 2500.0, 2570.0, 2620.0, 2690.0, "FDD", [5], ["Europe", "Asia"], "2600MHz"),
    Band(8, "GSM-900", "3G", 880.0, 915.0, 925.0, 960.0, "FDD", [5], ["Europe", "Asia", "Africa"], "900MHz UMTS"),
    Band(9, "UMTS-1700", "3G", 1749.9, 1784.9, 1844.9, 1879.9, "FDD", [5], ["Japan"], "Japan 1700MHz"),
    Band(10, "EAWS", "3G", 1710.0, 1770.0, 2110.0, 2170.0, "FDD", [5], ["Americas"], "Extended AWS"),
    Band(11, "LPDC", "3G", 1427.9, 1447.9, 1475.9, 1495.9, "FDD", [5], ["Japan"], "Japan 1500MHz"),
    Band(19, "UMTS-800", "3G", 830.0, 845.0, 875.0, 890.0, "FDD", [5], ["Japan"], "Japan 800MHz lower"),
    Band(20, "EU-DD", "3G", 832.0, 862.0, 791.0, 821.0, "FDD", [5], ["Europe"], "800MHz Digital Dividend"),
    Band(21, "UMTS-1500", "3G", 1447.9, 1462.9, 1495.9, 1510.9, "FDD", [5], ["Japan"], "Japan 1500MHz upper"),
]

# =============================================================================
# 4G (LTE) BANDS - 3GPP TS 36.101
# =============================================================================
LTE_BANDS = [
    # FDD Bands
    Band(1, "IMT", "4G", 1920.0, 1980.0, 2110.0, 2170.0, "FDD", [5, 10, 15, 20], ["Global"], "Primary global LTE band"),
    Band(2, "PCS", "4G", 1850.0, 1910.0, 1930.0, 1990.0, "FDD", [5, 10, 15, 20], ["Americas"], "PCS 1900"),
    Band(3, "DCS", "4G", 1710.0, 1785.0, 1805.0, 1880.0, "FDD", [5, 10, 15, 20], ["Europe", "Asia", "Middle East"], "1800MHz - most deployed LTE band globally"),
    Band(4, "AWS-1", "4G", 1710.0, 1755.0, 2110.0, 2155.0, "FDD", [5, 10, 15, 20], ["Americas"], "AWS 1700/2100"),
    Band(5, "CLR", "4G", 824.0, 849.0, 869.0, 894.0, "FDD", [5, 10], ["Americas", "Asia Pacific"], "850MHz"),
    Band(7, "IMT-E", "4G", 2500.0, 2570.0, 2620.0, 2690.0, "FDD", [5, 10, 15, 20], ["Europe", "Asia", "Americas"], "2600MHz - high capacity urban"),
    Band(8, "E-GSM", "4G", 880.0, 915.0, 925.0, 960.0, "FDD", [5, 10], ["Europe", "Asia", "Africa", "Middle East"], "900MHz LTE"),
    Band(11, "LPDC", "4G", 1427.9, 1447.9, 1475.9, 1495.9, "FDD", [5, 10], ["Japan"], "Japan 1500MHz"),
    Band(12, "LSMH-A", "4G", 699.0, 716.0, 729.0, 746.0, "FDD", [5, 10], ["Americas"], "700MHz lower A/B/C"),
    Band(13, "LSMH-C", "4G", 777.0, 787.0, 746.0, 756.0, "FDD", [10], ["Americas"], "700MHz upper C - Verizon"),
    Band(14, "LSMH-D", "4G", 788.0, 798.0, 758.0, 768.0, "FDD", [10], ["Americas"], "700MHz - FirstNet public safety"),
    Band(17, "LSMH-BC", "4G", 704.0, 716.0, 734.0, 746.0, "FDD", [5, 10], ["Americas"], "700MHz lower B/C - AT&T"),
    Band(18, "UMTS-800L", "4G", 815.0, 830.0, 860.0, 875.0, "FDD", [5, 10, 15], ["Japan"], "Japan 800MHz lower"),
    Band(19, "UMTS-800U", "4G", 830.0, 845.0, 875.0, 890.0, "FDD", [5, 10, 15], ["Japan"], "Japan 800MHz upper"),
    Band(20, "EU-DD", "4G", 832.0, 862.0, 791.0, 821.0, "FDD", [5, 10, 15, 20], ["Europe", "Middle East", "Africa"], "800MHz Digital Dividend - EU coverage"),
    Band(21, "LPDC-UP", "4G", 1447.9, 1462.9, 1495.9, 1510.9, "FDD", [5, 10, 15], ["Japan"], "Japan 1500MHz upper"),
    Band(24, "L-Band", "4G", 1626.5, 1660.5, 1525.0, 1559.0, "FDD", [5, 10], ["Americas"], "L-Band"),
    Band(25, "EPCS", "4G", 1850.0, 1915.0, 1930.0, 1995.0, "FDD", [5, 10, 15, 20], ["Americas"], "Extended PCS"),
    Band(26, "ECLR", "4G", 814.0, 849.0, 859.0, 894.0, "FDD", [5, 10, 15], ["Americas"], "Extended CLR 850MHz"),
    Band(28, "APT-700", "4G", 703.0, 748.0, 758.0, 803.0, "FDD", [5, 10, 15, 20], ["Asia Pacific", "Latin America", "Middle East"], "700MHz APT - wide adoption"),
    Band(29, "LSMH-SDL", "4G", 0, 0, 717.0, 728.0, "SDL", [5, 10], ["Americas"], "700MHz SDL - downlink only"),
    Band(30, "WCS", "4G", 2305.0, 2315.0, 2350.0, 2360.0, "FDD", [5, 10], ["Americas"], "WCS 2300MHz"),
    Band(31, "NMT-450", "4G", 452.5, 457.5, 462.5, 467.5, "FDD", [1.4, 3, 5], ["Americas"], "450MHz"),
    Band(32, "L-Band-SDL", "4G", 0, 0, 1452.0, 1496.0, "SDL", [5, 10, 15, 20], ["Europe"], "1500MHz SDL - supplemental DL"),
    Band(38, "IMT-E-TDD", "4G", 2570.0, 2620.0, 2570.0, 2620.0, "TDD", [5, 10, 15, 20], ["Europe", "Asia"], "2600MHz TDD"),
    Band(39, "DCS-TDD", "4G", 1880.0, 1920.0, 1880.0, 1920.0, "TDD", [5, 10, 15, 20], ["China"], "1900MHz TDD - TD-SCDMA refarmed"),
    Band(40, "S-Band", "4G", 2300.0, 2400.0, 2300.0, 2400.0, "TDD", [5, 10, 15, 20], ["China", "India", "Asia"], "2300MHz TDD - heavily used in India/China"),
    Band(41, "BRS", "4G", 2496.0, 2690.0, 2496.0, 2690.0, "TDD", [5, 10, 15, 20], ["Americas", "Asia", "Global"], "2500MHz TDD - T-Mobile/Sprint US, China"),
    Band(42, "CBRS", "4G", 3400.0, 3600.0, 3400.0, 3600.0, "TDD", [5, 10, 15, 20], ["Europe", "Asia", "Middle East"], "3.5GHz TDD - early 5G-like band"),
    Band(43, "C-Band-TDD", "4G", 3600.0, 3800.0, 3600.0, 3800.0, "TDD", [5, 10, 15, 20], ["Europe", "Asia"], "3.7GHz TDD"),
    Band(46, "LAA", "4G", 5150.0, 5925.0, 5150.0, 5925.0, "TDD", [10, 20], ["Global"], "5GHz unlicensed - LAA/LTE-U"),
    Band(48, "CBRS", "4G", 3550.0, 3700.0, 3550.0, 3700.0, "TDD", [5, 10, 15, 20], ["Americas"], "3.5GHz CBRS - US shared spectrum"),
    Band(66, "AWS-3", "4G", 1710.0, 1780.0, 2110.0, 2200.0, "FDD", [5, 10, 15, 20], ["Americas"], "Extended AWS - includes AWS-1 + AWS-3"),
    Band(71, "600MHz", "4G", 663.0, 698.0, 617.0, 652.0, "FDD", [5, 10, 15, 20], ["Americas"], "600MHz - T-Mobile US rural coverage"),
]

# =============================================================================
# 5G NR BANDS - 3GPP TS 38.101
# =============================================================================
NR_BANDS = [
    # FR1: Sub-6 GHz
    Band("n1", "IMT", "5G", 1920.0, 1980.0, 2110.0, 2170.0, "FDD", [5, 10, 15, 20], ["Global"], "Primary 5G FDD band"),
    Band("n2", "PCS", "5G", 1850.0, 1910.0, 1930.0, 1990.0, "FDD", [5, 10, 15, 20], ["Americas"], "PCS 1900 5G"),
    Band("n3", "DCS", "5G", 1710.0, 1785.0, 1805.0, 1880.0, "FDD", [5, 10, 15, 20, 25, 30], ["Europe", "Asia", "Middle East"], "1800MHz 5G - widely deployed"),
    Band("n5", "CLR", "5G", 824.0, 849.0, 869.0, 894.0, "FDD", [5, 10, 15, 20], ["Americas"], "850MHz NR"),
    Band("n7", "IMT-E", "5G", 2500.0, 2570.0, 2620.0, 2690.0, "FDD", [5, 10, 15, 20], ["Europe", "Asia"], "2600MHz NR"),
    Band("n8", "E-GSM", "5G", 880.0, 915.0, 925.0, 960.0, "FDD", [5, 10, 15, 20], ["Europe", "Asia", "Africa"], "900MHz NR - rural coverage"),
    Band("n12", "LSMH-A", "5G", 699.0, 716.0, 729.0, 746.0, "FDD", [5, 10, 15], ["Americas"], "700MHz NR"),
    Band("n14", "FirstNet", "5G", 788.0, 798.0, 758.0, 768.0, "FDD", [10], ["Americas"], "FirstNet 5G public safety"),
    Band("n20", "EU-DD", "5G", 832.0, 862.0, 791.0, 821.0, "FDD", [5, 10, 15, 20], ["Europe", "Middle East"], "800MHz NR - EU coverage"),
    Band("n25", "EPCS", "5G", 1850.0, 1915.0, 1930.0, 1995.0, "FDD", [5, 10, 15, 20], ["Americas"], "Extended PCS NR"),
    Band("n28", "APT-700", "5G", 703.0, 748.0, 758.0, 803.0, "FDD", [5, 10, 15, 20, 30], ["Asia Pacific", "Middle East", "Latin America"], "700MHz APT 5G"),
    Band("n38", "IMT-E-TDD", "5G", 2570.0, 2620.0, 2570.0, 2620.0, "TDD", [10, 15, 20], ["Europe", "Asia"], "2600MHz TDD NR"),
    Band("n40", "S-Band", "5G", 2300.0, 2400.0, 2300.0, 2400.0, "TDD", [10, 15, 20, 40, 50], ["China", "India"], "2300MHz TDD NR"),
    Band("n41", "BRS", "5G", 2496.0, 2690.0, 2496.0, 2690.0, "TDD", [10, 15, 20, 40, 50, 60, 80, 100], ["Americas", "Asia", "Global"], "2500MHz TDD - T-Mobile US primary 5G mid-band"),
    Band("n46", "LAA-NR", "5G", 5150.0, 5925.0, 5150.0, 5925.0, "TDD", [20, 40, 60, 80], ["Global"], "5GHz NR-U unlicensed"),
    Band("n48", "CBRS-NR", "5G", 3550.0, 3700.0, 3550.0, 3700.0, "TDD", [10, 15, 20, 40], ["Americas"], "3.5GHz CBRS 5G"),
    Band("n66", "AWS-3", "5G", 1710.0, 1780.0, 2110.0, 2200.0, "FDD", [5, 10, 15, 20, 40], ["Americas"], "Extended AWS NR"),
    Band("n70", "AWS-4", "5G", 1695.0, 1710.0, 1995.0, 2020.0, "FDD", [5, 10, 15, 20, 25], ["Americas"], "AWS-4 supplemental"),
    Band("n71", "600MHz", "5G", 663.0, 698.0, 617.0, 652.0, "FDD", [5, 10, 15, 20], ["Americas"], "600MHz NR - T-Mobile nationwide coverage"),
    Band("n77", "C-Band", "5G", 3300.0, 4200.0, 3300.0, 4200.0, "TDD", [10, 15, 20, 40, 50, 60, 80, 100], ["Global"], "3.3-4.2GHz C-Band - primary global 5G mid-band"),
    Band("n78", "C-Band", "5G", 3300.0, 3800.0, 3300.0, 3800.0, "TDD", [10, 15, 20, 40, 50, 60, 80, 100], ["Europe", "Asia", "Middle East", "Africa"], "3.5GHz - MOST deployed 5G band worldwide"),
    Band("n79", "C-Band-UP", "5G", 4400.0, 5000.0, 4400.0, 5000.0, "TDD", [40, 50, 60, 80, 100], ["Japan", "China"], "4.5GHz - Japan/China 5G"),
    # FR2: mmWave
    Band("n257", "mmWave-28", "5G", 26500.0, 29500.0, 26500.0, 29500.0, "TDD", [50, 100, 200, 400], ["Americas", "Asia", "Europe"], "28GHz mmWave - high capacity urban"),
    Band("n258", "mmWave-26", "5G", 24250.0, 27500.0, 24250.0, 27500.0, "TDD", [50, 100, 200, 400], ["Europe", "Asia"], "26GHz mmWave"),
    Band("n260", "mmWave-39", "5G", 37000.0, 40000.0, 37000.0, 40000.0, "TDD", [50, 100, 200, 400], ["Americas"], "39GHz mmWave - Verizon US"),
    Band("n261", "mmWave-28L", "5G", 27500.0, 28350.0, 27500.0, 28350.0, "TDD", [50, 100, 200, 400], ["Americas"], "28GHz mmWave lower - US specific"),
]


def get_all_bands() -> list[Band]:
    """Get all bands across all generations."""
    return GSM_BANDS + UMTS_BANDS + LTE_BANDS + NR_BANDS


def get_bands_by_generation(gen: str) -> list[Band]:
    """Get bands for a specific generation."""
    gen_map = {"2G": GSM_BANDS, "3G": UMTS_BANDS, "4G": LTE_BANDS, "5G": NR_BANDS}
    return gen_map.get(gen.upper(), [])


def identify_band_by_frequency(freq_mhz: float) -> list[dict]:
    """Identify which band(s) a given frequency belongs to."""
    matches = []
    for band in get_all_bands():
        # Check downlink
        if band.downlink_low_mhz <= freq_mhz <= band.downlink_high_mhz:
            matches.append({**band.to_dict(), "match_type": "downlink",
                           "offset_from_center_mhz": round(freq_mhz - band.downlink_mid_mhz, 2)})
        # Check uplink
        if band.uplink_low_mhz <= freq_mhz <= band.uplink_high_mhz:
            matches.append({**band.to_dict(), "match_type": "uplink",
                           "offset_from_center_mhz": round(freq_mhz - band.uplink_mid_mhz, 2)})
    return matches


def search_bands(query: str) -> list[dict]:
    """Search bands by name, region, or notes."""
    query_lower = query.lower()
    results = []
    for band in get_all_bands():
        if (query_lower in band.name.lower() or
            query_lower in band.notes.lower() or
            query_lower in band.generation.lower() or
            any(query_lower in r.lower() for r in band.regions)):
            results.append(band.to_dict())
    return results
