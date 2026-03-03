# Architecture — IQ Signal Analyzer & Band Identifier v3

## Dual-Mode System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         FastAPI Server (:8005)                           │
│                                                                          │
│  POST /api/v1/analyze              ► Raw IQ file → FFT → detect         │
│  POST /api/v1/analyze/spectrogram  ► Pre-computed spectrogram → detect  │
│  POST /api/v1/analyze/generate     ► Synthetic signal → detect          │
│  GET  /api/v1/bands                ► 84-band database                   │
│  GET  /api/v1/identify?freq=       ► Frequency → band lookup            │
│  GET  /                            ► Interactive web UI                  │
└──────────────┬──────────────────────────────┬────────────────────────────┘
               │                              │
    ┌──────────▼──────────┐        ┌──────────▼──────────┐
    │   IQ MODE           │        │  SPECTROGRAM MODE   │
    │                     │        │                     │
    │  Raw IQ (complex)   │        │  float32 FFT data   │
    │  → FFT (2048-pt)    │        │  → Reshape (N,2048) │
    │  → PSD (dB)         │        │  → Slice [357:1691] │
    │  → 1D power spectrum│        │  → Chunk reassembly │
    │                     │        │  → Mean across time  │
    │  Time: 0.3ms        │        │  → 1D power spectrum│
    └──────────┬──────────┘        │                     │
               │                   │  Time: 2-5ms        │
               │                   └──────────┬──────────┘
               │                              │
               └──────────────┬───────────────┘
                              │
               ┌──────────────▼──────────────────────────────┐
               │        2-PASS DETECTION PIPELINE (v3)       │
               │                                              │
               │  ┌────────────────────────────────────────┐ │
               │  │  PASS 1: Strong Signal Detection       │ │
               │  │                                        │ │
               │  │  Threshold = noise_floor + 6dB         │ │
               │  │  Min BW = 500 kHz (skip 2G)            │ │
               │  │                                        │ │
               │  │  For each region above threshold:      │ │
               │  │  ┌──────────────────────────────────┐  │ │
               │  │  │ Multi-Carrier Splitting (FIX #1) │  │ │
               │  │  │                                  │  │ │
               │  │  │ If BW > 8MHz:                    │  │ │
               │  │  │   Smooth PSD (5-tap avg)         │  │ │
               │  │  │   Find valleys (dip >3dB both    │  │ │
               │  │  │   sides AND <10dB above noise)   │  │ │
               │  │  │   Split into sub-carriers        │  │ │
               │  │  │                                  │  │ │
               │  │  │ Before: ████████████████████     │  │ │
               │  │  │         (one 20MHz region)       │  │ │
               │  │  │                                  │  │ │
               │  │  │ After:  ████ ▽ ████ ▽ ████      │  │ │
               │  │  │         (three 5-7MHz carriers)  │  │ │
               │  │  └──────────────────────────────────┘  │ │
               │  │                                        │ │
               │  │  Per carrier: -3dB BW + threshold BW   │ │
               │  │  Power-weighted centroid for center     │ │
               │  │  Spectral flatness measurement         │ │
               │  └────────────────────────────────────────┘ │
               │                    │                        │
               │  ┌─────────────────▼──────────────────────┐ │
               │  │  GAP COMPUTATION                       │ │
               │  │                                        │ │
               │  │  Full band:  ███ 4G ███  ███ 4G ███    │ │
               │  │  Gaps:       ▒▒▒▒▒▒▒▒▒  ▒▒▒▒▒▒▒▒▒    │ │
               │  │              ↑ search    ↑ search       │ │
               │  │              here        here           │ │
               │  └─────────────────┬──────────────────────┘ │
               │                    │                        │
               │  ┌─────────────────▼──────────────────────┐ │
               │  │  PASS 2: 2G Gap Detection (FIX #2)    │ │
               │  │                                        │ │
               │  │  Lower threshold: noise + 3dB          │ │
               │  │  Min BW: 50 kHz (catch 200kHz GSM)     │ │
               │  │  Only search in gap regions             │ │
               │  │                                        │ │
               │  │  Finds narrow 2G carriers that Pass 1  │ │
               │  │  would miss — same strategy as YOLO    │ │
               │  └────────────────────────────────────────┘ │
               └──────────────┬──────────────────────────────┘
                              │
               ┌──────────────▼──────────────────────────────┐
               │       6-STAGE CLASSIFIER (v3)               │
               │                                              │
               │  ┌─ 1. Bandwidth Matching ────── (25%) ──┐ │
               │  │  200kHz→GSM, 5MHz→UMTS/LTE, 10+→LTE  │ │
               │  └───────────────────────────────────────┘ │
               │  ┌─ 2. Spectral Flatness (FIX #4)─(20%)─┐ │
               │  │  GSM < 0.35 │ OFDM 0.25-0.65         │ │
               │  │  CDMA 0.55-1.0 (UMTS = flat)          │ │
               │  └───────────────────────────────────────┘ │
               │  ┌─ 3. OFDM CP Detection ──────── (20%) ─┐ │
               │  │  Cyclic prefix autocorrelation          │ │
               │  │  OFDM=yes → LTE/5G │ OFDM=no → GSM/UMTS│ │
               │  └───────────────────────────────────────┘ │
               │  ┌─ 4. Subcarrier Spacing ──────── (10%) ─┐ │
               │  │  15kHz → LTE │ 30kHz → 5G NR           │ │
               │  └───────────────────────────────────────┘ │
               │  ┌─ 5. Band DB Lookup ──────────── (10%) ─┐ │
               │  │  84 bands, TDD band cross-validation   │ │
               │  └───────────────────────────────────────┘ │
               │  ┌─ 6. TDD Detection (FIX #4) ──── (10%) ─┐ │
               │  │  Power variance across time frames      │ │
               │  │  TDD = periodic drops │ FDD = constant  │ │
               │  └───────────────────────────────────────┘ │
               │  ┌─ 7. 2G Gap Bonus ──────────── (5%) ───┐ │
               │  │  Boost GSM score if gap-detected       │ │
               │  └───────────────────────────────────────┘ │
               │                                              │
               │  Output classes: GSM, UMTS, LTE-FDD,        │
               │                  LTE-TDD, 5G_NR_FR1,        │
               │                  5G_NR_FR2                   │
               └──────────────────────────────────────────────┘
```

## Spectrogram Data Format (YOLO Scanner Compatible)

```
Raw float32 file:
┌──────────────────────────────────────────────────────────┐
│  row 0:   [bin0, bin1, bin2, ... bin2047]                │  2048 FFT bins
│  row 1:   [bin0, bin1, bin2, ... bin2047]                │  per time snapshot
│  ...                                                      │
│  row N-1: [bin0, bin1, bin2, ... bin2047]                │
└──────────────────────────────────────────────────────────┘
         Values are dBm power (-130 to -20 range)

Useful slice [:, 357:1691]:
┌─────────────────────────────────────────┐
│  1334 frequency bins × N time rows      │
│  Each bin = 15 kHz                      │
│  Total useful BW = 1334 × 15 = ~20 MHz │
└─────────────────────────────────────────┘

Multi-chunk assembly (same as scanner.py):
  Chunk 1: [:fifteen_mhz_points]           ← first 1000 bins
  Chunk 2: [five_mhz_points:]             ← skip 333, take rest
  Middle:  [five_mhz_points:fifteen_mhz_points]  ← 333..1000
```

## v3 Fixes vs YOLO Weaknesses

```
┌───────────────────────┬──────────────────────┬─────────────────────┐
│ Weakness              │ Fix Applied          │ Result              │
├───────────────────────┼──────────────────────┼─────────────────────┤
│ 1. Multi-carrier:     │ Valley splitting     │ 3 carriers in B3    │
│    saw 1 broad region │ at dips >3dB         │ instead of 1        │
├───────────────────────┼──────────────────────┼─────────────────────┤
│ 2. 2G missed:         │ 2-pass pipeline      │ Found GSM 953.4 MHz │
│    no gap detection   │ gaps + lower thresh  │ and 1860.2 MHz      │
├───────────────────────┼──────────────────────┼─────────────────────┤
│ 3. Low accuracy:      │ -3dB BW + flatness   │ 12% → 59%           │
│    wrong BW, wrong    │ + spectrogram mode   │ accuracy             │
│    data format        │                      │                     │
├───────────────────────┼──────────────────────┼─────────────────────┤
│ 4. No FDD/TDD:        │ TDD power variance   │ LTE-FDD / LTE-TDD  │
│    all called "LTE"   │ + separate classes   │ as distinct classes │
└───────────────────────┴──────────────────────┴─────────────────────┘
```

## Performance Optimization

```
┌────────────────────────────────────────────────────────────────┐
│  IQ MODE                         SPECTROGRAM MODE              │
│  ──────────                      ─────────────────             │
│  FFT (2048):        0.3ms        Read + reshape:     2ms      │
│  Detection:         0.5ms        Mean across time:   1ms      │
│  OFDM detection:    0.3ms        Detection (2-pass): 1ms      │
│  Classification:    0.1ms        Classification:     0.5ms    │
│  ─────────────────────────       ──────────────────────        │
│  TOTAL:             1.2ms        TOTAL:              4-5ms    │
│                                                                │
│  YOLO comparison:   170-940ms    (20-200x faster)              │
└────────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| FFT | numpy.fft (cached windows) | Raw IQ → power spectrum |
| Spectrogram | numpy reshape + slice | YOLO-format spectrogram parsing |
| Detection | numpy vectorized threshold | Signal finding (2-pass) |
| CP Correlation | numpy.vdot | OFDM detection |
| Band DB | 84-band dataclass list | 3GPP frequency lookup |
| API | FastAPI + JSONResponse | REST + numpy serialization |

## 3GPP Sources

| Gen | Spec | Content |
|-----|------|---------|
| 2G | TS 45.005 | GSM radio transmission |
| 3G | TS 25.101 | UMTS UE radio (FDD) |
| 4G | TS 36.101 | E-UTRA UE radio |
| 5G | TS 38.101 | NR UE radio |
