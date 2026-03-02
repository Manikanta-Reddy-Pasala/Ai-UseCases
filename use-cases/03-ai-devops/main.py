"""AI-Powered DevOps Platform - Log Analysis, Metrics, and Auto-Remediation.

Built with:
- Pattern-based + AI log analysis
- Real-time system metrics (psutil)
- Predefined safe remediation actions
- Claude SDK for deep root cause analysis
- FastAPI REST API with interactive dashboard

Usage:
    DEVOPS_MODE=demo python3 main.py      # Port 8002

API:
    POST /api/v1/analyze-logs       - Analyze log text
    GET  /api/v1/metrics            - Current system metrics
    GET  /api/v1/metrics/analyze    - Metrics with AI analysis
    GET  /api/v1/remediation        - List available actions
    POST /api/v1/remediation/{name} - Execute a remediation action
    GET  /api/v1/health             - Health check
    GET  /                          - Dashboard
"""

import logging
import time

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from config import config
from models.schemas import (
    HealthResponse, LogAnalysisRequest, LogAnalysisResponse, MetricAnalysis
)
from analyzers.log_analyzer import analyze_logs_pattern
from analyzers.metric_analyzer import analyze_metrics, collect_metrics
from remediation.actions import execute_action, get_available_actions

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI-Powered DevOps Platform",
    description="Log analysis, system metrics, and auto-remediation",
    version="1.0.0",
)


@app.on_event("startup")
async def startup():
    mode = "REAL (Claude API)" if config.is_real_mode else "DEMO (pattern matching)"
    logger.info(f"AI DevOps Platform started in {mode} mode on port {config.PORT}")


@app.post("/api/v1/analyze-logs", response_model=LogAnalysisResponse)
async def analyze_logs(request: LogAnalysisRequest):
    """Analyze application logs for anomalies and root causes."""
    start = time.time()
    result = analyze_logs_pattern(request.logs, request.service_name)
    result.duration_ms = int((time.time() - start) * 1000)
    return result


@app.get("/api/v1/metrics")
async def get_metrics():
    """Get current system metrics."""
    return collect_metrics()


@app.get("/api/v1/metrics/analyze", response_model=MetricAnalysis)
async def analyze_system_metrics():
    """Get system metrics with health analysis and recommendations."""
    return analyze_metrics()


@app.get("/api/v1/remediation")
async def list_remediation_actions():
    """List available auto-remediation actions."""
    return get_available_actions()


@app.post("/api/v1/remediation/{action_name}")
async def run_remediation(action_name: str, dry_run: bool = True):
    """Execute a remediation action (dry_run=true by default for safety)."""
    return await execute_action(action_name, dry_run=dry_run)


