"""Feature store - computes and serves features for ML models."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime

from models.schemas import Event, FeatureVector
from pipeline.ingestion import get_entity_events

logger = logging.getLogger(__name__)

# In-memory feature cache
_feature_cache: dict[str, FeatureVector] = {}
_stats = {"features_computed": 0}


def compute_features(entity_id: str) -> FeatureVector:
    """Compute feature vector from entity's event history."""
    events = get_entity_events(entity_id, last_n=200)

    if not events:
        return FeatureVector(entity_id=entity_id)

    features = {}

    # Event count features
    features["total_events"] = float(len(events))
    event_types = defaultdict(int)
    for e in events:
        event_types[e.event_type] += 1

    features["page_views"] = float(event_types.get("page_view", 0))
    features["cart_adds"] = float(event_types.get("add_to_cart", 0))
    features["purchases"] = float(event_types.get("purchase", 0))
    features["searches"] = float(event_types.get("search", 0))
    features["cart_removes"] = float(event_types.get("remove_from_cart", 0))
    features["wishlist_adds"] = float(event_types.get("wishlist_add", 0))

    # Ratio features
    if features["page_views"] > 0:
        features["cart_to_view_ratio"] = round(features["cart_adds"] / features["page_views"], 4)
        features["purchase_to_view_ratio"] = round(features["purchases"] / features["page_views"], 4)
    else:
        features["cart_to_view_ratio"] = 0.0
        features["purchase_to_view_ratio"] = 0.0

    # Monetary features
    total_cart_value = sum(
        e.data.get("price", 0) * e.data.get("quantity", 1)
        for e in events if e.event_type == "add_to_cart"
    )
    total_purchase_value = sum(
        e.data.get("total", 0) for e in events if e.event_type == "purchase"
    )
    features["total_cart_value"] = round(float(total_cart_value), 2)
    features["total_purchase_value"] = round(float(total_purchase_value), 2)
    features["avg_cart_item_price"] = round(
        total_cart_value / features["cart_adds"], 2
    ) if features["cart_adds"] > 0 else 0.0

    # Engagement features
    total_duration = sum(
        e.data.get("duration_sec", 0) for e in events if e.event_type == "page_view"
    )
    features["total_browse_time_sec"] = float(total_duration)
    features["avg_page_duration_sec"] = round(
        total_duration / features["page_views"], 1
    ) if features["page_views"] > 0 else 0.0

    # Session diversity
    sessions = {e.data.get("session_id", "") for e in events if e.data.get("session_id")}
    features["unique_sessions"] = float(len(sessions))

    # Cache the features
    fv = FeatureVector(entity_id=entity_id, features=features)
    _feature_cache[entity_id] = fv
    _stats["features_computed"] += 1

    return fv


def get_cached_features(entity_id: str) -> FeatureVector | None:
    return _feature_cache.get(entity_id)


def get_stats() -> dict:
    return {
        "features_computed": _stats["features_computed"],
        "cached_entities": len(_feature_cache),
    }
