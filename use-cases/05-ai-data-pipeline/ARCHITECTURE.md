# Architecture — AI Data Pipeline

## System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     FastAPI Server (:8004)                        │
│                                                                   │
│  POST /api/v1/events ────────────► Single Event Ingest           │
│  POST /api/v1/events/batch ──────► Batch Ingest                  │
│  POST /api/v1/events/generate ───► Sample Event Generator        │
│  GET  /api/v1/features/{id} ─────► Feature Computation           │
│  POST /api/v1/predict/{id} ──────► Model Prediction              │
│  POST /api/v1/ab-test/{id} ──────► A/B Test (v1 vs v2)          │
│  GET  /api/v1/models ────────────► Model Registry                │
│  GET  /api/v1/stats ─────────────► Pipeline Statistics           │
│  GET  / ─────────────────────────► Interactive Dashboard         │
└───────────┬─────────────┬──────────────┬─────────────────────────┘
            │             │              │
 ┌──────────▼──────┐ ┌────▼────────┐ ┌───▼──────────────┐
 │   INGESTION     │ │  FEATURE    │ │  MODEL SERVING   │
 │                 │ │  STORE      │ │                  │
 │ Event Store     │ │             │ │ ┌──────────────┐ │
 │ (in-memory)     │ │ Compute 15+ │ │ │ Model v1     │ │
 │                 │ │ features    │ │ │ logistic_reg │ │
 │ ┌─────────────┐ │ │ from event  │ │ │ 7 weights    │ │
 │ │ _events[]   │ │ │ history     │ │ │ thresh: 0.50 │ │
 │ │ list of all │ │ │             │ │ └──────────────┘ │
 │ │ events      │ │ │ Categories: │ │                  │
 │ └─────────────┘ │ │ • Count     │ │ ┌──────────────┐ │
 │                 │ │ • Ratio     │ │ │ Model v2     │ │
 │ ┌─────────────┐ │ │ • Monetary  │ │ │ logistic_reg │ │
 │ │_entity_evts │ │ │ • Engagement│ │ │ 7 weights    │ │
 │ │ dict by     │ │ │ • Session   │ │ │ thresh: 0.45 │ │
 │ │ entity_id   │ │ │             │ │ └──────────────┘ │
 │ └─────────────┘ │ │ Cache:      │ │                  │
 │                 │ │ _feature_   │ │ ┌──────────────┐ │
 │ Sample Events:  │ │ cache{}     │ │ │ A/B Testing  │ │
 │ • page_view     │ │             │ │ │ Compare v1   │ │
 │ • add_to_cart   │ │             │ │ │ vs v2 by     │ │
 │ • purchase      │ │             │ │ │ confidence   │ │
 │ • search        │ │             │ │ └──────────────┘ │
 │ • wishlist_add  │ │             │ │                  │
 │ • remove_cart   │ │             │ │ Prediction:      │
 │ • review_view   │ │             │ │ sigmoid(Σ w*f)   │
 └─────────────────┘ └─────────────┘ └──────────────────┘
```

## Feature Engineering Detail

```
Event History for user_001:
┌──────────────────────────────────────────┐
│ page_view (9x) │ add_to_cart (6x)       │
│ purchase  (4x) │ search (5x)            │
│ remove_cart(3x)│ wishlist_add (1x)      │
└──────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────┐
│         15 COMPUTED FEATURES             │
│                                          │
│  COUNT FEATURES:                         │
│  ├── total_events: 30                    │
│  ├── page_views: 9                       │
│  ├── cart_adds: 6                        │
│  ├── purchases: 4                        │
│  ├── searches: 5                         │
│  └── cart_removes: 3                     │
│                                          │
│  RATIO FEATURES:                         │
│  ├── cart_to_view_ratio: 0.6667          │
│  └── purchase_to_view_ratio: 0.4444      │
│                                          │
│  MONETARY FEATURES:                      │
│  ├── total_cart_value: $389.91           │
│  ├── total_purchase_value: $519.88       │
│  └── avg_cart_item_price: $64.98         │
│                                          │
│  ENGAGEMENT FEATURES:                    │
│  ├── total_browse_time_sec: 675          │
│  └── avg_page_duration_sec: 75           │
│                                          │
│  SESSION FEATURES:                       │
│  └── unique_sessions: 5                  │
└──────────────────────────────────────────┘
```

## Model Serving: Logistic Regression

```
score = sigmoid(Σ weight_i × feature_i)

Model v1 weights:          Model v2 weights:
  cart_to_view:    3.5       cart_to_view:    4.0
  purchase_to_view:2.0       purchase_to_view:1.5
  total_cart_value:0.005     total_cart_value: 0.008
  avg_page_dur:   0.02      avg_page_dur:    0.015
  cart_adds:      0.3       cart_adds:       0.4
  unique_sessions:0.2       total_browse:    0.003
  wishlist_adds:  0.5       searches:        0.2

Threshold: 0.50              Threshold: 0.45

label = "likely_buyer" if score >= threshold else "browser"
confidence = |score - 0.5| × 2   (distance from boundary)
```

## A/B Test Logic

```
Predict with both models → Compare confidence → Winner

v1: score=0.999 conf=0.999  ──┐
                               ├──► Winner: v2 (conf 1.0 > 0.999)
v2: score=0.999 conf=1.000  ──┘
```