@app.get("/api/v1/health", response_model=HealthResponse)
async def health():
    analysis = analyze_metrics()
    return HealthResponse(status="ok", mode=config.DEVOPS_MODE, system_health=analysis.health_score)


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    mode = "REAL" if config.is_real_mode else "DEMO"
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>AI DevOps Dashboard</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}}
.c{{max-width:1000px;margin:0 auto;padding:2rem}}
h1{{font-size:2rem;color:#34d399;margin-bottom:.5rem}}
.sub{{color:#94a3b8;margin-bottom:2rem}}
.badge{{display:inline-block;padding:2px 10px;border-radius:12px;font-size:.75rem;
       background:{('#22c55e' if mode=='REAL' else '#eab308')};color:#000;font-weight:600}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:1.5rem}}
.card{{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:1rem;text-align:center}}
.card .val{{font-size:1.8rem;font-weight:700;color:#34d399}}.card .lbl{{font-size:.8rem;color:#94a3b8}}
.card.warn .val{{color:#eab308}}.card.crit .val{{color:#ef4444}}
.section{{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:1.5rem;margin-bottom:1.5rem}}
h2{{color:#34d399;margin-bottom:1rem;font-size:1.1rem}}
textarea{{width:100%;height:200px;padding:.75rem;border:1px solid #334155;border-radius:8px;
         background:#0f172a;color:#e2e8f0;font-family:monospace;font-size:.85rem;resize:vertical}}
button{{padding:.5rem 1.5rem;border:none;border-radius:8px;background:#059669;color:white;
       font-size:.9rem;cursor:pointer;font-weight:600;margin:.5rem .5rem 0 0}}
button:hover{{background:#047857}}button.warn{{background:#d97706}}button.danger{{background:#dc2626}}
#output{{background:#0f172a;border:1px solid #334155;border-radius:8px;padding:1rem;
        min-height:100px;white-space:pre-wrap;font-family:monospace;font-size:.85rem;margin-top:1rem}}
</style></head>
<body><div class="c">
<h1>AI DevOps Dashboard <span class="badge">{mode}</span></h1>
<p class="sub">Real-time system monitoring, log analysis, and auto-remediation</p>

<div class="grid" id="metrics">
<div class="card"><div class="val" id="cpu">-</div><div class="lbl">CPU %</div></div>
<div class="card"><div class="val" id="mem">-</div><div class="lbl">Memory %</div></div>
<div class="card"><div class="val" id="disk">-</div><div class="lbl">Disk %</div></div>
<div class="card"><div class="val" id="health">-</div><div class="lbl">Health Score</div></div>
</div>
<div id="warnings" style="margin-bottom:1rem;color:#eab308;font-size:.85rem;"></div>

<div class="section">
<h2>Log Analysis</h2>
<textarea id="logs" placeholder="Paste application logs here...">2026-03-02 10:01:45 ERROR [payment-service] Connection refused to database host db-primary:5432
2026-03-02 10:02:15 ERROR [order-service] java.lang.OutOfMemoryError: Java heap space
2026-03-02 10:02:16 FATAL [order-service] OOM killer terminated process PID 4523
2026-03-02 10:02:30 ERROR [api-gateway] 502 Bad Gateway: upstream order-service connection reset
2026-03-02 10:01:31 WARN [user-service] Slow query detected: SELECT * FROM users WHERE id=1234 took 2.3s</textarea>
<button onclick="analyzeLogs()">Analyze Logs</button>
<button class="warn" onclick="loadSample()">Load Sample Logs</button>
</div>

<div class="section">
<h2>Remediation Actions</h2>
<button onclick="runAction('check_processes')">Check Processes</button>
<button onclick="runAction('check_disk')">Check Disk</button>
<button onclick="runAction('check_connections')">Check Network</button>
<button class="warn" onclick="runAction('clear_cache')">Clear Cache</button>
<button class="danger" onclick="runAction('clear_tmp',false)">Clean Temp (Execute)</button>
</div>

<div id="output">Dashboard ready. Metrics refresh every 10 seconds.</div>
</div>

<script>
async function refreshMetrics(){{
  try{{
    const r=await fetch('/api/v1/metrics/analyze');const d=await r.json();
    document.getElementById('cpu').textContent=d.metrics.cpu_percent+'%';
    document.getElementById('mem').textContent=d.metrics.memory_percent+'%';
    document.getElementById('disk').textContent=d.metrics.disk_percent+'%';
    document.getElementById('health').textContent=d.health_score;
    const cards=document.querySelectorAll('.card');
    cards.forEach(c=>c.classList.remove('warn','crit'));
    if(d.metrics.cpu_percent>70)cards[0].classList.add(d.metrics.cpu_percent>90?'crit':'warn');
    if(d.metrics.memory_percent>75)cards[1].classList.add(d.metrics.memory_percent>90?'crit':'warn');
    if(d.metrics.disk_percent>75)cards[2].classList.add(d.metrics.disk_percent>90?'crit':'warn');
    if(d.health_score<80)cards[3].classList.add(d.health_score<50?'crit':'warn');
    document.getElementById('warnings').innerHTML=d.warnings.map(w=>'&#9888; '+w).join('<br>');
  }}catch(e){{}}
}}

async function analyzeLogs(){{
  const logs=document.getElementById('logs').value;
  if(!logs)return;
  document.getElementById('output').textContent='Analyzing logs...';
  try{{
    const r=await fetch('/api/v1/analyze-logs',{{method:'POST',headers:{{'Content-Type':'application/json'}},
      body:JSON.stringify({{logs,service_name:'multi-service'}})}});
    const d=await r.json();
    let out=`Log Analysis: ${{d.total_lines}} lines | ${{d.anomalies.length}} anomalies | ${{d.duration_ms}}ms\\n${'='.repeat(60)}\\n\\n`;
    out+=`Summary: ${{d.summary}}\\n\\nRoot Cause: ${{d.root_cause}}\\n\\nAnomalies:\\n`;
    d.anomalies.forEach((a,i)=>out+=`  ${{i+1}}. [${{a.severity.toUpperCase()}}] ${{a.category}}: ${{a.description}}\\n     Log: ${{a.log_line.substring(0,120)}}\\n     Fix: ${{a.recommendation}}\\n\\n`);
    out+=`\\nRecommended Actions:\\n`;d.recommended_actions.forEach((a,i)=>out+=`  ${{i+1}}. ${{a}}\\n`);
    document.getElementById('output').textContent=out;
  }}catch(e){{document.getElementById('output').textContent='Error: '+e.message;}}
}}

async function runAction(name,dry=true){{
  document.getElementById('output').textContent='Executing: '+name+'...';
  try{{
    const r=await fetch('/api/v1/remediation/'+name+'?dry_run='+dry,{{method:'POST'}});
    const d=await r.json();
    let out=`Action: ${{d.action}}\\nRisk: ${{d.risk_level}}\\nCommand: ${{d.command}}\\nExecuted: ${{d.executed}}\\n\\nResult:\\n${{d.result}}`;
    document.getElementById('output').textContent=out;
  }}catch(e){{document.getElementById('output').textContent='Error: '+e.message;}}
}}

async function loadSample(){{
  try{{const r=await fetch('/api/v1/health');document.getElementById('logs').value=`2026-03-02 10:01:45 ERROR [payment-service] Connection refused to database host db-primary:5432
2026-03-02 10:01:51 FATAL [payment-service] All database connection attempts exhausted
2026-03-02 10:02:00 ERROR [api-gateway] 503 Service Unavailable: payment-service not responding
2026-03-02 10:02:05 WARN [monitoring] CPU usage spike detected: 92% on node worker-3
2026-03-02 10:02:15 ERROR [order-service] java.lang.OutOfMemoryError: Java heap space
2026-03-02 10:02:16 FATAL [order-service] OOM killer terminated process PID 4523
2026-03-02 10:02:30 ERROR [api-gateway] 502 Bad Gateway: upstream order-service connection reset
2026-03-02 10:01:31 WARN [user-service] Slow query detected: SELECT * FROM users took 2.3s
2026-03-02 10:03:15 WARN [disk-monitor] Disk usage at 87% on /var/log partition`;}}catch(e){{}}
}}

refreshMetrics(); setInterval(refreshMetrics, 10000);
</script></body></html>"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=False)
