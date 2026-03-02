"""Edge inference engine - supports numpy demo, OpenVINO, and ONNX backends.

This demonstrates the inference pipeline pattern used in production:
1. Image preprocessing (resize, normalize, pad)
2. Model inference (backend-agnostic)
3. Postprocessing (NMS, confidence filtering)
"""

from __future__ import annotations

import logging
import time
from typing import Any

import numpy as np

from models.schemas import Detection, InferenceResult

logger = logging.getLogger(__name__)

# Simulated classes (YOLO-like)
CLASSES = [
    "frequency_peak", "noise_floor", "harmonic", "interference",
    "signal_burst", "carrier_wave", "modulation_pattern", "anomaly",
    "background", "artifact",
]


class EdgeInferenceEngine:
    """Backend-agnostic inference engine for edge deployment."""

    def __init__(self, backend: str = "numpy"):
        self.backend = backend
        self.input_shape = (1, 3, 640, 640)  # NCHW
        self.num_classes = len(CLASSES)
        self._model = None
        self._load_model()

    def _load_model(self):
        """Load model based on backend."""
        if self.backend == "numpy":
            # Demo mode: use random weights as a mock model
            np.random.seed(42)
            self._model = {
                "conv_weights": np.random.randn(64, 3, 3, 3).astype(np.float32) * 0.1,
                "fc_weights": np.random.randn(self.num_classes, 64).astype(np.float32) * 0.1,
            }
            logger.info("Loaded demo numpy model (simulated edge inference)")
        elif self.backend == "openvino":
            logger.info("OpenVINO backend: would load IR model (.xml/.bin)")
            self._model = "openvino_placeholder"
        elif self.backend == "onnx":
            logger.info("ONNX backend: would load .onnx model")
            self._model = "onnx_placeholder"

    def preprocess(self, image_data: np.ndarray) -> tuple[np.ndarray, float]:
        """Preprocess image: resize, normalize, pad to input shape."""
        start = time.time()

        if image_data.ndim == 2:  # Grayscale
            image_data = np.stack([image_data] * 3, axis=-1)

        # Resize to model input (simplified)
        h, w = image_data.shape[:2]
        target_h, target_w = self.input_shape[2], self.input_shape[3]

        # Simple resize via sampling
        row_indices = np.linspace(0, h - 1, target_h).astype(int)
        col_indices = np.linspace(0, w - 1, target_w).astype(int)
        resized = image_data[np.ix_(row_indices, col_indices)]

        # Normalize to [0, 1]
        normalized = resized.astype(np.float32) / 255.0

        # HWC to NCHW
        transposed = np.transpose(normalized, (2, 0, 1))
        batched = np.expand_dims(transposed, 0)

        preprocess_ms = (time.time() - start) * 1000
        return batched, preprocess_ms

    def infer(self, preprocessed: np.ndarray) -> tuple[np.ndarray, float]:
        """Run inference through the model."""
        start = time.time()

        if self.backend == "numpy":
            # Simulate convolution + detection (mock but realistic pipeline)
            # Global average pool of input
            features = np.mean(preprocessed, axis=(2, 3))  # (1, 3)
            # Project through "conv" weights (simplified)
            features_expanded = np.tile(features, (1, 22))[:, :64]  # (1, 64)
            # Classification
            logits = features_expanded @ self._model["fc_weights"].T  # (1, num_classes)
            # Sigmoid for confidence
            confidences = 1 / (1 + np.exp(-logits))

            # Generate pseudo-detections based on input patterns
            # Create bounding boxes based on where "signal" is strongest
            num_detections = np.random.randint(2, 6)
            detections = np.zeros((num_detections, 6))  # x1,y1,x2,y2,conf,class
            for i in range(num_detections):
                cx = np.random.uniform(0.1, 0.9)
                cy = np.random.uniform(0.1, 0.9)
                w = np.random.uniform(0.05, 0.3)
                h = np.random.uniform(0.05, 0.2)
                detections[i] = [
                    cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2,
                    float(confidences[0, i % self.num_classes]) * np.random.uniform(0.5, 1.0),
                    i % self.num_classes,
                ]

            raw_output = detections
        else:
            # Placeholder for real backends
            raw_output = np.zeros((3, 6))

        inference_ms = (time.time() - start) * 1000
        return raw_output, inference_ms

    def postprocess(self, raw_output: np.ndarray, conf_threshold: float = 0.3) -> tuple[list[Detection], float]:
        """Postprocess: filter by confidence, apply NMS."""
        start = time.time()

        detections = []
        for det in raw_output:
            x1, y1, x2, y2, conf, cls_id = det
            if conf >= conf_threshold:
                detections.append(Detection(
                    class_name=CLASSES[int(cls_id) % len(CLASSES)],
                    confidence=round(float(conf), 4),
                    bbox=[round(float(x1), 4), round(float(y1), 4),
                          round(float(x2), 4), round(float(y2), 4)],
                ))

        # Simple NMS (remove overlapping detections of same class)
        detections = self._nms(detections, iou_threshold=0.5)

        postprocess_ms = (time.time() - start) * 1000
        return detections, postprocess_ms

    def detect(self, image_data: np.ndarray) -> InferenceResult:
        """Full detection pipeline: preprocess → infer → postprocess."""
        h, w = image_data.shape[:2]

        preprocessed, preprocess_ms = self.preprocess(image_data)
        raw_output, inference_ms = self.infer(preprocessed)
        detections, postprocess_ms = self.postprocess(raw_output)

        return InferenceResult(
            model_name="edge-detector-v1",
            backend=self.backend,
            detections=detections,
            inference_time_ms=round(inference_ms, 2),
            image_size=[w, h],
            preprocessing_ms=round(preprocess_ms, 2),
            postprocessing_ms=round(postprocess_ms, 2),
        )

    def benchmark(self, iterations: int = 100) -> dict:
        """Run inference benchmark."""
        # Create synthetic input
        test_input = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        times = []
        for _ in range(iterations):
            start = time.time()
            preprocessed, _ = self.preprocess(test_input)
            _, inf_time = self.infer(preprocessed)
            times.append((time.time() - start) * 1000)

        times = np.array(times)
        import psutil
        mem = psutil.Process().memory_info().rss / 1024 / 1024

        return {
            "model_name": "edge-detector-v1",
            "backend": self.backend,
            "iterations": iterations,
            "avg_inference_ms": round(float(np.mean(times)), 2),
            "min_inference_ms": round(float(np.min(times)), 2),
            "max_inference_ms": round(float(np.max(times)), 2),
            "p95_inference_ms": round(float(np.percentile(times, 95)), 2),
            "throughput_fps": round(1000 / float(np.mean(times)), 1),
            "memory_usage_mb": round(mem, 1),
        }

    @staticmethod
    def _nms(detections: list[Detection], iou_threshold: float = 0.5) -> list[Detection]:
        """Simple Non-Maximum Suppression."""
        if len(detections) <= 1:
            return detections

        # Sort by confidence
        detections.sort(key=lambda d: d.confidence, reverse=True)

        kept = []
        for det in detections:
            overlap = False
            for k in kept:
                if det.class_name == k.class_name:
                    iou = _compute_iou(det.bbox, k.bbox)
                    if iou > iou_threshold:
                        overlap = True
                        break
            if not overlap:
                kept.append(det)

        return kept


def _compute_iou(box1: list[float], box2: list[float]) -> float:
    """Compute IoU between two bounding boxes."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - inter

    return inter / union if union > 0 else 0
