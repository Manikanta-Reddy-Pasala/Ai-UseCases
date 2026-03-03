# Implementation Details — IQ Signal Analyzer & Band Identifier v3

## Project Structure

```
06-spectrum-band-identifier/
├── main.py                              # FastAPI: 3 analysis endpoints + band DB + web UI
├── signal_processing/
│   ├── iq_reader.py                     # 7-format IQ parser + synthetic signal generator
│   ├── spectral_analyzer.py             # v3: 2-pass FFT detection + multi-carrier split
│   └── spectrogram_analyzer.py          # NEW: YOLO-format spectrogram analyzer
├── detector/
│   └── technology_classifier.py         # v3: 6-stage classifier (BW+flat+OFDM+SCS+band+TDD)
├── bands/
│   └── spectrum_db.py                   # 84-band database + frequency lookup
├── analyzer/
│   └── frequency_analyzer.py            # Generation comparison, overlaps, regional filter
├── data/samples/                        # Real IQ test files (B1, B3, B8, B20, B28)
├── requirements.txt
├── COMPARISON-vs-YOLO.md                # Detailed DSP vs YOLO analysis
└── .env.example
```

## Key Code: Spectrogram Analyzer (`signal_processing/spectrogram_analyzer.py`)

This is the new module that processes the SAME data format as the YOLO scanner:

```python
def analyze_spectrogram(raw_data, center_freq_khz, bandwidth_khz, num_chunks, ...):
    # Step 1: Reshape — same as scanner.py
    spectrogram = raw_data.reshape(n_rows, 2048)
    spec = spectrogram[:, 357:1691]        # 1334 useful bins, 15kHz each

    # Step 2: Multi-chunk reassembly (same logic as YOLO scanner)
    if num_chunks > 1:
        spec = _reassemble_chunks(spec, num_chunks, rows_per_chunk)

    # Step 3: Average across time → 1D power spectrum
    mean_psd = np.mean(spec, axis=0)       # dBm values
    freq_axis = start_freq + np.arange(len(mean_psd)) * 15  # kHz

    # Step 4: 2-pass detection (same pipeline as IQ mode)
    #   Pass 1: strong signals (3G/4G) with 6dB threshold, min 500kHz
    #   Pass 2: 2G in gaps with 3dB threshold, min 50kHz
```

## Key Code: Multi-Carrier Splitting (`spectral_analyzer.py`)

```python
def _split_multi_carrier(freq_axis, psd_db, start, end, noise_floor, min_dip_db=3.0):
    """Split wide signal into individual carriers at valleys."""
    smoothed = np.convolve(region_p, np.ones(5)/5, mode='same')  # Noise smoothing

    for i in range(5, n-5):
        left_max  = np.max(smoothed[i-15:i])      # Peak on left
        right_max = np.max(smoothed[i+1:i+16])    # Peak on right
        val = smoothed[i]                           # Valley value

        if (left_max - val >= 3.0 and              # 3dB dip from left
            right_max - val >= 3.0 and             # 3dB dip from right
            val < noise_floor + 10):               # Close to noise = real gap
            splits.append(i)

    # Result: [(start1, end1), (start2, end2), ...] = individual carriers
```

## Key Code: 6-Stage Classifier (`detector/technology_classifier.py`)

```python
# Scoring weights:
total = (bw_score      * 0.25 +    # Bandwidth match
         flatness_score * 0.20 +    # Spectral flatness (CDMA vs OFDM)
         ofdm_score     * 0.20 +    # CP autocorrelation
         scs_score      * 0.10 +    # Subcarrier spacing (15kHz vs 30kHz)
         band_score     * 0.10 +    # Band DB cross-validation
         tdd_score      * 0.10 +    # TDD power variance
         gap_bonus      * 0.05)     # 2G gap detection bonus

# Classification classes (v3):
#   GSM, UMTS, LTE-FDD, LTE-TDD, 5G_NR_FR1, 5G_NR_FR2

# TDD detection:
def detect_tdd_pattern(samples, sample_rate):
    powers = [np.mean(|chunk|^2) for chunk in time_windows]
    power_std = np.std(powers_db)
    is_tdd = power_std > 3.0 and power_range > 6.0
    # FDD = constant power, TDD = periodic drops
```

