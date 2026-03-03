# Comparison: Use Case 6 (FFT/DSP) vs Ultralytics YOLO Scanner

## Head-to-Head

```
┌────────────────────────────┬──────────────────────────┬───────────────────────────┐
│                            │  USE CASE 6 (FFT/DSP)    │  ULTRALYTICS YOLO         │
│                            │  This project             │  scanner.py (production)  │
├────────────────────────────┼──────────────────────────┼───────────────────────────┤
│  APPROACH                  │  Signal processing       │  Computer vision          │
│                            │  FFT → PSD → threshold   │  Spectrogram → image →    │
│                            │  → BW match → classify   │  YOLO object detection    │
├────────────────────────────┼──────────────────────────┼───────────────────────────┤
│  INPUT                     │  Raw IQ samples          │  Pre-computed spectrogram │
│                            │  (complex64)             │  (float32 FFT data)       │
├────────────────────────────┼──────────────────────────┼───────────────────────────┤
│  ANALYSIS TIME             │  1.2 ms                  │  170-940 ms               │
│  (core inference)          │                          │                           │
├────────────────────────────┼──────────────────────────┼───────────────────────────┤
│  MODELS                    │  None (rule-based)       │  2 YOLO models:           │
│                            │                          │  • YOLOv12n (3G/4G .pt)   │
│                            │                          │  • YOLO11n (2G OpenVINO)  │
├────────────────────────────┼──────────────────────────┼───────────────────────────┤
│  MEMORY                    │  ~50 MB                  │  ~800-1100 MB             │
│                            │  (numpy only)            │  (PyTorch + OpenVINO +    │
│                            │                          │   Ultralytics + models)   │
├────────────────────────────┼──────────────────────────┼───────────────────────────┤
│  DEPENDENCIES              │  numpy, scipy            │  torch, ultralytics,      │
│                            │  (2 packages)            │  openvino, onnxruntime,   │
│                            │                          │  opencv, protobuf (7+)    │
├────────────────────────────┼──────────────────────────┼───────────────────────────┤
│  ACCURACY                  │  Moderate                │  HIGH                     │
│  (see detail below)        │  BW-based heuristics     │  Trained on real data     │
├────────────────────────────┼──────────────────────────┼───────────────────────────┤
│  PROTOCOL                  │  HTTP REST (FastAPI)     │  TCP socket (protobuf)    │
├────────────────────────────┼──────────────────────────┼───────────────────────────┤
│  GPU REQUIRED              │  No                      │  No (CPU inference)       │
├────────────────────────────┼──────────────────────────┼───────────────────────────┤
│  DOCKER IMAGE              │  ~200 MB                 │  ~3+ GB                   │
└────────────────────────────┴──────────────────────────┴───────────────────────────┘
```

## Why YOLO is Better (for Production)

### 1. Accuracy: Trained on Real-World Data

```
YOLO:
  • 2G model trained on thousands of real GSM spectrograms
  • 3G/4G model distinguishes UMTS, LTE-FDD, LTE-TDD (3 classes)
  • Handles weak signals, overlapping signals, fading, interference
  • Detects patterns humans labeled — not just threshold crossings
  • 2G detection in GAPS between 3G/4G (smart exclusion pipeline)

FFT/DSP (Use Case 6):
  • Detects ANY signal above noise floor — not just cellular
  • Cannot distinguish LTE-FDD from LTE-TDD (same BW)
  • Struggles with weak signals near noise floor
  • No training data — pure heuristic rules
  • OFDM CP detection works for strong signals only
```

### 2. The Killer Feature: 2G in Gaps

```
YOLO scanner has a 2-pass pipeline:

Pass 1: Detect 3G/4G (strong, wide signals)
  ┌─────────────────────────────────────────────────────┐
  │   ████ 4G ████    ████ 4G ████    ████ 3G ████     │
  │                                                      │
  │   ↑ detected      ↑ detected      ↑ detected        │
  └─────────────────────────────────────────────────────┘

Pass 2: Extract GAP regions, run 2G model on gaps only
  ┌─────────────────────────────────────────────────────┐
  │   ████ 4G ████ ▒▒GAP▒▒ ████ 4G ████ ▒▒GAP▒▒       │
  │                 ↑ run 2G          ↑ run 2G           │
  │                 model here        model here          │
  └─────────────────────────────────────────────────────┘

This is BRILLIANT because:
  • 2G signals (200kHz) are TINY next to 4G (10MHz+)
  • YOLO finds them by visual pattern in the spectrogram gaps
  • FFT threshold detection often misses them or misclassifies

Use Case 6 has NO equivalent to this gap-based detection.
```

