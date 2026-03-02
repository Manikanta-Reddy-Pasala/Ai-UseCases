"""AI Data Pipeline - Event Ingestion, Feature Engineering, and Model Serving.

Full ML pipeline: events → features → predictions with A/B testing.

API:
    POST /api/v1/events           - Ingest event(s)
    POST /api/v1/events/generate  - Generate sample events
    GET  /api/v1/features/{id}    - Compute features for entity
    POST /api/v1/predict/{id}     - Get prediction for entity
    POST /api/v1/ab-test/{id}     - Run A/B test between models
    GET  /api/v1/models           - List active models
    GET  /api/v1/stats            - Pipeline statistics
    GET  /                        - Interactive demo
"""

import logging

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from config import config
from models.schemas import Event, HealthResponse, PipelineStats
from pipeline.ingestion import ingest_event, ingest_batch, get_stats as ingest_stats, generate_sample_events
from features.store import compute_features, get_stats as feature_stats
from serving.model_server import predict, ab_test, get_models, get_stats as serve_stats, init_models

logging.basicConfig(level=getattr(logging, config.LOG_LEVEL), format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Data Pipeline", version="1.0.0")


@app.on_event("startup")
async def startup():
    init_models()
    logger.info(f"AI Data Pipeline started on port {config.PORT}")


@app.post("/api/v1/events")
async def ingest(event: Event):
    return ingest_event(event)


@app.post("/api/v1/events/batch")
async def ingest_events_batch(events: list[Event]):
    return {"ingested": ingest_batch(events)}


@app.post("/api/v1/events/generate")
async def generate_events(entity_id: str = "user_001", count: int = 20):
    events = generate_sample_events(entity_id, count)
    ingested = ingest_batch(events)
    return {"entity_id": entity_id, "events_generated": ingested}


@app.get("/api/v1/features/{entity_id}")
async def get_features(entity_id: str):
    return compute_features(entity_id)


@app.post("/api/v1/predict/{entity_id}")
async def get_prediction(entity_id: str, model_name: str = "purchase_propensity_v1"):
    return predict(entity_id, model_name)


@app.post("/api/v1/ab-test/{entity_id}")
async def run_ab_test(entity_id: str,
                      model_a: str = "purchase_propensity_v1",
                      model_b: str = "purchase_propensity_v2"):
    return ab_test(entity_id, model_a, model_b)


@app.get("/api/v1/models")
async def list_models():
    return get_models()


@app.get("/api/v1/stats", response_model=PipelineStats)
async def pipeline_stats():
    i = ingest_stats()
    f = feature_stats()
    s = serve_stats()
    return PipelineStats(
        events_ingested=i["total_ingested"],
        features_computed=f["features_computed"],
        predictions_served=s["total_predictions"],
        active_models=s["active_models"],
        avg_prediction_ms=s["avg_prediction_ms"],
    )


@app.get("/api/v1/health", response_model=HealthResponse)
async def health():
    i = ingest_stats()
    s = serve_stats()
    return HealthResponse(status="ok", events_ingested=i["total_ingested"], models_active=s["active_models"])


@app.get("/", response_class=HTMLResponse)
async def demo():
    return """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>AI Data Pipeline</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}
.c{max-width:1000px;margin:0 auto;padding:2rem}
h1{font-size:2rem;color:#06b6d4;margin-bottom:.5rem}
.sub{color:#94a3b8;margin-bottom:2rem}
.grid{display:grid;grid-template-columns:repeat(5,1fr);gap:.75rem;margin-bottom:1.5rem}
.card{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:.75rem;text-align:center}
.card .val{font-size:1.3rem;font-weight:700;color:#06b6d4}.card .lbl{font-size:.7rem;color:#94a3b8}
.section{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:1.5rem;margin-bottom:1rem}
h2{color:#06b6d4;margin-bottom:.75rem;font-size:1rem}
button{padding:.5rem 1rem;border:none;border-radius:8px;background:#0891b2;color:white;
       font-size:.85rem;cursor:pointer;font-weight:600;margin:.25rem}
button:hover{background:#0e7490}
input{padding:.5rem;border:1px solid #334155;border-radius:6px;background:#0f172a;color:#e2e8f0;width:150px;margin:.25rem}
#output{background:#0f172a;border:1px solid #334155;border-radius:8px;padding:1rem;
        min-height:150px;white-space:pre-wrap;font-family:monospace;font-size:.8rem;margin-top:1rem}
</style></head>
<body><div class="c">
<h1>AI Data Pipeline</h1>
<p class="sub">Events → Feature Engineering → Model Serving → A/B Testing</p>

<div class="grid" id="stats">
<div class="card"><div class="val" id="sEvents">0</div><div class="lbl">Events</div></div>
<div class="card"><div class="val" id="sFeatures">0</div><div class="lbl">Features</div></div>
<div class="card"><div class="val" id="sPredictions">0</div><div class="lbl">Predictions</div></div>
<div class="card"><div class="val" id="sModels">0</div><div class="lbl">Models</div></div>
<div class="card"><div class="val" id="sLatency">0</div><div class="lbl">Avg ms</div></div>
</div>

<div class="section">
<h2>1. Ingest Events</h2>
<input type="text" id="entityId" value="user_001" placeholder="Entity ID">
<input type="number" id="eventCount" value="20" min="1" max="100" style="width:80px">
<button onclick="generateEvents()">Generate Events</button>
</div>

<div class="section">
<h2>2. Compute Features & Predict</h2>
<button onclick="getFeatures()">Get Features</button>
<button onclick="getPrediction('purchase_propensity_v1')">Predict (v1)</button>
<button onclick="getPrediction('purchase_propensity_v2')">Predict (v2)</button>
<button onclick="runABTest()">A/B Test (v1 vs v2)</button>
</div>

<div class="section">
<h2>3. Full Pipeline Demo</h2>
<button onclick="fullPipeline()">Run Full Pipeline: Ingest → Features → Predict → A/B Test</button>
</div>

<div id="output">Ready. Click "Generate Events" to start the pipeline demo.</div>
</div>

<script>
const eid=()=>document.getElementById('entityId').value||'user_001';

async function refreshStats(){
  try{const r=await fetch('/api/v1/stats');const d=await r.json();
  document.getElementById('sEvents').textContent=d.events_ingested;
  document.getElementById('sFeatures').textContent=d.features_computed;
  document.getElementById('sPredictions').textContent=d.predictions_served;
  document.getElementById('sModels').textContent=d.active_models;
  document.getElementById('sLatency').textContent=d.avg_prediction_ms;}catch(e){}
}

async function generateEvents(){
  const cnt=document.getElementById('eventCount').value;
  try{const r=await fetch(`/api/v1/events/generate?entity_id=${eid()}&count=${cnt}`,{method:'POST'});
  const d=await r.json();
  document.getElementById('output').textContent=`Generated ${d.events_generated} events for ${d.entity_id}`;
  refreshStats();}catch(e){document.getElementById('output').textContent='Error: '+e.message;}
}

async function getFeatures(){
  try{const r=await fetch(`/api/v1/features/${eid()}`);const d=await r.json();
  let out=`Features for ${d.entity_id}:\\n${'='.repeat(50)}\\n`;
  Object.entries(d.features).sort().forEach(([k,v])=>out+=`  ${k}: ${v}\\n`);
  document.getElementById('output').textContent=out;refreshStats();}catch(e){document.getElementById('output').textContent='Error: '+e.message;}
}

async function getPrediction(model){
  try{const r=await fetch(`/api/v1/predict/${eid()}?model_name=${model}`,{method:'POST'});
  const d=await r.json();
  let out=`Prediction: ${d.model_name} (${d.model_version})\\n${'='.repeat(50)}\\n`;
  out+=`Label: ${d.label}\\nScore: ${d.score}\\nConfidence: ${d.confidence}\\nLatency: ${d.latency_ms}ms\\n\\nFeatures Used:\\n`;
  Object.entries(d.features_used).forEach(([k,v])=>out+=`  ${k}: ${v}\\n`);
  document.getElementById('output').textContent=out;refreshStats();}catch(e){document.getElementById('output').textContent='Error: '+e.message;}
}

async function runABTest(){
  try{const r=await fetch(`/api/v1/ab-test/${eid()}`,{method:'POST'});const d=await r.json();
  let out=`A/B Test: ${d.model_a} vs ${d.model_b}\\n${'='.repeat(50)}\\n`;
  out+=`\\nModel A (${d.prediction_a.model_name}): score=${d.prediction_a.score} label=${d.prediction_a.label} conf=${d.prediction_a.confidence}`;
  out+=`\\nModel B (${d.prediction_b.model_name}): score=${d.prediction_b.score} label=${d.prediction_b.label} conf=${d.prediction_b.confidence}`;
  out+=`\\n\\nWinner: ${d.winner}`;
  document.getElementById('output').textContent=out;refreshStats();}catch(e){document.getElementById('output').textContent='Error: '+e.message;}
}

async function fullPipeline(){
  document.getElementById('output').textContent='Running full pipeline...\\n';
  const out=[];
  // 1. Generate events
  let r=await fetch(`/api/v1/events/generate?entity_id=${eid()}&count=30`,{method:'POST'});
  let d=await r.json();out.push(`1. INGEST: ${d.events_generated} events for ${d.entity_id}`);
  // 2. Compute features
  r=await fetch(`/api/v1/features/${eid()}`);d=await r.json();
  out.push(`\\n2. FEATURES: ${Object.keys(d.features).length} features computed`);
  Object.entries(d.features).slice(0,5).forEach(([k,v])=>out.push(`   ${k}: ${v}`));
  // 3. Predict v1
  r=await fetch(`/api/v1/predict/${eid()}?model_name=purchase_propensity_v1`,{method:'POST'});d=await r.json();
  out.push(`\\n3. PREDICT v1: ${d.label} (score: ${d.score}, conf: ${d.confidence}, ${d.latency_ms}ms)`);
  // 4. Predict v2
  r=await fetch(`/api/v1/predict/${eid()}?model_name=purchase_propensity_v2`,{method:'POST'});d=await r.json();
  out.push(`   PREDICT v2: ${d.label} (score: ${d.score}, conf: ${d.confidence}, ${d.latency_ms}ms)`);
  // 5. A/B test
  r=await fetch(`/api/v1/ab-test/${eid()}`,{method:'POST'});d=await r.json();
  out.push(`\\n4. A/B TEST: Winner = ${d.winner}`);
  document.getElementById('output').textContent=out.join('\\n');refreshStats();
}

refreshStats();setInterval(refreshStats,5000);
</script></body></html>"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=False)
