from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class LogEntry(BaseModel):
    timestamp: str = ""
    level: str = "INFO"
    service: str = "unknown"
    message: str = ""


class LogAnalysisRequest(BaseModel):
    logs: str  # Raw log text or list of log lines
    service_name: str = "unknown"


class Anomaly(BaseModel):
    severity: Severity
    category: str
    description: str
    affected_service: str = ""
    log_line: str = ""
    recommendation: str = ""


class LogAnalysisResponse(BaseModel):
    service: str
    total_lines: int = 0
    anomalies: list[Anomaly] = []
    summary: str = ""
    root_cause: str = ""
    recommended_actions: list[str] = []
    duration_ms: int = 0


class MetricSnapshot(BaseModel):
    cpu_percent: float = 0
    memory_percent: float = 0
    disk_percent: float = 0
    load_avg_1m: float = 0
    load_avg_5m: float = 0
    load_avg_15m: float = 0
    net_bytes_sent: int = 0
    net_bytes_recv: int = 0
    uptime_seconds: float = 0
    processes: int = 0
    open_files: int = 0


class MetricAnalysis(BaseModel):
    metrics: MetricSnapshot
    health_score: int = 100  # 0-100
    status: str = "healthy"
    warnings: list[str] = []
    recommendations: list[str] = []


class RemediationAction(BaseModel):
    action: str
    command: str = ""
    risk_level: str = "low"
    description: str = ""
    executed: bool = False
    result: str = ""


class IncidentReport(BaseModel):
    incident_id: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    severity: Severity = Severity.INFO
    title: str = ""
    description: str = ""
    root_cause: str = ""
    affected_services: list[str] = []
    actions_taken: list[RemediationAction] = []
    status: str = "open"


class HealthResponse(BaseModel):
    status: str = "ok"
    mode: str = "demo"
    system_health: int = 100
