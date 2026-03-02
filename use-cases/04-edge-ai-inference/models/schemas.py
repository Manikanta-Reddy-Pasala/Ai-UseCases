from __future__ import annotations

from pydantic import BaseModel


class Detection(BaseModel):
    class_name: str
    confidence: float
    bbox: list[float] = []  # [x1, y1, x2, y2]


class InferenceResult(BaseModel):
    model_name: str = "edge-detector"
    backend: str = "numpy"
    detections: list[Detection] = []
    inference_time_ms: float = 0
    image_size: list[int] = []  # [width, height]
    preprocessing_ms: float = 0
    postprocessing_ms: float = 0


class ModelInfo(BaseModel):
    name: str
    backend: str
    input_shape: list[int] = []
    num_classes: int = 0
    status: str = "loaded"
    optimizations: list[str] = []


class BenchmarkResult(BaseModel):
    model_name: str
    backend: str
    iterations: int
    avg_inference_ms: float
    min_inference_ms: float
    max_inference_ms: float
    p95_inference_ms: float
    throughput_fps: float
    memory_usage_mb: float = 0


class HealthResponse(BaseModel):
    status: str = "ok"
    backend: str = "numpy"
    models_loaded: int = 0
