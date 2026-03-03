# Architecture — 2G/3G/4G/5G Spectrum Band Identifier

## System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     FastAPI Server (:8005)                        │
│                                                                   │
│  GET  /api/v1/bands ─────────────► Full Band Database            │
│  GET  /api/v1/bands/{gen} ───────► Generation Detail             │
│  GET  /api/v1/identify?freq= ───► Frequency Lookup              │
│  GET  /api/v1/search?q= ────────► Text Search                   │
│  GET  /api/v1/compare ──────────► Cross-Gen Comparison           │
│  GET  /api/v1/overlaps ─────────► Overlap Detection              │
│  GET  /api/v1/region/{name} ────► Regional Filter                │
│  GET  /api/v1/stats ────────────► Database Stats                 │
│  GET  / ────────────────────────► Interactive Explorer            │
└────────────────────────────┬─────────────────────────────────────┘
                             │
              ┌──────────────▼──────────────┐
              │     SPECTRUM DATABASE        │
              │                             │
              │  ┌────────────────────────┐ │
              │  │  GSM_BANDS (10)       │ │
              │  │  450-1990 MHz          │ │
              │  │  0.2 MHz channels      │ │
              │  │  FDD only              │ │
              │  ├────────────────────────┤ │
              │  │  UMTS_BANDS (14)      │ │
              │  │  791-2690 MHz          │ │
              │  │  5 MHz channels        │ │
              │  │  FDD only              │ │
              │  ├────────────────────────┤ │
              │  │  LTE_BANDS (34)       │ │
              │  │  462-5925 MHz          │ │
              │  │  1.4-20 MHz channels   │ │
              │  │  FDD + TDD + SDL       │ │
              │  ├────────────────────────┤ │
              │  │  NR_BANDS (26)        │ │
              │  │  617-40000 MHz         │ │
              │  │  5-400 MHz channels    │ │
              │  │  FDD + TDD (FR1+FR2)  │ │
              │  └────────────────────────┘ │
              │                             │
              │  Total: 84 bands            │
              │  Range: 460 MHz - 40 GHz    │
              └─────────────────────────────┘

              ┌─────────────────────────────┐
              │     FREQUENCY ANALYZER      │
              │                             │
              │  identify_band_by_frequency  │
              │  ├── Check DL range          │
              │  ├── Check UL range          │
              │  └── Return all matches      │
              │                             │
              │  get_generation_summary      │
              │  ├── Band count              │
              │  ├── FDD/TDD/SDL split       │
              │  ├── Frequency range          │
              │  └── Regional coverage        │
              │                             │
              │  find_band_overlaps          │
              │  ├── Cross-gen DL overlap    │
              │  ├── Dedup + sort by MHz     │
              │  └── Top 30 overlaps          │
              │                             │
              │  compare_generations         │
              │  ├── Band count              │
              │  ├── Total spectrum           │
              │  ├── Max channel BW           │
              │  └── Frequency range          │
              └─────────────────────────────┘
```

## Band Data Model

```
┌─────────────────────────────────────────────────────────┐
│                    Band Object                           │
│                                                          │
│  band_number: int|str     (1, "n78", "n257")            │
│  name: str                ("C-Band", "IMT", "mmWave")   │
│  generation: str          ("2G", "3G", "4G", "5G")      │
│                                                          │
│  ┌──────────────────────────────────────────┐           │
│  │ Uplink                                   │           │
│  │  low_mhz ──────────── high_mhz          │           │
│  │           mid_mhz ↑                      │           │
│  │       (auto-calculated)                   │           │
│  └──────────────────────────────────────────┘           │
│                                                          │
│  ┌──────────────────────────────────────────┐           │
│  │ Downlink                                 │           │
│  │  low_mhz ──────────── high_mhz          │           │
│  │           mid_mhz ↑                      │           │
│  │       (auto-calculated)                   │           │
│  └──────────────────────────────────────────┘           │
│                                                          │
│  duplex: FDD | TDD | SDL                                │
│  duplex_spacing_mhz: (auto: DL_low - UL_low)           │
│                                                          │
│  Computed Properties:                                    │
│  ├── uplink_mid_mhz:    (UL_low + UL_high) / 2         │
│  ├── downlink_mid_mhz:  (DL_low + DL_high) / 2         │
│  ├── uplink_bandwidth:   UL_high - UL_low               │
│  ├── downlink_bandwidth: DL_high - DL_low               │
│  └── frequency_category:                                 │
│       < 1 GHz  → "Low Band (sub-1GHz)"                  │
│       1-3 GHz  → "Mid Band (1-3GHz)"                    │
│       3-6 GHz  → "High Mid Band (3-6GHz)"               │
│       6-24 GHz → "High Band (6-24GHz)"                  │
│       24+ GHz  → "mmWave (24GHz+)"                      │
└─────────────────────────────────────────────────────────┘
```

## Spectrum Landscape

```
Frequency (MHz)
│
│  2G ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
│     450    900  1800 1900
│
│  3G ░░░░████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
│         800   1900  2100  2600
│
│  4G ░░████████████████████████████░░░░░░░░░░░░░░░░░░░░░
│     450  700  900  1800  2300  2600  3500  5925
│
│  5G ░░░░████████████████████████████████████████████████
│       600  900  1800  2500  3500  4500  5925   28G  40G
│     ├─────────────────────┤├────────────┤├──────────────┤
│          FR1: sub-6GHz          |         FR2: mmWave
│
└──────────────────────────────────────────────────────── MHz
  0   1000  2000  3000  4000  5000  6000    28000    40000
```

## 3GPP Specification Sources

| Generation | Spec | Content |
|-----------|------|---------|
| 2G (GSM) | TS 45.005 | Radio transmission and reception |
| 3G (UMTS) | TS 25.101 | UE radio transmission and reception (FDD) |
| 4G (LTE) | TS 36.101 | E-UTRA UE radio transmission and reception |
| 5G (NR) | TS 38.101 | NR UE radio transmission and reception |
