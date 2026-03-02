"""Orchestrator Agent - routes tasks to specialized agents and aggregates results."""

from __future__ import annotations

import logging
import time
from typing import Any

from agents.base import BaseAgent
from agents.research import ResearchAgent
from agents.code_agent import CodeAgent
from agents.analysis import AnalysisAgent
from agents.action import ActionAgent
from models.schemas import (
    AgentCapability, AgentStep, AgentType, TaskRequest, TaskResponse, TaskStatus
)
from memory.store import get_summary, store_conversation

logger = logging.getLogger(__name__)


# Agent registry
AGENT_REGISTRY: dict[AgentType, AgentCapability] = {
    AgentType.RESEARCH: AgentCapability(
        agent_type=AgentType.RESEARCH,
        name="Research Agent",
        description="Searches the web, gathers information, reads documents, and provides structured research summaries.",
        tools=["web_search", "file_read", "file_write"],
        examples=["search for X", "find information about Y", "research Z topic"],
    ),
    AgentType.CODE: AgentCapability(
        agent_type=AgentType.CODE,
        name="Code Agent",
        description="Generates code, reviews code quality, debugs issues, writes tests and documentation.",
        tools=["file_read", "file_write", "shell_exec"],
        examples=["write a Python function", "review this code", "generate a REST API"],
    ),
    AgentType.ANALYSIS: AgentCapability(
        agent_type=AgentType.ANALYSIS,
        name="Analysis Agent",
        description="Analyzes data, detects patterns, generates statistics, and provides insights with recommendations.",
        tools=["file_read", "file_write", "shell_exec"],
        examples=["analyze this data", "find trends in X", "compare A vs B"],
    ),
    AgentType.ACTION: AgentCapability(
        agent_type=AgentType.ACTION,
        name="Action Agent",
        description="Executes API calls, runs commands, performs deployments, and handles system operations.",
        tools=["api_call", "shell_exec", "file_read", "file_write"],
        examples=["call this API", "deploy the service", "execute command"],
    ),
}


def _create_agent(agent_type: AgentType) -> BaseAgent:
    """Factory to create agent instances."""
    agents = {
        AgentType.RESEARCH: ResearchAgent,
        AgentType.CODE: CodeAgent,
        AgentType.ANALYSIS: AnalysisAgent,
        AgentType.ACTION: ActionAgent,
    }
    cls = agents.get(agent_type)
    if not cls:
        raise ValueError(f"Unknown agent type: {agent_type}")
    return cls()


class Orchestrator:
    """Routes tasks to the appropriate specialized agent and manages the workflow."""

    def __init__(self):
        self.router = BaseAgent()
        self.router.agent_type = AgentType.ORCHESTRATOR
        self.router.system_prompt = self._build_router_prompt()

    def _build_router_prompt(self) -> str:
        agent_descriptions = "\n".join(
            f"- **{cap.agent_type.value}**: {cap.description} (examples: {', '.join(cap.examples[:2])})"
            for cap in AGENT_REGISTRY.values()
        )
        return f"""You are an Orchestrator Agent. Your job is to:
1. Understand the user's request
2. Decide which specialized agent(s) should handle it
3. Break complex tasks into steps if needed

Available agents:
{agent_descriptions}

Respond with EXACTLY this format:
ROUTE:<agent_type>|<task description for that agent>

For multi-step tasks, respond with multiple lines:
ROUTE:<agent1>|<step 1 description>
ROUTE:<agent2>|<step 2 description>

Agent types: research, code, analysis, action

Examples:
- "Search for Python best practices" → ROUTE:research|Search for Python best practices and summarize key findings
- "Write a REST API" → ROUTE:code|Write a REST API with CRUD endpoints using FastAPI
- "Analyze server logs" → ROUTE:analysis|Analyze the server logs and identify patterns and anomalies
- "Research AI trends then write a report" → ROUTE:research|Research current AI trends in 2026
ROUTE:code|Write a structured report based on the research findings"""

    async def process(self, request: TaskRequest) -> TaskResponse:
        """Process a task request through the orchestrator pipeline."""
        start = time.time()
        task_response = TaskResponse(query=request.query, status=TaskStatus.IN_PROGRESS)
        task_id = task_response.task_id

        store_conversation(task_id, "user", request.query)
        logger.info(f"[{task_id}] Processing: {request.query[:100]}")

        try:
            # Step 1: Route the task
            route_step = await self.router.run(task_id, request.query)
            task_response.steps.append(route_step)

            # Parse routing decision
            routes = self._parse_routes(route_step.result)
            if not routes:
                # If routing failed, default to research
                routes = [(AgentType.RESEARCH, request.query)]

            logger.info(f"[{task_id}] Routing to: {[(r[0].value, r[1][:50]) for r in routes]}")

            # Step 2: Execute each routed task
            accumulated_context = ""
            for agent_type, task_description in routes[:request.max_steps]:
                agent = _create_agent(agent_type)
                context = get_summary(task_id) + "\n" + accumulated_context

                step = await agent.run(task_id, task_description, context=context)
                task_response.steps.append(step)
                accumulated_context += f"\n[{agent_type.value}]: {step.result[:500]}"

            # Step 3: Build final answer
            task_response.final_answer = self._build_final_answer(task_response.steps)
            task_response.status = TaskStatus.COMPLETED

        except Exception as e:
            logger.error(f"[{task_id}] Error: {e}", exc_info=True)
            task_response.status = TaskStatus.FAILED
            task_response.final_answer = f"Error processing request: {e}"
            task_response.steps.append(AgentStep(
                agent=AgentType.ORCHESTRATOR,
                thought="Error occurred",
                result=str(e)
            ))

        task_response.duration_ms = int((time.time() - start) * 1000)
        return task_response

    def _parse_routes(self, route_text: str) -> list[tuple[AgentType, str]]:
        """Parse ROUTE:agent|task lines from orchestrator output."""
        routes = []
        agent_map = {
            "research": AgentType.RESEARCH,
            "code": AgentType.CODE,
            "analysis": AgentType.ANALYSIS,
            "action": AgentType.ACTION,
        }

        for line in route_text.strip().split("\n"):
            line = line.strip()
            if line.startswith("ROUTE:"):
                parts = line[6:].split("|", 1)
                if len(parts) == 2:
                    agent_key = parts[0].strip().lower()
                    task = parts[1].strip()
                    if agent_key in agent_map:
                        routes.append((agent_map[agent_key], task))

        return routes

    def _build_final_answer(self, steps: list[AgentStep]) -> str:
        """Aggregate results from all steps into a final answer."""
        # Skip the routing step, collect agent results
        results = []
        for step in steps:
            if step.agent != AgentType.ORCHESTRATOR and step.result:
                results.append(f"**{step.agent.value.title()} Agent:**\n{step.result}")

        if not results:
            return "No results were generated."

        return "\n\n---\n\n".join(results)

    @staticmethod
    def get_registered_agents() -> list[AgentCapability]:
        """Get list of all registered agent capabilities."""
        return list(AGENT_REGISTRY.values())
