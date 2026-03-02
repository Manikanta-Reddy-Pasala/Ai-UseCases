"""System metrics collection and analysis."""

from __future__ import annotations

import logging
import time

import psutil

from models.schemas import MetricAnalysis, MetricSnapshot

logger = logging.getLogger(__name__)


def collect_metrics() -> MetricSnapshot:
    """Collect current system metrics using psutil."""
    try:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        load = psutil.getloadavg()
        net = psutil.net_io_counters()
        boot = psutil.boot_time()

        return MetricSnapshot(
            cpu_percent=cpu,
            memory_percent=mem.percent,
            disk_percent=disk.percent,
            load_avg_1m=load[0],
            load_avg_5m=load[1],
            load_avg_15m=load[2],
            net_bytes_sent=net.bytes_sent,
            net_bytes_recv=net.bytes_recv,
            uptime_seconds=time.time() - boot,
            processes=len(psutil.pids()),
            open_files=sum(len(p.open_files()) for p in psutil.process_iter(['open_files']) if p.info['open_files']) if False else 0,
        )
    except Exception as e:
        logger.error(f"Metric collection error: {e}")
        return MetricSnapshot()


def analyze_metrics(metrics: MetricSnapshot | None = None) -> MetricAnalysis:
    """Analyze system metrics and generate health assessment."""
    if metrics is None:
        metrics = collect_metrics()

    warnings = []
    recommendations = []
    health_score = 100

    # CPU analysis
    if metrics.cpu_percent > 90:
        warnings.append(f"CRITICAL: CPU at {metrics.cpu_percent}%")
        recommendations.append("Scale horizontally or identify CPU-intensive processes: top -o %CPU")
        health_score -= 30
    elif metrics.cpu_percent > 70:
        warnings.append(f"WARNING: CPU at {metrics.cpu_percent}%")
        recommendations.append("Monitor CPU trend, consider load balancing")
        health_score -= 15

    # Memory analysis
    if metrics.memory_percent > 90:
        warnings.append(f"CRITICAL: Memory at {metrics.memory_percent}%")
        recommendations.append("Free memory: check for leaks, restart services, or scale up")
        health_score -= 30
    elif metrics.memory_percent > 75:
        warnings.append(f"WARNING: Memory at {metrics.memory_percent}%")
        recommendations.append("Monitor memory growth, review service memory limits")
        health_score -= 10

    # Disk analysis
    if metrics.disk_percent > 90:
        warnings.append(f"CRITICAL: Disk at {metrics.disk_percent}%")
        recommendations.append("Free disk space: clean logs, remove temp files: du -sh /var/log/* | sort -rh | head")
        health_score -= 25
    elif metrics.disk_percent > 75:
        warnings.append(f"WARNING: Disk at {metrics.disk_percent}%")
        recommendations.append("Plan disk cleanup or expansion")
        health_score -= 10

    # Load average
    import os
    cpu_count = os.cpu_count() or 1
    if metrics.load_avg_1m > cpu_count * 2:
        warnings.append(f"WARNING: Load average {metrics.load_avg_1m:.1f} (CPUs: {cpu_count})")
        recommendations.append("System overloaded: check for blocking I/O or too many processes")
        health_score -= 15

    health_score = max(0, health_score)
    status = "healthy" if health_score >= 80 else "degraded" if health_score >= 50 else "critical"

    return MetricAnalysis(
        metrics=metrics,
        health_score=health_score,
        status=status,
        warnings=warnings,
        recommendations=recommendations,
    )
