"""Event ingestion and processing pipeline."""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import datetime

from models.schemas import Event

logger = logging.getLogger(__name__)

# In-memory event store
_events: list[Event] = []
_entity_events: dict[str, list[Event]] = defaultdict(list)
_stats = {"total_ingested": 0}


def ingest_event(event: Event) -> Event:
    """Ingest a single event into the pipeline."""
    if not event.event_id:
        event.event_id = str(uuid.uuid4())[:8]
    if not event.timestamp:
        event.timestamp = datetime.utcnow().isoformat()

    _events.append(event)
    _entity_events[event.entity_id].append(event)
    _stats["total_ingested"] += 1

    logger.debug(f"Ingested event {event.event_id}: {event.event_type} for {event.entity_id}")
    return event


def ingest_batch(events: list[Event]) -> int:
    """Ingest a batch of events."""
    for event in events:
        ingest_event(event)
    return len(events)


def get_entity_events(entity_id: str, last_n: int = 100) -> list[Event]:
    """Get recent events for an entity."""
    return _entity_events.get(entity_id, [])[-last_n:]


def get_stats() -> dict:
    return {
        "total_ingested": _stats["total_ingested"],
        "unique_entities": len(_entity_events),
        "event_types": len({e.event_type for e in _events}),
    }


def generate_sample_events(entity_id: str = "user_001", count: int = 20) -> list[Event]:
    """Generate sample e-commerce events for demo."""
    import random
    event_types = [
        ("page_view", {"page": "/products", "duration_sec": 45}),
        ("page_view", {"page": "/cart", "duration_sec": 30}),
        ("add_to_cart", {"product_id": "p123", "price": 29.99, "quantity": 1}),
        ("add_to_cart", {"product_id": "p456", "price": 49.99, "quantity": 2}),
        ("search", {"query": "wireless headphones", "results_count": 15}),
        ("purchase", {"order_id": "ord_001", "total": 129.97, "items": 3}),
        ("page_view", {"page": "/deals", "duration_sec": 120}),
        ("remove_from_cart", {"product_id": "p789", "price": 19.99}),
        ("wishlist_add", {"product_id": "p321", "price": 89.99}),
        ("review_view", {"product_id": "p123", "rating_shown": 4.5}),
    ]

    events = []
    for i in range(count):
        et, data = random.choice(event_types)
        events.append(Event(
            event_type=et,
            entity_id=entity_id,
            data={**data, "session_id": f"sess_{random.randint(1,5)}"},
        ))
    return events
