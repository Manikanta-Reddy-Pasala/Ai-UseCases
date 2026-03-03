# Edge AI Inference Platform

## On-Device AI Without Cloud Dependency

Run AI models directly on edge devices — no internet, no cloud, no latency. Built from real production experience deploying YOLO models for RF frequency pattern detection in defense environments.

---

### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    INFERENCE PIPELINE                         │
│                                                              │
│  Image ──► Preprocess ──► Model Inference ──► Postprocess    │
│   Input      │                  │                │           │
│              │                  │                │           │
│         ┌────▼────┐      ┌─────▼──────┐   ┌────▼─────┐     │
│         │ Resize  │      │  Backend   │   │   NMS    │     │
│         │ 640x640 │      │            │   │ Filter   │     │
│         │         │      │ ┌────────┐ │   │ Dedup    │     │
│         │ Normal- │      │ │ NumPy  │ │   │          │     │
│         │ ize 0-1 │      │ │OpenVINO│ │   │ conf >   │     │
│         │         │      │ │  ONNX  │ │   │  0.3     │     │
│         │ HWC →   │      │ └────────┘ │   │ IoU <    │     │
│         │ NCHW    │      │            │   │  0.5     │     │
│         └─────────┘      └────────────┘   └──────────┘     │
│                                                              │
│  Result: [{class: "frequency_peak", conf: 0.89,              │
│            bbox: [0.12, 0.34, 0.56, 0.78]}]                 │
└──────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   MODEL OPTIMIZER                            │
│                                                              │
│   Original Model (25MB, FP32)                                │
│         │                                                    │
│         ├── Static Shape ──────── 4x speedup                 │
│         ├── FP16 Quantization ─── 1.5x speedup, 50% smaller │
│         └── INT8 Quantization ─── 2.5x speedup, 75% smaller │
│                                                              │
│   Combined: Up to 10-15x faster, 75% smaller                │
└──────────────────────────────────────────────────────────────┘
```

### Performance (Tested)

| Metric | Value |
|--------|-------|
| Avg Inference | 15.5ms |
| P95 Latency | 19.3ms |
| Throughput | 64.6 FPS |
| Memory | 78.8 MB |
| INT8 Speedup | 10x estimated |
| Detection Classes | 10 (RF/signal domain) |

### Quick Demo

```bash
python3 main.py   # Port 8003

# Detect on random image
curl -X POST http://localhost:8003/api/v1/detect/random?width=640&height=480

# Benchmark
curl -X POST http://localhost:8003/api/v1/model/benchmark?iterations=50

# Optimize
curl -X POST "http://localhost:8003/api/v1/model/optimize?quantization=int8"
```

### Live: http://135.181.93.114:8003

---

**Detailed Docs**: [ARCHITECTURE.md](ARCHITECTURE.md) | [IMPLEMENTATION.md](IMPLEMENTATION.md)
