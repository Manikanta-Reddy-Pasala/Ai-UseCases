# Architecture — IQ Signal Analyzer & Band Identifier

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                      FastAPI Server (:8005)                           │
│                                                                       │
│  POST /api/v1/analyze ──────────────► IQ File Upload + Analysis      │
│  POST /api/v1/analyze/generate ─────► Synthetic Signal + Analysis    │
│  GET  /api/v1/bands ────────────────► Band Database (84 bands)       │
│  GET  /api/v1/identify?freq= ───────► Frequency → Band Lookup       │
│  GET  /api/v1/compare ──────────────► Generation Comparison          │
│  GET  / ────────────────────────────► Interactive Web UI + PSD Plot  │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
        ┌──────────────▼──────────────────────────────────────────────┐
        │                 IQ ANALYSIS PIPELINE                         │
        │                 Total: 1.2ms (analysis only)                 │
        │                                                              │
        │  ┌──────────────────────────────────────────────────────┐   │
        │  │  STAGE 1: IQ READER                         0.1ms   │   │
        │  │                                                      │   │
        │  │  Input bytes ──► Format detection ──► complex64[]    │   │
        │  │                                                      │   │
        │  │  Formats:                                            │   │
        │  │  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌─────────┐  │   │
        │  │  │ uint8   │ │ int16   │ │ float32  │ │  npy    │  │   │
        │  │  │ RTL-SDR │ │ RTL-SDR │ │ USRP     │ │ NumPy   │  │   │
        │  │  │ -127.5  │ │ /32768  │ │ direct   │ │ direct  │  │   │
        │  │  │ /127.5  │ │         │ │ I+jQ     │ │         │  │   │
        │  │  └─────────┘ └─────────┘ └──────────┘ └─────────┘  │   │
        │  │  ┌─────────┐ ┌─────────┐ ┌──────────┐              │   │
        │  │  │ int8    │ │  CSV    │ │  WAV     │              │   │
        │  │  │ HackRF  │ │ I,Q    │ │ 2-ch     │              │   │
        │  │  │ /128    │ │ columns │ │ audio    │              │   │
        │  │  └─────────┘ └─────────┘ └──────────┘              │   │
        │  └──────────────────────────────────────────────────────┘   │
        │                          │                                   │
        │  ┌───────────────────────▼──────────────────────────────┐   │
        │  │  STAGE 2: SPECTRAL ANALYSIS (FFT)           0.3ms   │   │
        │  │                                                      │   │
        │  │  samples[0:N]                                        │   │
        │  │       │                                              │   │
        │  │  ┌────▼──────┐                                       │   │
        │  │  │  Hanning  │  Pre-cached window (no realloc)       │   │
        │  │  │  Window   │                                       │   │
        │  │  └────┬──────┘                                       │   │
        │  │       │                                              │   │
        │  │  ┌────▼──────┐                                       │   │
        │  │  │  np.fft   │  2048-point FFT                       │   │
        │  │  │  .fft()   │  Up to 8 frames averaged              │   │
        │  │  └────┬──────┘                                       │   │
        │  │       │                                              │   │
        │  │  ┌────▼──────┐                                       │   │
        │  │  │ fftshift  │  DC → center (SDR display format)     │   │
        │  │  │ 10*log10  │  → PSD in dB                          │   │
        │  │  └────┬──────┘                                       │   │
        │  │       │                                              │   │
        │  │  Output: freq_axis_hz[], psd_db[]                    │   │
        │  └───────────────────────┬──────────────────────────────┘   │
        │                          │                                   │
        │  ┌───────────────────────▼──────────────────────────────┐   │
        │  │  STAGE 3: SIGNAL DETECTION                  0.5ms   │   │
        │  │                                                      │   │
        │  │  Noise Floor = percentile(PSD, 25%)                  │   │
        │  │  Threshold = Noise Floor + 6 dB                      │   │
        │  │                                                      │   │
        │  │  PSD:  ──────╱╲────────╱╲╱╲──────────                │   │
        │  │  Thr:  ------┼---------┼-------- threshold           │   │
        │  │  NF:   ______┼____NF___┼________________             │   │
        │  │              │         │                              │   │
        │  │         Signal 1   Signal 2                          │   │
        │  │                                                      │   │
        │  │  For each region above threshold:                    │   │
        │  │  ├── bandwidth = freq_end - freq_start               │   │
        │  │  ├── skip if < 50 kHz (noise spike)                  │   │
        │  │  ├── center = power-weighted centroid                 │   │
        │  │  ├── peak_power, SNR = peak - noise_floor            │   │
        │  │  └── absolute_center = tuned_freq + offset           │   │
        │  │                                                      │   │
        │  │  Vectorized: np.diff(above) for start/end indices    │   │
        │  └───────────────────────┬──────────────────────────────┘   │
        │                          │                                   │
        │  ┌───────────────────────▼──────────────────────────────┐   │
        │  │  STAGE 4: TECHNOLOGY CLASSIFICATION         0.3ms   │   │
        │  │                                                      │   │
        │  │  ┌────────────────────────────────────────────────┐  │   │
        │  │  │  Step 1: BANDWIDTH MATCHING (0.05ms)           │  │   │
        │  │  │                                                │  │   │
        │  │  │  Detected BW    Standard BWs     Technology    │  │   │
        │  │  │  ──────────    ────────────     ──────────    │  │   │
        │  │  │  ~200 kHz   →  200 kHz       →  GSM (2G)     │  │   │
        │  │  │  ~5 MHz     →  5 MHz         →  UMTS (3G)    │  │   │
        │  │  │  ~10 MHz    →  10 MHz        →  LTE (4G)     │  │   │
        │  │  │  ~50 MHz    →  50 MHz        →  5G NR FR1    │  │   │
        │  │  │  ~200 MHz   →  200 MHz       →  5G NR FR2    │  │   │
        │  │  │                                                │  │   │
        │  │  │  Tolerance: ±20-50% depending on tech          │  │   │
        │  │  │  Score: 1.0 - |measured/standard - 1.0|        │  │   │
        │  │  └────────────────────────────────────────────────┘  │   │
        │  │                                                      │   │
        │  │  ┌────────────────────────────────────────────────┐  │   │
        │  │  │  Step 2: OFDM DETECTION (0.15ms)               │  │   │
        │  │  │                                                │  │   │
        │  │  │  Cyclic Prefix autocorrelation:                │  │   │
        │  │  │                                                │  │   │
        │  │  │  OFDM Symbol:                                  │  │   │
        │  │  │  ┌──CP──┬──────FFT data──────┐                 │  │   │
        │  │  │  │XXXXX│                     │XXXXX│           │  │   │
        │  │  │  └──┬──┘                     └──┬──┘           │  │   │
        │  │  │     └────── correlate ──────────┘              │  │   │
        │  │  │     CP = copy of last N samples                │  │   │
        │  │  │                                                │  │   │
        │  │  │  If corr > 0.3 → OFDM (LTE or 5G NR)         │  │   │
        │  │  │  If corr < 0.3 → non-OFDM (GSM or UMTS)      │  │   │
        │  │  │                                                │  │   │
        │  │  │  Optimized: np.vdot, only 20K samples,        │  │   │
        │  │  │  10 symbols max, 5 FFT sizes                   │  │   │
        │  │  └────────────────────────────────────────────────┘  │   │
        │  │                                                      │   │
        │  │  ┌────────────────────────────────────────────────┐  │   │
        │  │  │  Step 3: SUBCARRIER SPACING (0.02ms)           │  │   │
        │  │  │                                                │  │   │
        │  │  │  SCS = sample_rate / best_fft_size             │  │   │
        │  │  │  ~15 kHz → LTE                                 │  │   │
        │  │  │  ~30 kHz → 5G NR (FR1)                         │  │   │
        │  │  │  ~120 kHz → 5G NR (FR2)                        │  │   │
        │  │  └────────────────────────────────────────────────┘  │   │
        │  │                                                      │   │
        │  │  ┌────────────────────────────────────────────────┐  │   │
        │  │  │  Step 4: BAND DATABASE LOOKUP (0.08ms)         │  │   │
        │  │  │                                                │  │   │
        │  │  │  absolute_center_freq_mhz → search 84 bands   │  │   │
        │  │  │  Match UL range and DL range                   │  │   │
        │  │  │  Boost score if generation matches BW match    │  │   │
        │  │  └────────────────────────────────────────────────┘  │   │
        │  │                                                      │   │
        │  │  Final Score = BW(40%) + OFDM(25%) + SCS(15%)        │   │
        │  │               + Band(20%)                             │   │
        │  │                                                      │   │
        │  │  Output: technology, generation, confidence,          │   │
        │  │          center_freq_hz, decoding_hint                │   │
        │  └──────────────────────────────────────────────────────┘   │
        └─────────────────────────────────────────────────────────────┘
