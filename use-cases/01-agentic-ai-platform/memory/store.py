"""Memory store for agent context - supports Redis or in-memory fallback."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# In-memory fallback store
_memory: dict[str, list[dict]] = {}
_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis as redis_lib
        from config import config
        _redis_client = redis_lib.from_url(config.REDIS_URL, decode_responses=True)
        _redis_client.ping()
        logger.info("Connected to Redis for memory store")
        return _redis_client
    except Exception:
        logger.info("Redis unavailable, using in-memory store")
        _redis_client = False  # Mark as tried and failed
        return None


def store_context(task_id: str, entry: dict[str, Any]) -> None:
    """Store a context entry for a task."""
    entry["timestamp"] = datetime.utcnow().isoformat()
    r = _get_redis()
    if r:
        r.rpush(f"agent:memory:{task_id}", json.dumps(entry, default=str))
        r.expire(f"agent:memory:{task_id}", 3600)  # 1 hour TTL
    else:
        _memory.setdefault(task_id, []).append(entry)


def get_context(task_id: str, last_n: int = 20) -> list[dict]:
    """Retrieve recent context for a task."""
    r = _get_redis()
    if r:
        items = r.lrange(f"agent:memory:{task_id}", -last_n, -1)
        return [json.loads(i) for i in items]
    return _memory.get(task_id, [])[-last_n:]


def store_conversation(task_id: str, role: str, content: str) -> None:
    """Store a conversation turn."""
    store_context(task_id, {"type": "conversation", "role": role, "content": content})


def get_summary(task_id: str) -> str:
    """Get a text summary of context for a task."""
    entries = get_context(task_id)
    if not entries:
        return "No prior context."
    lines = []
    for e in entries:
        if e.get("type") == "conversation":
            lines.append(f"[{e['role']}]: {e['content'][:200]}")
        elif e.get("type") == "tool_result":
            lines.append(f"[tool:{e.get('tool')}]: {str(e.get('result', ''))[:200]}")
        else:
            lines.append(str(e)[:200])
    return "\n".join(lines[-10:])
