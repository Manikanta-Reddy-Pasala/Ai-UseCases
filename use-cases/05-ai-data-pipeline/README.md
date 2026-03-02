# Use Case 5: AI Data Pipeline

## Real-Time Event Ingestion, Feature Engineering, and Model Serving

Full ML pipeline demonstrating: event ingestion → feature computation → model serving with A/B testing. Simulates an e-commerce purchase propensity prediction system.

## Architecture

```
Events → Ingestion → Feature Store → Model Server → Predictions
  │          │             │              │              │
  │    Event Store    Compute 15+    2 Models       A/B Testing
  │   (in-memory)    features from   (logistic      (v1 vs v2)
  │                  event history    regression)
  │
  └── page_view, add_to_cart, purchase, search, wishlist, etc.
```

## Components

| Component | File | Purpose |
|-----------|------|---------|
| Event Ingestion | `pipeline/ingestion.py` | Ingest, store, generate sample events |
| Feature Store | `features/store.py` | Compute 15+ features from event history |
| Model Server | `serving/model_server.py` | Predictions with A/B testing |
| API | `main.py` | FastAPI with interactive dashboard |

## Features Computed (15+)

- **Count features**: page_views, cart_adds, purchases, searches
- **Ratio features**: cart_to_view_ratio, purchase_to_view_ratio
- **Monetary features**: total_cart_value, avg_cart_item_price
- **Engagement features**: total_browse_time, avg_page_duration
- **Session features**: unique_sessions

## Models

- **purchase_propensity_v1**: Logistic regression with 7 weighted features
- **purchase_propensity_v2**: Updated weights with browse time and search features
- A/B testing compares model confidence for winner selection

## Tested Results

```
VM: 135.181.93.114:8004
Events: 30 ingested → 15 features computed → prediction in 0.14ms
A/B Test: v1 vs v2, winner selected by confidence
Pipeline latency: <1ms end-to-end
```

## Quick Start
```bash
pip install -r requirements.txt
python3 main.py    # Port 8004

# Full pipeline test
curl -X POST "http://localhost:8004/api/v1/events/generate?entity_id=user_001&count=30"
curl http://localhost:8004/api/v1/features/user_001
curl -X POST "http://localhost:8004/api/v1/predict/user_001"
curl -X POST "http://localhost:8004/api/v1/ab-test/user_001"
```
