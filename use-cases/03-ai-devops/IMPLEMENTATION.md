# Implementation Details — AI-Powered DevOps Platform

## Project Structure

```
03-ai-devops/
├── main.py                  # FastAPI app, routes, live dashboard
├── config.py                # Environment config
├── analyzers/
│   ├── log_analyzer.py      # 10-pattern log analysis + root cause
│   └── metric_analyzer.py   # psutil metrics + health scoring
├── remediation/
│   └── actions.py           # 7 safe actions with dry-run
├── models/
│   └── schemas.py           # Pydantic: Anomaly, MetricSnapshot, etc.
├── data/
│   └── sample-logs.txt      # 20-line sample with multiple issues
├── .env.example
└── requirements.txt
```

## Key Code

### Log Analyzer (`analyzers/log_analyzer.py`)

```python
ERROR_PATTERNS = [
    (r'(?i)out\s*of\s*memory|OOM|oom.kill', Severity.CRITICAL, "Memory", "Out of memory"),
    (r'(?i)connection\s*(refused|timed?\s*out)', Severity.WARNING, "Network", "Connection issue"),
    (r'(?i)(500|502|503|504)\s*(internal|bad)', Severity.CRITICAL, "HTTP", "Server error"),
    # ... 7 more patterns
]

def analyze_logs_pattern(logs: str, service: str) -> LogAnalysisResponse:
    for line in logs.split("\n"):
        for pattern, severity, category, desc in ERROR_PATTERNS:
            if re.search(pattern, line):
                anomalies.append(Anomaly(severity, category, desc, log_line=line))
                break  # One match per line

    root_cause = _determine_root_cause(anomalies)  # Priority-based
    actions = [_get_recommendation(a.category) for a in anomalies]  # Specific commands
```

### Metric Analyzer (`analyzers/metric_analyzer.py`)

```python
def collect_metrics() -> MetricSnapshot:
    return MetricSnapshot(
        cpu_percent=psutil.cpu_percent(interval=1),
        memory_percent=psutil.virtual_memory().percent,
        disk_percent=psutil.disk_usage("/").percent,
        load_avg_1m=psutil.getloadavg()[0],
        processes=len(psutil.pids()),
    )

def analyze_metrics(metrics) -> MetricAnalysis:
    health_score = 100
    if metrics.cpu_percent > 90:    health_score -= 30   # CRITICAL
    elif metrics.cpu_percent > 70:  health_score -= 15   # WARNING
    # ... similar for memory, disk, load
```

### Remediation Actions (`remediation/actions.py`)

```python
SAFE_ACTIONS = {
    "clear_tmp": RemediationAction(
        command="find /tmp -type f -mtime +7 -delete",
        risk_level="low",
    ),
    "check_processes": RemediationAction(
        command="ps aux --sort=-%mem | head -15",
        risk_level="low",
    ),
    # ... 5 more actions
}

async def execute_action(name: str, dry_run: bool = True):
    if dry_run:
        return f"[DRY RUN] Would execute: {action.command}"
    proc = await asyncio.create_subprocess_shell(action.command, ...)
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
```

## API Reference

| Endpoint | Method | Input | Output |
|----------|--------|-------|--------|
| `/api/v1/analyze-logs` | POST | `{logs, service_name}` | `{anomalies[], root_cause, actions[]}` |
| `/api/v1/metrics` | GET | - | `{cpu, memory, disk, load, ...}` |
| `/api/v1/metrics/analyze` | GET | - | `{metrics, health_score, warnings[]}` |
| `/api/v1/remediation` | GET | - | List of 7 available actions |
| `/api/v1/remediation/{name}` | POST | `?dry_run=true` | `{action, result, executed}` |

## Test Results

```
✓ Health: OK, system_health=100
✓ Log analysis: 6 anomalies (2 CRIT OOM + 4 WARN)
✓ Root cause: "Memory exhaustion - cascading failures"
✓ Metrics: real-time CPU/MEM/DISK
✓ 7 remediation actions available
✓ Dry run works correctly
```
