"""AI-powered log analysis - pattern detection, anomaly identification, root cause analysis."""

from __future__ import annotations

import re
import logging
from typing import Any

import anthropic

from config import config
from models.schemas import Anomaly, LogAnalysisResponse, Severity

logger = logging.getLogger(__name__)

# Known error patterns
ERROR_PATTERNS = [
    (r'(?i)out\s*of\s*memory|OOM|oom.kill', Severity.CRITICAL, "Memory", "Out of memory detected"),
    (r'(?i)connection\s*(refused|timed?\s*out|reset)', Severity.WARNING, "Network", "Connection issue detected"),
    (r'(?i)disk\s*(full|space|quota)', Severity.CRITICAL, "Disk", "Disk space issue"),
    (r'(?i)(segfault|segmentation\s*fault|core\s*dump)', Severity.CRITICAL, "Crash", "Process crash detected"),
    (r'(?i)(timeout|timed?\s*out|deadline\s*exceeded)', Severity.WARNING, "Timeout", "Timeout detected"),
    (r'(?i)(unauthorized|403|401|authentication\s*fail)', Severity.WARNING, "Auth", "Authentication failure"),
    (r'(?i)(500|502|503|504)\s*(internal|bad\s*gateway|unavailable|timeout)', Severity.CRITICAL, "HTTP", "Server error"),
    (r'(?i)exception|traceback|panic|fatal', Severity.WARNING, "Exception", "Exception/error detected"),
    (r'(?i)(cpu|load)\s*(high|spike|100%|threshold)', Severity.WARNING, "CPU", "High CPU/load detected"),
    (r'(?i)slow\s*query|query\s*timeout|deadlock', Severity.WARNING, "Database", "Database issue detected"),
]


def analyze_logs_pattern(logs: str, service: str) -> LogAnalysisResponse:
    """Analyze logs using pattern matching (works without API key)."""
    lines = [l.strip() for l in logs.strip().split("\n") if l.strip()]
    anomalies = []
    error_count = 0
    warn_count = 0

    for line in lines:
        for pattern, severity, category, desc in ERROR_PATTERNS:
            if re.search(pattern, line):
                anomalies.append(Anomaly(
                    severity=severity,
                    category=category,
                    description=desc,
                    affected_service=service,
                    log_line=line[:200],
                    recommendation=_get_recommendation(category),
                ))
                if severity == Severity.CRITICAL:
                    error_count += 1
                else:
                    warn_count += 1
                break  # One match per line

    # Count log levels
    info_lines = sum(1 for l in lines if re.search(r'(?i)\bINFO\b', l))
    error_lines = sum(1 for l in lines if re.search(r'(?i)\bERROR\b|\bFATAL\b', l))
    warn_lines = sum(1 for l in lines if re.search(r'(?i)\bWARN\b', l))

    summary = (
        f"Analyzed {len(lines)} log lines from '{service}': "
        f"{error_lines} errors, {warn_lines} warnings, {info_lines} info. "
        f"Found {len(anomalies)} anomalies ({error_count} critical, {warn_count} warnings)."
    )

    # Basic root cause analysis
    root_cause = _determine_root_cause(anomalies)

    return LogAnalysisResponse(
        service=service,
        total_lines=len(lines),
        anomalies=anomalies[:20],  # Limit
        summary=summary,
        root_cause=root_cause,
        recommended_actions=list({a.recommendation for a in anomalies})[:5],
    )


async def analyze_logs_ai(logs: str, service: str) -> LogAnalysisResponse:
    """Analyze logs using Claude AI for deeper insights."""
    # First do pattern analysis
    pattern_result = analyze_logs_pattern(logs, service)

    if not config.is_real_mode:
        return pattern_result

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    prompt = f"""Analyze these application logs from service '{service}'. Identify:
1. Root cause of any errors
2. Pattern anomalies
3. Performance concerns
4. Recommended fixes (specific commands if possible)

Pattern analysis already found: {pattern_result.summary}
Anomalies found: {len(pattern_result.anomalies)}

Logs:
{logs[:5000]}

Respond in this JSON format:
{{"root_cause": "...", "summary": "...", "recommended_actions": ["action1", "action2"]}}"""

    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )

    ai_text = response.content[0].text
    pattern_result.root_cause = f"[AI Analysis] {ai_text[:500]}"
    return pattern_result


def _determine_root_cause(anomalies: list[Anomaly]) -> str:
    if not anomalies:
        return "No anomalies detected - system appears healthy."

    categories = [a.category for a in anomalies if a.severity == Severity.CRITICAL]
    if "Memory" in categories:
        return "Memory exhaustion - likely cause of cascading failures. Check for memory leaks or increase resource limits."
    if "Disk" in categories:
        return "Disk space exhaustion - may cause write failures and service degradation. Free space or expand storage."
    if "Crash" in categories:
        return "Process crash detected - check for unhandled exceptions, memory corruption, or resource limits."
    if "HTTP" in categories:
        return "Server errors (5xx) - backend services may be unhealthy. Check dependent services and resource utilization."
    if "Database" in categories:
        return "Database issues detected - check query performance, connection pools, and lock contention."

    warn_categories = [a.category for a in anomalies if a.severity == Severity.WARNING]
    if warn_categories:
        return f"Multiple warnings detected in: {', '.join(set(warn_categories))}. Monitor closely and address proactively."

    return "Minor issues detected. Continue monitoring."


def _get_recommendation(category: str) -> str:
    recommendations = {
        "Memory": "Check memory usage with 'free -h', identify large processes with 'top -o %MEM', consider increasing limits or fixing leaks",
        "Network": "Check network connectivity with 'ping' and 'curl', verify DNS resolution, check firewall rules",
        "Disk": "Check disk usage with 'df -h', find large files with 'du -sh /*', clean up logs or expand storage",
        "Crash": "Check core dumps, review recent deployments, verify resource limits with 'ulimit -a'",
        "Timeout": "Check service response times, review connection pool settings, consider increasing timeout thresholds",
        "Auth": "Verify credentials, check token expiration, review access policies and RBAC configuration",
        "HTTP": "Check service health endpoints, review recent deployments, check resource utilization",
        "Exception": "Review stack traces, check recent code changes, verify configuration and dependencies",
        "CPU": "Identify CPU-intensive processes with 'top', check for runaway loops, consider scaling horizontally",
        "Database": "Review slow query logs, check index usage with EXPLAIN, monitor connection pool utilization",
    }
    return recommendations.get(category, "Investigate and monitor the situation")
