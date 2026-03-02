from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    ORCHESTRATOR = "orchestrator"
    RESEARCH = "research"
    CODE = "code"
    ANALYSIS = "analysis"
    ACTION = "action"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ToolCall(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = {}
    result: Any = None


class AgentStep(BaseModel):
    agent: AgentType
    thought: str = ""
    action: str = ""
    tool_calls: list[ToolCall] = []
    result: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TaskRequest(BaseModel):
    query: str
    context: dict[str, Any] = {}
    max_steps: int = 10


class TaskResponse(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    query: str
    status: TaskStatus = TaskStatus.PENDING
    steps: list[AgentStep] = []
    final_answer: str = ""
    total_tokens: int = 0
    duration_ms: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentCapability(BaseModel):
    agent_type: AgentType
    name: str
    description: str
    tools: list[str] = []
    examples: list[str] = []


class HealthResponse(BaseModel):
    status: str = "ok"
    mode: str = "demo"
    agents_registered: int = 0
    uptime_seconds: float = 0
