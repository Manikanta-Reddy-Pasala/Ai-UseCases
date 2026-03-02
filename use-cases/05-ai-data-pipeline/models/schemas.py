from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Event(BaseModel):
    event_id: str = ""
    event_type: str = ""
    entity_id: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: dict[str, Any] = {}


class FeatureVector(BaseModel):
    entity_id: str
    features: dict[str, float] = {}
    computed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class Prediction(BaseModel):
    entity_id: str
    model_name: str = "default"
    model_version: str = "v1"
    score: float = 0.0
    label: str = ""
    confidence: float = 0.0
    features_used: dict[str, float] = {}
    latency_ms: float = 0.0


class PipelineStats(BaseModel):
    events_ingested: int = 0
    features_computed: int = 0
    predictions_served: int = 0
    active_models: int = 0
    avg_prediction_ms: float = 0.0


class ModelConfig(BaseModel):
    name: str
    version: str = "v1"
    model_type: str = "logistic_regression"
    weights: dict[str, float] = {}
    threshold: float = 0.5
    active: bool = True


class ABTestResult(BaseModel):
    model_a: str
    model_b: str
    entity_id: str
    prediction_a: Prediction
    prediction_b: Prediction
    winner: str = ""


class HealthResponse(BaseModel):
    status: str = "ok"
    events_ingested: int = 0
    models_active: int = 0
