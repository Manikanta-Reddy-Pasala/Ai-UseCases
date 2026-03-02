# Use Case 4: Edge AI Inference Platform

## On-Device AI Without Cloud Dependency

Production-ready edge inference platform demonstrating YOLO-style object detection with model optimization for resource-constrained environments. Based on real production experience with RF frequency pattern detection.

## Architecture

```
Image Input → Preprocess → Model Inference → Postprocess (NMS) → Detections
                 │              │                  │
            Resize/Norm    Backend Engine      Confidence Filter
            HWC→NCHW      (numpy/OpenVINO)     + NMS Dedup
                                │
                        Model Optimizer
                        ├── Static Shape (4-15x speedup)
                        ├── FP16 Quantization (1.5x, 50% size)
                        └── INT8 Quantization (2.5x, 75% size)
```

## Key Features

- **Full detection pipeline**: preprocess → infer → NMS postprocessing
- **Backend-agnostic**: numpy (demo), OpenVINO, ONNX Runtime
- **Model optimizer**: static shape, FP16/INT8 quantization simulation
- **Performance benchmark**: latency, throughput FPS, memory usage, P95
- **10 detection classes** (RF/signal domain): frequency_peak, noise_floor, harmonic, interference, etc.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/detect` | Detect objects in uploaded image |
| POST | `/api/v1/detect/random` | Test with synthetic image |
| GET | `/api/v1/model/info` | Model information |
| POST | `/api/v1/model/benchmark` | Run performance benchmark |
| POST | `/api/v1/model/optimize` | Simulate optimization |
| GET | `/` | Interactive demo |

## Tested Results

```
VM: 135.181.93.114:8003
Backend: numpy (demo)
Avg Inference: 17.26ms | P95: 19.25ms | Throughput: 58 FPS
INT8 Optimization: 10x estimated speedup, 75% size reduction
Memory: 78.4 MB
```

## Production Reference

Based on real deployment: YOLO models for RF frequency analysis achieving 4-15x speedup through OpenVINO static shape optimization, running entirely on-device without cloud dependency.