```

## Signal Generation (Test Mode)

```
┌─────────────────────────────────────────────────────────────────┐
│  Synthetic Signal Generator (for testing / demo)                 │
│                                                                  │
│  GSM:    Phase modulation (GMSK-like)                           │
│          → cumulative random ±1 bits × modulation index         │
│          → exp(j × phase) → single narrow carrier               │
│                                                                  │
│  UMTS:   QPSK chips → frequency-domain bandlimit to 5MHz       │
│          → np.fft.fft → zero outside BW → np.fft.ifft          │
│          → flat wideband spectrum (CDMA-like)                   │
│                                                                  │
│  LTE:    OFDM symbol generation:                                │
│          → Random QPSK on 600 subcarriers (10MHz)               │
│          → 1024-pt IFFT → add cyclic prefix (72 samples)        │
│          → concatenate symbols → real OFDM with CP              │
│                                                                  │
│  5G NR:  Same as LTE but wider:                                 │
│          → 1632 subcarriers (50MHz), 4096-pt IFFT               │
│          → CP = 288 samples (30kHz SCS)                         │
│                                                                  │
│  All: + AWGN noise at configurable SNR                          │
└─────────────────────────────────────────────────────────────────┘
```

## Performance Optimization Techniques

```
┌──────────────────────────────────────────────────────────────────┐
│  BEFORE (v1)                    AFTER (v2)              SPEEDUP  │
│  ─────────────────────────────────────────────────────────────   │
│  scipy.welch(4096)  3.3ms  →  raw np.fft(2048)  0.3ms   11x    │
│  Python loop detect 0.8ms  →  np.diff vectorize 0.5ms    1.6x   │
│  OFDM 100K samples  9.4ms  →  20K + np.vdot     0.3ms   31x    │
│  Hanning alloc/call 0.1ms  →  pre-cached dict    0ms     ∞      │
│  scipy dependency    heavy  →  numpy-only         light   -      │
│  ─────────────────────────────────────────────────────────────   │
│  TOTAL              ~14ms  →                     1.2ms   11.7x   │
└──────────────────────────────────────────────────────────────────┘

