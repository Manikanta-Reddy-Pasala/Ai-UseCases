# IQ Signal Analyzer & 2G/3G/4G/5G Band Identifier

## Feed Raw IQ Data → Auto-Detect Technology → Get Center Frequency for Decoding

Takes raw IQ samples from **any SDR** (RTL-SDR, HackRF, USRP, or file), runs FFT spectral analysis, detects signals, classifies the cellular technology (GSM/UMTS/LTE/5G NR), and outputs the **exact center frequency + decoding command**.

---

### The Pipeline (1.2ms)

```
                    RAW IQ DATA
                    (any format)
                         │
     ┌───────────────────┼───────────────────┐
     │    RTL-SDR        │     HackRF        │     USRP
     │    uint8/int16    │     int8           │     float32/complex64
     │    .npy  .csv     │     .wav           │
     └───────────────────┼───────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │    IQ READER        │  Auto-detect format
              │    Parse → complex64│  Normalize to [-1, 1]
              └──────────┬──────────┘
                         │                          ⏱ 0.1ms
                         ▼
              ┌─────────────────────┐
              │  FFT SPECTRAL       │  Raw numpy FFT (not scipy)
              │  ANALYSIS           │  Hanning window + averaging
              │                     │  2048-pt FFT, 8 frame avg
              │  Output: PSD (dB)   │
              └──────────┬──────────┘
                         │                          ⏱ 0.3ms
                         ▼
              ┌─────────────────────┐
              │  SIGNAL DETECTION   │  Vectorized threshold crossing
              │                     │  Noise floor = 25th percentile
              │  • Find peaks       │  Threshold = noise + 6dB
              │  • Measure BW       │  Power-weighted centroid
              │  • Calc center freq │  for center frequency
              └──────────┬──────────┘
                         │                          ⏱ 0.5ms
                         ▼
              ┌─────────────────────┐
              │  TECHNOLOGY         │  4-stage classification:
              │  CLASSIFIER         │
              │                     │  1. Bandwidth matching
              │  GSM:    200 kHz    │     (vs known standards)
              │  UMTS:   5 MHz      │
              │  LTE:    1.4-20 MHz │  2. OFDM CP detection
              │  5G NR:  5-100 MHz  │     (cyclic prefix corr)
              │  5G FR2: 50-400 MHz │
              │                     │  3. Subcarrier spacing
              │                     │     (15kHz=LTE, 30kHz=NR)
              │                     │
              │                     │  4. Band DB lookup
              │                     │     (84 bands, 3GPP)
              └──────────┬──────────┘
                         │                          ⏱ 0.3ms
                         ▼
     ┌───────────────────────────────────────────┐
     │              OUTPUT                        │
     │                                            │
     │  Technology: LTE (4G)                      │
     │  Confidence: 74%                           │
     │  Center Frequency: 1842.500 MHz            │
     │  Bandwidth: 10 MHz                         │
     │  SNR: 55.6 dB                              │
     │                                            │
     │  DECODE: srsRAN fc=1842.500M bw=10M        │
     │          SCS=15kHz                         │
     └───────────────────────────────────────────┘
                                            Total: ⏱ 1.2ms
```

### Performance

| Metric | Value |
|--------|-------|
| **Analysis pipeline** | **1.2 ms** (FFT + detect + classify) |
| FFT (2048-pt) | 0.3 ms |
| Signal detection | 0.5 ms |
| OFDM + classification | 0.3 ms |
| Real file Band 8 (14MB) | 12 ms (incl. HTTP upload) |
| Real file Band 3 (34MB) | 35 ms (incl. HTTP upload) |

### Supported IQ Formats

| Format | Source | Extension |
|--------|--------|-----------|
| uint8 | RTL-SDR raw | .bin, .raw |
| int16 | RTL-SDR | .dat |
| int8 | HackRF | .cs8, .dat |
| float32 interleaved | USRP, MATLAB | .dat, .bin |
| complex64 | GNU Radio, NumPy | .cf32 |
| NumPy | Python | .npy |
| CSV | Any (I,Q columns) | .csv |
| WAV | SDR#, HDSDR | .wav |

### Tested with Real IQ Data

| Sample | Band | Signals | Center Freq | Time |
|--------|------|---------|-------------|------|
| sample_vec_B3.dat (34MB) | LTE Band 3 | 2 | 1842.500 MHz | 35ms |
| sample_vec_B8.dat (14MB) | LTE Band 8 | 2 | 942.500 MHz | 12ms |
| sample_vec_B1.dat (24MB) | LTE Band 1 | - | 2140 MHz | - |
| sample_vec_B20.dat (9MB) | LTE Band 20 | - | 806 MHz | - |
| sample_vec_B28.dat (19MB) | LTE Band 28 | - | 780.5 MHz | - |

### Quick Start

```bash
pip install -r requirements.txt
python3 main.py   # Port 8005

# Analyze real IQ file
curl -X POST http://localhost:8005/api/v1/analyze \
  -F "file=@sample_vec_B3.dat" \
  -F "sample_rate=30720000" \
  -F "center_freq=1842500000" \
  -F "fmt=float32"

# Generate test signal and analyze
curl -X POST "http://localhost:8005/api/v1/analyze/generate?signal_type=lte&center_freq=1842500000"
```

### Live: http://135.181.93.114:8005

---

**Detailed Docs**: [ARCHITECTURE.md](ARCHITECTURE.md) | [IMPLEMENTATION.md](IMPLEMENTATION.md)