### 3. Visual Pattern Recognition vs Signal Processing

```
YOLO sees this spectrogram as an IMAGE:
  ┌──────────────────────────────────────────┐
  │ ░░░░░████████░░░░░░██████████░░░░░░░░░░ │  ← time axis
  │ ░░░░░████████░░░░░░██████████░░░░░░░░░░ │
  │ ░░░░░████████░░░░░░██████████░░░░░░░░░░ │
  │ ░░░░░████████░░░░▓▓██████████░░░░░░░░░░ │  ← ▓▓ = weak 2G
  │ ░░░░░████████░░░░▓▓██████████░░░░░░░░░░ │
  └──────────────────────────────────────────┘
    ← frequency axis →

  YOLO detects:
  • Shape: rectangular block = 4G carrier
  • Width in pixels → bandwidth → technology
  • Brightness pattern → signal characteristics
  • Tiny bright spot in gap → 2G carrier

FFT/DSP (Use Case 6) sees this as 1D power spectrum:
  ┌──────────────────────────────────────────┐
  │            ╱╲         ╱╲                 │
  │           ╱  ╲       ╱  ╲                │
  │──────────╱────╲─────╱────╲───────────── │ ← noise floor
  └──────────────────────────────────────────┘

  Only sees peaks above threshold — misses the 2G.
```

### 4. Frequency Accuracy

```
YOLO test expectations (from test_scanner_ai_script.py):

Band 1:  4G=[2165.0, 2146.7]  3G=[2116.4, 2137.7]  2G=[]
Band 3:  4G=[1815.0, 1870.0, 1849.5]  3G=[]  2G=[1860.2, 1842.6]
Band 8:  4G=[]  3G=[932.6, 937.2, 927.5]  2G=[953.4]
Band 20: 4G=[813.6, 798.5]  3G=[]  2G=[]
Band 28: 4G=[763.1, 800.8]  3G=[]  2G=[]
Band 40: 4G=[2342.1, 2312.5, 2361.9]  3G=[]  2G=[2352.8]

Tolerance: ±2.0 MHz — YOLO hits this consistently

Use Case 6 on same data:
Band 3:  center=1842.500 MHz (vs expected 1842.6) ✓ close
Band 8:  center=942.500 MHz (vs expected 932.6-953.4) — just center, no separation

YOLO detects MULTIPLE distinct carriers per band.
Use Case 6 detects broader signal regions.
```

## Why Use Case 6 is Better (for Some Things)

### 1. Speed: 700x Faster

```
                    Use Case 6          YOLO Scanner
Band 8 (14MB):     12 ms               170 ms          14x
Band 3 (34MB):     35 ms               940 ms          27x
Analysis only:     1.2 ms              ~200-900 ms     ~700x

For real-time spectrum monitoring where you need to scan
thousands of frequencies per second, FFT/DSP wins massively.
```

### 2. No Training Required

```
YOLO needs:
  • Labeled spectrogram datasets (thousands of images)
  • GPU training time (hours to days)
  • Per-region model tuning (different operators = different patterns)
  • Model versioning, retraining pipeline

FFT/DSP needs:
  • 3GPP standard bandwidth values (public knowledge)
  • Physics-based rules (OFDM CP detection, BW matching)
  • Zero training, works on any band immediately
```

### 3. Lightweight Deployment

```
Use Case 6:                 YOLO Scanner:
  Docker: ~200 MB             Docker: ~3+ GB
  RAM: ~50 MB                 RAM: ~800-1100 MB
  CPU: any                    CPU: needs compute for PyTorch
  Deps: numpy, scipy          Deps: torch, ultralytics, openvino, ...

  Runs on Raspberry Pi        Needs a real server
```