Key decisions:
  1. Raw FFT over scipy.welch — we control averaging ourselves
  2. Hanning window cache — dict keyed by FFT size, allocated once
  3. OFDM: only 20K samples needed (10 symbols sufficient)
  4. np.vdot for CP correlation — single call vs loop
  5. 2048-pt FFT — enough resolution, 2x faster than 4096
  6. Vectorized threshold: np.diff(above.astype(int8)) for edges
```

## Band Database (unchanged from v1)

```
┌─────────────────────────────────────────────────────────────────┐
│  84 BANDS across 4 generations (3GPP compliant)                  │
│                                                                  │
│  2G GSM:   10 bands │ 450-1990 MHz │ 200 kHz │ FDD              │
│  3G UMTS:  14 bands │ 791-2690 MHz │ 5 MHz   │ FDD              │
│  4G LTE:   34 bands │ 462-5925 MHz │ ≤20 MHz │ FDD+TDD+SDL     │
│  5G NR:    26 bands │ 617-40 GHz   │ ≤400 MHz│ FDD+TDD          │
│                                                                  │
│  Spectrum:                                                       │
│  2G ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░    │
│  3G ░░██████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░    │
│  4G ░██████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░    │
│  5G ░░████████████████████████████████████████████████████████   │
│     0    1    2    3    4    5    6           28          40 GHz  │
└─────────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| FFT | numpy.fft | Fastest pure-Python FFT |
| Window | numpy (cached) | Zero-alloc after first call |
| Detection | numpy vectorized | No Python loops in hot path |
| CP Correlation | numpy.vdot | Single BLAS call |
| IQ Parse | numpy.frombuffer | Zero-copy for binary formats |
| API | FastAPI + Uvicorn | Async, <1ms overhead |
| Serialization | Custom _sanitize() | Handle numpy→JSON |

## 3GPP Sources

| Gen | Spec | Content |
|-----|------|---------|
| 2G | TS 45.005 | GSM radio transmission |
| 3G | TS 25.101 | UMTS UE radio (FDD) |
| 4G | TS 36.101 | E-UTRA UE radio |
| 5G | TS 38.101 | NR UE radio |
