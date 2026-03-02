# Use Case 3: AI-Powered DevOps

## Intelligent Log Analysis, Metrics Monitoring, and Auto-Remediation

AI-powered DevOps platform that analyzes logs for anomalies, monitors system metrics, provides root cause analysis, and offers safe auto-remediation actions.

## Architecture

```
                         ┌─────────────────┐
                         │  FastAPI Server  │
                         │   Port 8002      │
                         └────────┬────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
    ┌─────────▼──────┐  ┌────────▼────────┐  ┌──────▼────────┐
    │  Log Analyzer   │  │ Metric Analyzer │  │ Remediation   │
    │ (Pattern+AI)    │  │   (psutil)      │  │  (Actions)    │
    └────────┬───────┘  └────────┬────────┘  └──────┬────────┘
             │                   │                   │
    ┌────────▼───────┐  ┌────────▼────────┐  ┌──────▼────────┐
    │ 10 Error       │  │ CPU/Mem/Disk    │  │ 7 Safe        │
    │ Patterns       │  │ Load/Network    │  │ Actions       │
    │ + Claude AI    │  │ Health Score    │  │ + Dry Run     │
    └────────────────┘  └─────────────────┘  └───────────────┘
```

## Key Features

### Log Analysis (Pattern + AI)
- 10 built-in error patterns: OOM, connection errors, disk full, crashes, timeouts, auth failures, HTTP 5xx, exceptions, CPU spikes, DB issues
- Automatic severity classification (Critical/Warning/Info)
- Root cause analysis with cascading failure detection
- Actionable fix recommendations with specific commands

### System Metrics
- Real-time CPU, Memory, Disk, Load Average via psutil
- Network I/O, process count, uptime tracking
- Health score (0-100) with automatic status classification
- Threshold-based warnings with specific recommendations

### Auto-Remediation
- 7 predefined safe actions with risk levels
- Dry-run mode by default (safety first)
- Actions: clear_tmp, clear_logs, clear_cache, check_processes, check_disk, check_connections, restart_service

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/analyze-logs` | Analyze log text for anomalies |
| GET | `/api/v1/metrics` | Raw system metrics |
| GET | `/api/v1/metrics/analyze` | Metrics with health analysis |
| GET | `/api/v1/remediation` | List available actions |
| POST | `/api/v1/remediation/{name}` | Execute action (dry_run default) |
| GET | `/` | Interactive dashboard |

## Quick Start
```bash
pip install -r requirements.txt
python3 main.py    # Port 8002
```

## Tested & Running
```
VM: 135.181.93.114:8002
Log Analysis: 20 lines → 9 anomalies (2 critical OOM), root cause identified in 2ms
Metrics: Real-time CPU/Memory/Disk with health scoring
```
