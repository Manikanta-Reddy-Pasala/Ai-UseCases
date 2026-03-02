# Use Case 6: 2G/3G/4G/5G Spectrum Band Identifier

## Complete Cellular Frequency Band Database

Comprehensive tool for identifying, comparing, and exploring all cellular frequency bands from 2G GSM through 5G NR mmWave. Built from 3GPP specifications (TS 36.101, TS 38.101, TS 25.101, TS 45.005).

## Database Coverage

| Generation | Bands | Frequency Range | Max Channel BW | Key Bands |
|-----------|-------|-----------------|----------------|-----------|
| **2G (GSM)** | 10 | 450 - 1990 MHz | 200 kHz | GSM-900, DCS-1800, PCS-1900 |
| **3G (UMTS)** | 14 | 791 - 2690 MHz | 5 MHz | Band 1 (IMT), Band 8 (900) |
| **4G (LTE)** | 34 | 462 - 5925 MHz | 20 MHz | Band 3, 7, 20, 28, 41, 42 |
| **5G (NR)** | 26 | 617 - 40000 MHz | 400 MHz | n77, n78, n257, n258, n260 |
| **Total** | **84 bands** | **460 MHz - 40 GHz** | | |

## Features

- **Frequency Identification**: Enter any frequency in MHz, get all matching bands across all generations
- **Generation Comparison**: Side-by-side comparison of 2G/3G/4G/5G spectrum
- **Mid-Frequency Calculation**: Automatic center frequency for every band
- **Regional Filtering**: Find bands deployed in Middle East, Europe, Americas, Asia
- **Overlap Detection**: Cross-generation frequency overlap analysis
- **Search**: Search by band name, region, or description

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/bands` | All 84 bands |
| GET | `/api/v1/bands/{gen}` | Bands by generation |
| GET | `/api/v1/identify?freq=3500` | Identify band by frequency |
| GET | `/api/v1/search?q=mmWave` | Search bands |
| GET | `/api/v1/compare` | Compare generations |
| GET | `/api/v1/overlaps` | Cross-gen overlaps |
| GET | `/api/v1/region/{name}` | Regional bands |
| GET | `/` | Interactive explorer |

## Example: 3500 MHz Identification

```
GET /api/v1/identify?freq=3500

→ 6 matches:
  4G Band 42 (CBRS) - mid: 3500.0 MHz
  5G Band n77 (C-Band) - mid: 3750.0 MHz
  5G Band n78 (C-Band) - mid: 3550.0 MHz  ← Most deployed 5G band worldwide
```

## Middle East Bands

```
2G: GSM-900, E-GSM-900, DCS-1800
4G: Band 3 (1800), Band 8 (900), Band 20 (800), Band 28 (700), Band 42 (3500)
5G: n3 (1800), n20 (800), n28 (700), n78 (3500 C-Band)
```

## Quick Start
```bash
pip install -r requirements.txt
python3 main.py    # Port 8005
# Open http://localhost:8005
```

## Tested & Running
```
VM: 135.181.93.114:8005
84 bands loaded (10 GSM + 14 UMTS + 34 LTE + 26 NR)
Frequency range: 460 MHz to 40 GHz
3GPP compliant band definitions
```
