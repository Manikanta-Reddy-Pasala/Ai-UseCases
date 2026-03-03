# AI Data Pipeline

## Real-Time Events → Feature Engineering → Model Serving → A/B Testing

Complete ML pipeline that ingests user events, computes features in real-time, serves predictions from multiple models, and runs A/B tests to find the best model.

---

### The Pipeline

```
┌──────────────────────────────────────────────────────────────┐
│                      EVENT INGESTION                          │
│                                                               │
│   page_view ──┐                                               │
│   add_to_cart ┤                                               │
│   purchase ───┤──► Event Store ──► Entity Events              │
│   search ─────┤       │              (by user_id)             │
│   wishlist ───┘       │                                       │
│                       ▼                                       │
│              25 events/user                                   │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                    FEATURE ENGINEERING                         │
│                                                               │
│   15+ Features Computed:                                      │
│                                                               │
│   Count:    page_views=9, cart_adds=6, purchases=4            │
│   Ratios:   cart_to_view=0.67, purchase_to_view=0.44          │
│   Money:    cart_value=$389, avg_item=$65                      │
│   Engage:   browse_time=675s, avg_page=75s                    │
│   Sessions: unique_sessions=5                                 │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                    MODEL SERVING                              │
│                                                               │
│   ┌─────────────────┐    ┌─────────────────┐                 │
│   │  Model v1        │    │  Model v2        │                │
│   │  7 features      │    │  7 features      │                │
│   │  cart_ratio: 3.5 │    │  cart_ratio: 4.0 │                │
│   │  purchase: 2.0   │    │  browse_time:0.003│               │
│   │                  │    │  searches: 0.2   │                │
│   │  score: 0.999    │    │  score: 0.999    │                │
│   │  "likely_buyer"  │    │  "likely_buyer"  │                │
│   └────────┬─────────┘    └────────┬─────────┘                │
│            │                       │                          │
│            └───────────┬───────────┘                          │
│                        │                                      │
│              ┌─────────▼──────────┐                           │
│              │     A/B TEST       │                           │
│              │  Winner: v2        │                           │
│              │  (higher conf)     │                           │
│              └────────────────────┘                           │
└──────────────────────────────────────────────────────────────┘
```

### Key Numbers

| Metric | Value |
|--------|-------|
| Events ingested | 55 (test run) |
| Features per entity | 15 |
| Prediction latency | 0.14ms |
| Active models | 2 (v1, v2) |
| A/B test winner | v2 (higher confidence) |

### Quick Demo

```bash
python3 main.py   # Port 8004

# Full pipeline in 4 calls:
curl -X POST "localhost:8004/api/v1/events/generate?entity_id=user_001&count=30"
curl localhost:8004/api/v1/features/user_001
curl -X POST "localhost:8004/api/v1/predict/user_001"
curl -X POST "localhost:8004/api/v1/ab-test/user_001"
```

### Live: http://135.181.93.114:8004

---

**Detailed Docs**: [ARCHITECTURE.md](ARCHITECTURE.md) | [IMPLEMENTATION.md](IMPLEMENTATION.md)
