# AI-Powered DevOps Platform

## Intelligent Log Analysis, Metrics Monitoring & Auto-Remediation

Detect production issues before users do. This platform analyzes logs for anomalies, monitors system health in real-time, identifies root causes, and offers safe one-click remediation actions.

---

### How It Works

```
┌──────────────────────────────────────────────────────────────┐
│                    APPLICATION LOGS                            │
│                                                               │
│  ERROR [payment] Connection refused to db:5432                │
│  ERROR [order] OutOfMemoryError: Java heap space              │
│  FATAL [order] OOM killer terminated PID 4523                 │
│  ERROR [gateway] 502 Bad Gateway                              │
│  WARN  [user] Slow query took 2.3s                            │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────────┐
            │       PATTERN ANALYZER       │
            │                              │
            │  10 Detection Patterns:      │
            │  • OOM / Memory exhaustion   │
            │  • Connection refused/timeout │
            │  • HTTP 5xx errors           │
            │  • Disk full                 │
            │  • CPU spike                 │
            │  • Slow queries / deadlocks  │
            │  • Auth failures             │
            │  • Crashes / segfaults       │
            │  • Exceptions / tracebacks   │
            │  • Timeout / deadline        │
            └──────────┬───────────────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
   ┌──────────┐  ┌──────────┐  ┌──────────────┐
   │ ANOMALY  │  │  ROOT    │  │ RECOMMENDED  │
   │ LIST     │  │  CAUSE   │  │ ACTIONS      │
   │          │  │          │  │              │
   │ 6 found  │  │ Memory   │  │ • free -h    │
   │ 2 CRIT   │  │ exhaust  │  │ • top -o MEM │
   │ 4 WARN   │  │ cascade  │  │ • check heap │
   └──────────┘  └──────────┘  └──────────────┘

┌──────────────────────────────────────────────────────────────┐
│                   SYSTEM METRICS (real-time)                   │
│                                                               │
│   CPU: 12%  │  Memory: 21%  │  Disk: 72%  │  Health: 100    │
│   ████░░░░  │  ██░░░░░░░░░  │  ███████░░  │  ██████████     │
│                                                               │
│   Load Avg: 0.06  │  Processes: 224  │  Uptime: 21.2 days   │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                   AUTO-REMEDIATION                            │
│                                                               │
│   [Check Processes]  [Check Disk]  [Check Network]           │
│   [Clear Cache]      [Clean Temp]  [Truncate Logs]           │
│                                                               │
│   All actions: DRY RUN by default (safety first)             │
└──────────────────────────────────────────────────────────────┘
```

### Key Capabilities

| Feature | Details |
|---------|---------|
| **Log Analysis** | 10 pattern detectors, severity classification, root cause |
| **System Metrics** | CPU, Memory, Disk, Load, Network via psutil |
| **Health Scoring** | 0-100 score with threshold-based warnings |
| **Root Cause** | Cascading failure detection (OOM → service down → 502) |
| **Remediation** | 7 safe actions, dry-run default, risk-level tagged |
| **AI Analysis** | Claude SDK for deep log interpretation (real mode) |

### Live: http://135.181.93.114:8002

---

**Detailed Docs**: [ARCHITECTURE.md](ARCHITECTURE.md) | [IMPLEMENTATION.md](IMPLEMENTATION.md)
