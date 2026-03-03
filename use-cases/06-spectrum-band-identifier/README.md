# IQ Signal Analyzer & 2G/3G/4G/5G Band Identifier

## Feed IQ Data or Spectrograms → Auto-Detect 2G/3G/4G/5G → Center Frequency for Decoding

Dual-mode signal analyzer: processes **raw IQ samples** from any SDR or **pre-computed spectrograms** (same format as our YOLO production scanner). Detects signals, classifies technology, outputs center frequencies with decoding commands.

**Tested against YOLO ground truth: 58.8% accuracy (10/17 frequencies) — pure DSP, zero training.**

---

### Two Operating Modes

```
MODE 1: Raw IQ Input (any SDR)              MODE 2: Spectrogram Input (YOLO format)
─────────────────────────────                ───────────────────────────────────────
RTL-SDR / HackRF / USRP / .npy              float32 FFT data (dBm power values)
         │                                   Same format as YOLO scanner.py
         ▼                                            │
    IQ Reader (auto-detect format)                    ▼
         │                                   Reshape to (N, 2048)
         ▼                                   Slice [:, 357:1691]
    FFT (2048-pt, Hanning, 8-avg)            Multi-chunk reassembly
         │                                            │
         ▼                                            ▼
    ┌────────────────────────────────────────────────────────┐
    │              SHARED ANALYSIS PIPELINE                   │
    │                                                        │
    │  PASS 1: Detect strong signals (3G/4G/5G)              │
    │    • Threshold = noise_floor + 6dB                     │
    │    • Min bandwidth 500kHz (skip 2G)                    │
    │    • Multi-carrier splitting at valleys                 │
    │    • -3dB bandwidth measurement                        │
    │    • Spectral flatness scoring                         │
    │                                                        │
    │  PASS 2: Detect 2G in GAPS                             │
    │    • Compute gap regions between 3G/4G                 │
    │    • Lower threshold (noise + 3dB)                     │
    │    • Min bandwidth 50kHz (catch 200kHz GSM)            │
    │                                                        │
    │  CLASSIFY each signal:                                 │
    │    • BW matching (200kHz→GSM, 5MHz→UMTS, 10MHz→LTE)   │
    │    • Spectral flatness (CDMA=flat, OFDM=medium)        │
    │    • OFDM cyclic prefix detection (LTE vs UMTS)        │
    │    • TDD power variance detection (FDD vs TDD)         │
    │    • Band DB cross-validation (84 bands, 3GPP)         │
    │    • Separate LTE-FDD and LTE-TDD classes              │
    └────────────────────────────────────────────────────────┘
                         │
                         ▼
    ┌────────────────────────────────────────────────────────┐
    │  OUTPUT per signal:                                    │
    │    Technology:  LTE-FDD (4G)                           │
    │    Center Freq: 1849.5 MHz                             │
    │    Bandwidth:   10 MHz                                 │
    │    SNR:         35.2 dB                                │
    │    Flatness:    0.45 (OFDM)                            │
    │    TDD:         No                                     │
    │    Gap detect:  No                                     │
    │    DECODE:      srsRAN fc=1849.5M bw=10M SCS=15kHz    │
    └────────────────────────────────────────────────────────┘
```

### Performance

| Metric | IQ Mode | Spectrogram Mode |
|--------|---------|------------------|
| Analysis time | **1.2 ms** | **4-28 ms** |
| Accuracy vs YOLO | N/A (different input) | **58.8% (10/17)** |
| Band 3 accuracy | - | **80% (4/5)** |
| Band 8 accuracy | - | **75% (3/4)** |
| YOLO time | - | 170-940 ms |
| Speed advantage | - | **10-50x faster** |

### vs YOLO Production Scanner

```
┌────────────────────┬─────────────┬───────────────┐
│                    │  DSP v3     │  YOLO Scanner │
├────────────────────┼─────────────┼───────────────┤
│ Accuracy           │  58.8%      │  100%         │
│ Speed              │  4-28ms     │  170-940ms    │
│ Memory             │  50 MB      │  1.1 GB       │
│ Training needed    │  None       │  GPU + data   │
│ 2G gap detection   │  Yes (v3)   │  Yes          │
│ Multi-carrier      │  Yes (v3)   │  Yes          │
│ FDD/TDD split      │  Yes (v3)   │  Yes          │
│ Docker image       │  ~200 MB    │  ~3 GB        │
└────────────────────┴─────────────┴───────────────┘
```

### Quick Start

```bash
pip install -r requirements.txt
python3 main.py   # Port 8005

# Analyze spectrogram (YOLO format)
curl -X POST http://localhost:8005/api/v1/analyze/spectrogram \
  -F "file=@sample_vec_B3.dat" \
  -F "center_freq_khz=1845000" \
  -F "bandwidth_khz=80000" \
  -F "num_chunks=7"

# Analyze raw IQ
curl -X POST http://localhost:8005/api/v1/analyze \
  -F "file=@recording.raw" \
  -F "sample_rate=20000000" \
  -F "center_freq=1842500000"

# Generate test signal
curl -X POST "localhost:8005/api/v1/analyze/generate?signal_type=lte&center_freq=1842500000"
```

### Live: http://135.181.93.114:8005

---

**Docs**: [ARCHITECTURE.md](ARCHITECTURE.md) | [IMPLEMENTATION.md](IMPLEMENTATION.md) | [COMPARISON-vs-YOLO.md](COMPARISON-vs-YOLO.md)
