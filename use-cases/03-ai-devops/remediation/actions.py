"""Auto-remediation actions - safe, predefined operations for common issues."""

from __future__ import annotations

import asyncio
import logging

from models.schemas import RemediationAction

logger = logging.getLogger(__name__)

# Predefined safe remediation actions
SAFE_ACTIONS = {
    "clear_tmp": RemediationAction(
        action="Clear temporary files",
        command="find /tmp -type f -mtime +7 -delete 2>/dev/null; echo 'Cleaned /tmp files older than 7 days'",
        risk_level="low",
        description="Remove temp files older than 7 days to free disk space",
    ),
    "clear_logs": RemediationAction(
        action="Truncate large log files",
        command="find /var/log -name '*.log' -size +100M -exec truncate -s 0 {} \\; 2>/dev/null; echo 'Truncated large logs'",
        risk_level="medium",
        description="Truncate log files larger than 100MB",
    ),
    "restart_service": RemediationAction(
        action="Restart service",
        command="echo 'Service restart placeholder - specify service name'",
        risk_level="medium",
        description="Restart a specific service to clear stuck state",
    ),
    "clear_cache": RemediationAction(
        action="Clear system cache",
        command="sync; echo 3 > /proc/sys/vm/drop_caches 2>/dev/null; echo 'Cache cleared'",
        risk_level="low",
        description="Clear filesystem cache to free memory",
    ),
    "check_processes": RemediationAction(
        action="Check top processes",
        command="ps aux --sort=-%mem | head -15",
        risk_level="low",
        description="List top processes by memory usage",
    ),
    "check_disk": RemediationAction(
        action="Check disk usage",
        command="df -h && echo '---' && du -sh /var/log/* 2>/dev/null | sort -rh | head -10",
        risk_level="low",
        description="Show disk usage and largest log files",
    ),
    "check_connections": RemediationAction(
        action="Check network connections",
        command="ss -tuln | head -20",
        risk_level="low",
        description="List active network connections and listening ports",
    ),
}


async def execute_action(action_name: str, dry_run: bool = True) -> RemediationAction:
    """Execute a predefined remediation action."""
    if action_name not in SAFE_ACTIONS:
        return RemediationAction(
            action=action_name,
            result=f"Unknown action: {action_name}. Available: {list(SAFE_ACTIONS.keys())}",
        )

    action = SAFE_ACTIONS[action_name].model_copy()

    if dry_run:
        action.result = f"[DRY RUN] Would execute: {action.command}"
        return action

    try:
        proc = await asyncio.create_subprocess_shell(
            action.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        action.executed = True
        action.result = stdout.decode()[:2000]
        if stderr.decode().strip():
            action.result += f"\nStderr: {stderr.decode()[:500]}"
    except asyncio.TimeoutError:
        action.result = "Action timed out after 30s"
    except Exception as e:
        action.result = f"Error: {e}"

    return action


def get_available_actions() -> list[RemediationAction]:
    """List all available remediation actions."""
    return list(SAFE_ACTIONS.values())