### 4. Explainability

```
Use Case 6 output:
  "BW 5010kHz matches UMTS standard 5000kHz (score 99.8%)"
  "OFDM detection: True (confidence 100%, SCS 15kHz)"
  "Band DB: 942.5 MHz matches 3G Band 8, 4G Band 8, 5G n8"

  → Full reasoning chain, every step explained

YOLO output:
  "Detected: class=4G, bbox=[123, 0, 456, 640], conf=0.87"

  → Black box. Why 4G? What bandwidth? Which band?
```

### 5. Any IQ Format

```
Use Case 6: Takes raw IQ from ANY source
  RTL-SDR, HackRF, USRP, .npy, .csv, .wav
  Auto-detects format, normalizes to complex64
  Works with any sample rate and center frequency

YOLO Scanner: Expects pre-computed spectrogram
  Specific float32 FFT format
  Fixed FFT size (2048), fixed slice (357:1691)
  Requires protobuf TCP protocol
```

## The Best of Both Worlds: Hybrid Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    HYBRID PIPELINE                            │
│                                                              │
│  Raw IQ → FFT/DSP (1ms) → Quick Scan → Candidates          │
│                                              │               │
│                                    ┌─────────▼──────────┐   │
│                                    │ For each candidate: │   │
│                                    │ Generate spectrogram│   │
│                                    │ Run YOLO for:       │   │
│                                    │ • Exact freq        │   │
│                                    │ • 2G in gaps        │   │
│                                    │ • Technology class  │   │
│                                    └─────────┬──────────┘   │
│                                              │               │
│                              Final: merged results           │
│                              FFT speed + YOLO accuracy       │
└─────────────────────────────────────────────────────────────┘

Stage 1 (FFT/DSP - 1ms):
  "I see signals at 942.5 MHz (585kHz wide) and 953 MHz (small)"

Stage 2 (YOLO - 200ms, only when needed):
  "The 942.5 MHz signal is LTE Band 8 with 3 carriers at 932.6, 937.2, 927.5 MHz"
  "The 953 MHz signal is GSM at 953.4 MHz"
```

## Summary Scorecard

```
┌────────────────────┬───────────────┬───────────────┐
│  Criteria          │  FFT/DSP (UC6)│  YOLO Scanner │
├────────────────────┼───────────────┼───────────────┤
│  Speed             │  ★★★★★        │  ★★☆☆☆        │
│  Accuracy          │  ★★★☆☆        │  ★★★★★        │
│  2G Detection      │  ★★☆☆☆        │  ★★★★★        │
│  3G/4G Detection   │  ★★★☆☆        │  ★★★★★        │
│  Multi-carrier     │  ★★☆☆☆        │  ★★★★★        │
│  Explainability    │  ★★★★★        │  ★★☆☆☆        │
│  Lightweight       │  ★★★★★        │  ★★☆☆☆        │
│  No Training       │  ★★★★★        │  ☆☆☆☆☆        │
│  Format Flexibility│  ★★★★★        │  ★★☆☆☆        │
│  Production Ready  │  ★★★☆☆        │  ★★★★★        │
│  Edge Deploy       │  ★★★★★        │  ★★★☆☆        │
│  Memory Efficient  │  ★★★★★        │  ★★☆☆☆        │
├────────────────────┼───────────────┼───────────────┤
│  BEST FOR          │  Real-time    │  Production   │
│                    │  scanning,    │  cellular     │
│                    │  edge devices,│  detection,   │
│                    │  quick triage │  accuracy     │
└────────────────────┴───────────────┴───────────────┘
```

## Bottom Line

**YOLO Scanner wins on accuracy** — trained models recognize visual patterns that rules can't match, especially for 2G in gaps and multi-carrier separation.

**Use Case 6 wins on speed and simplicity** — 700x faster, 16x less memory, zero training, any input format.

**In production: Use YOLO.** For portfolio/demo/edge/real-time scanning: Use Case 6 is impressive and the right approach for a different problem (wideband spectrum monitoring vs targeted cellular detection).

**The ideal system: Hybrid** — FFT for fast wideband scan, YOLO for precise classification of detected signals.
