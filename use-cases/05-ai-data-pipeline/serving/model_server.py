"""Model serving with A/B testing support."""

from __future__ import annotations

import logging
import time
from typing import Any

import numpy as np

from models.schemas import ABTestResult, FeatureVector, ModelConfig, Prediction
from features.store import compute_features

logger = logging.getLogger(__name__)

# Model registry
_models: dict[str, ModelConfig] = {}
_prediction_stats = {"total_predictions": 0, "total_latency_ms": 0}

# Default models
DEFAULT_MODELS = [
    ModelConfig(
        name="purchase_propensity_v1",
        version="v1",
        model_type="logistic_regression",
        weights={
            "cart_to_view_ratio": 3.5,
            "purchase_to_view_ratio": 2.0,
            "total_cart_value": 0.005,
            "avg_page_duration_sec": 0.02,
            "cart_adds": 0.3,
            "unique_sessions": 0.2,
            "wishlist_adds": 0.5,
        },
        threshold=0.5,
    ),
    ModelConfig(
        name="purchase_propensity_v2",
        version="v2",
        model_type="logistic_regression",
        weights={
            "cart_to_view_ratio": 4.0,
            "purchase_to_view_ratio": 1.5,
            "total_cart_value": 0.008,
            "avg_page_duration_sec": 0.015,
            "cart_adds": 0.4,
            "total_browse_time_sec": 0.003,
            "searches": 0.2,
        },
        threshold=0.45,
    ),
]


def init_models():
    """Initialize default models."""
    for model in DEFAULT_MODELS:
        _models[model.name] = model
    logger.info(f"Initialized {len(_models)} models")


def predict(entity_id: str, model_name: str = "purchase_propensity_v1") -> Prediction:
    """Run prediction for an entity using specified model."""
    start = time.time()

    model = _models.get(model_name)
    if not model:
        return Prediction(entity_id=entity_id, model_name=model_name, label="error",
                         score=0, confidence=0, latency_ms=0)

    # Get features
    fv = compute_features(entity_id)

    # Logistic regression: sigmoid(sum(weight * feature))
    logit = 0.0
    features_used = {}
    for feature_name, weight in model.weights.items():
        val = fv.features.get(feature_name, 0.0)
        logit += weight * val
        features_used[feature_name] = val

    # Sigmoid
    score = 1 / (1 + np.exp(-logit))
    label = "likely_buyer" if score >= model.threshold else "browser"
    confidence = abs(score - 0.5) * 2  # Distance from decision boundary

    latency = (time.time() - start) * 1000
    _prediction_stats["total_predictions"] += 1
    _prediction_stats["total_latency_ms"] += latency

    return Prediction(
        entity_id=entity_id,
        model_name=model_name,
        model_version=model.version,
        score=round(float(score), 4),
        label=label,
        confidence=round(float(confidence), 4),
        features_used=features_used,
        latency_ms=round(latency, 2),
    )


def ab_test(entity_id: str, model_a: str, model_b: str) -> ABTestResult:
    """Run A/B test between two models."""
    pred_a = predict(entity_id, model_a)
    pred_b = predict(entity_id, model_b)

    # Winner has higher confidence
    winner = model_a if pred_a.confidence >= pred_b.confidence else model_b

    return ABTestResult(
        model_a=model_a,
        model_b=model_b,
        entity_id=entity_id,
        prediction_a=pred_a,
        prediction_b=pred_b,
        winner=winner,
    )


def get_models() -> list[ModelConfig]:
    return list(_models.values())


def get_stats() -> dict:
    total = _prediction_stats["total_predictions"]
    avg = _prediction_stats["total_latency_ms"] / total if total > 0 else 0
    return {"total_predictions": total, "avg_prediction_ms": round(avg, 2), "active_models": len(_models)}