## API Reference

| Endpoint | Method | Input | Output | Speed |
|----------|--------|-------|--------|-------|
| `/api/v1/analyze` | POST | IQ file + sr + fc + fmt | Signals + PSD | 12-35ms |
| `/api/v1/analyze/spectrogram` | POST | Spectrogram file + cf_khz + bw_khz + chunks | Signals | 4-28ms |
| `/api/v1/analyze/generate` | POST | signal_type + center_freq + sr + snr | Signals + PSD | 22-44ms |
| `/api/v1/bands` | GET | `?generation=` | Band list | <1ms |
| `/api/v1/identify` | GET | `?freq=3500` | Matching bands | <1ms |
| `/api/v1/compare` | GET | - | 2G/3G/4G/5G comparison | <1ms |

## Comparison Test Results: DSP v3 vs YOLO Ground Truth

```
┌──────┬─────────┬─────────┬───────┬───────────────────────────────────────┐
│ Band │ YOLO    │ DSP v3  │ Time  │ Detail                                │
│      │ expects │ found   │       │                                       │
├──────┼─────────┼─────────┼───────┼───────────────────────────────────────┤
│ B1   │ 4G: 2165.0, 2146.7       │                                       │
│      │ 3G: 2116.4, 2137.7       │                                       │
│      │ 4/4     │ 2/4 50% │ 19ms  │ Hit 2146.7, 2116.4. Miss 2165, 2137 │
├──────┼─────────┼─────────┼───────┼───────────────────────────────────────┤
│ B3   │ 4G: 1815.0, 1870.0, 1849.5                                      │
│      │ 2G: 1860.2, 1842.6       │                                       │
│      │ 5/5     │ 4/5 80% │ 28ms  │ Hit 1870, 1815, 1860.2, 1842.6     │
│      │         │         │       │ Miss 1849.5                          │
├──────┼─────────┼─────────┼───────┼───────────────────────────────────────┤
│ B8   │ 3G: 932.6, 937.2, 927.5  │                                       │
│      │ 2G: 953.4                 │                                       │
│      │ 4/4     │ 3/4 75% │ 5ms   │ Hit 932.6, 937.2 (3G), 953.4 (2G)  │
│      │         │         │       │ Miss 927.5                           │
├──────┼─────────┼─────────┼───────┼───────────────────────────────────────┤
│ B20  │ 4G: 813.6, 798.5         │                                       │
│      │ 2/2     │ 1/2 50% │ 4ms   │ Hit 798.5 (wrong gen). Miss 813.6   │
├──────┼─────────┼─────────┼───────┼───────────────────────────────────────┤
│ B28  │ 4G: 763.1, 800.8         │                                       │
│      │ 2/2     │ 0/2  0% │ 8ms   │ Carriers at band edges missed       │
├──────┼─────────┼─────────┼───────┼───────────────────────────────────────┤
│ ALL  │ 17/17   │ 10/17   │ avg   │                                       │
│      │ 100%    │ 58.8%   │ 13ms  │ Speed: 10-50x faster than YOLO      │
└──────┴─────────┴─────────┴───────┴───────────────────────────────────────┘

Remaining gaps:
  - Generation misclassification (freq found, wrong 2G/3G/4G label)
  - False positives in gap detection (29 extra detections)
  - B28 carriers at extreme band edges
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8005` | Server port |
| `LOG_LEVEL` | `INFO` | Logging |

Analysis parameters (per-request):
| Parameter | Default | Description |
|-----------|---------|-------------|
| `fft_size` | `2048` | FFT points (IQ mode) |
| `threshold_db` | `6` | Detection threshold above noise |
| `center_freq_khz` | required | Tuned center frequency (spectrogram) |
| `bandwidth_khz` | required | Total bandwidth (spectrogram) |
| `num_chunks` | `1` | Frequency chunks in spectrogram |
