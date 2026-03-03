# Implementation Details — AI Data Pipeline

## Project Structure

```
05-ai-data-pipeline/
├── main.py                  # FastAPI app, routes, dashboard
├── config.py                # Port, feature store type
├── pipeline/
│   └── ingestion.py         # Event store, sample generator
├── features/
│   └── store.py             # Feature computation (15+ features)
├── serving/
│   └── model_server.py      # Model registry, predict, A/B test
├── models/
│   └── schemas.py           # Event, FeatureVector, Prediction, etc.
└── requirements.txt
```

## Key Code

### Event Ingestion (`pipeline/ingestion.py`)

```python
_events: list[Event] = []
_entity_events: dict[str, list[Event]] = defaultdict(list)

def ingest_event(event: Event):
    _events.append(event)
    _entity_events[event.entity_id].append(event)

def generate_sample_events(entity_id, count=20):
    # Random e-commerce events: page_view, add_to_cart, purchase, search...
    event_types = [
        ("page_view", {"page": "/products", "duration_sec": 45}),
        ("add_to_cart", {"product_id": "p123", "price": 29.99, "quantity": 1}),
        ("purchase", {"order_id": "ord_001", "total": 129.97, "items": 3}),
        ...
    ]
```

### Feature Store (`features/store.py`)

```python
def compute_features(entity_id: str) -> FeatureVector:
    events = get_entity_events(entity_id, last_n=200)

    features = {}
    # Count features
    features["page_views"] = float(event_types.get("page_view", 0))
    features["cart_adds"] = float(event_types.get("add_to_cart", 0))

    # Ratio features
    features["cart_to_view_ratio"] = cart_adds / page_views

    # Monetary features
    features["total_cart_value"] = sum(e.data["price"] * e.data["quantity"]
                                       for e in events if e.event_type == "add_to_cart")

    # Engagement features
    features["avg_page_duration_sec"] = total_duration / page_views

    # Session features
    features["unique_sessions"] = len({e.data.get("session_id") for e in events})

    return FeatureVector(entity_id=entity_id, features=features)
```

### Model Server (`serving/model_server.py`)

```python
def predict(entity_id, model_name="purchase_propensity_v1"):
    model = _models[model_name]
    fv = compute_features(entity_id)

    # Logistic regression: sigmoid(sum(weight * feature))
    logit = sum(weight * fv.features.get(fname, 0)
                for fname, weight in model.weights.items())
    score = 1 / (1 + np.exp(-logit))
    label = "likely_buyer" if score >= model.threshold else "browser"
    confidence = abs(score - 0.5) * 2

    return Prediction(score=score, label=label, confidence=confidence)

def ab_test(entity_id, model_a, model_b):
    pred_a = predict(entity_id, model_a)
    pred_b = predict(entity_id, model_b)
    winner = model_a if pred_a.confidence >= pred_b.confidence else model_b
    return ABTestResult(winner=winner, prediction_a=pred_a, prediction_b=pred_b)
```

## API Reference

| Endpoint | Method | Input | Output |
|----------|--------|-------|--------|
| `/api/v1/events` | POST | Event JSON | Stored event |
| `/api/v1/events/generate` | POST | `?entity_id=&count=` | `{events_generated}` |
| `/api/v1/features/{id}` | GET | - | `{features: {15 keys}}` |
| `/api/v1/predict/{id}` | POST | `?model_name=` | `{score, label, confidence, latency_ms}` |
| `/api/v1/ab-test/{id}` | POST | `?model_a=&model_b=` | `{winner, prediction_a, prediction_b}` |
| `/api/v1/models` | GET | - | List of ModelConfig |
| `/api/v1/stats` | GET | - | `{events, features, predictions, models}` |

## Test Results

```
✓ Health: OK, 2 models active
✓ Ingest: 25 events generated
✓ Features: 15 computed for test_user
✓ Predict v1: likely_buyer, score=0.999
✓ Predict v2: likely_buyer, score=0.999
✓ A/B test: winner=purchase_propensity_v2
✓ Pipeline stats: 55 events, 7 predictions
```
