"""Base agent class using Anthropic Claude SDK with tool use support."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import anthropic

from config import config
from models.schemas import AgentStep, AgentType, ToolCall
from memory.store import store_context
from tools import execute_tool

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for all agents. Handles Claude API interaction and tool use loop."""

    agent_type: AgentType = AgentType.ORCHESTRATOR
    system_prompt: str = "You are a helpful AI assistant."
    tools: list[dict] = []
    max_tool_rounds: int = 5

    def __init__(self):
        if config.is_real_mode:
            self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        else:
            self.client = None

    async def run(self, task_id: str, user_message: str, context: str = "") -> AgentStep:
        """Run the agent with a user message, handling tool use in a loop."""
        start = time.time()

        if not config.is_real_mode:
            return await self._demo_run(task_id, user_message, context)

        # Build messages
        messages = []
        if context:
            messages.append({"role": "user", "content": f"Context from previous steps:\n{context}"})
            messages.append({"role": "assistant", "content": "Understood, I have the context."})
        messages.append({"role": "user", "content": user_message})

        all_tool_calls = []
        final_text = ""

        # Agentic loop: keep going while Claude requests tool use
        for round_num in range(self.max_tool_rounds):
            response = self.client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=4096,
                system=self.system_prompt,
                tools=self.tools if self.tools else [],
                messages=messages,
            )

            # Process response blocks
            assistant_content = response.content
            text_parts = []
            tool_uses = []

            for block in assistant_content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_uses.append(block)

            if text_parts:
                final_text = "\n".join(text_parts)

            # If no tool use, we're done
            if not tool_uses:
                break

            # Execute tools and build tool results
            messages.append({"role": "assistant", "content": assistant_content})
            tool_results = []
            for tool_use in tool_uses:
                logger.info(f"[{self.agent_type}] Tool call: {tool_use.name}({json.dumps(tool_use.input)[:200]})")
                result = await execute_tool(tool_use.name, tool_use.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result[:3000],  # Limit tool result size
                })
                all_tool_calls.append(ToolCall(
                    tool_name=tool_use.name,
                    arguments=tool_use.input,
                    result=result[:500]
                ))
                store_context(task_id, {
                    "type": "tool_result",
                    "tool": tool_use.name,
                    "result": result[:500]
                })

            messages.append({"role": "user", "content": tool_results})

        duration = int((time.time() - start) * 1000)
        step = AgentStep(
            agent=self.agent_type,
            thought=f"Processed with {len(all_tool_calls)} tool calls in {duration}ms",
            action=f"Used tools: {[tc.tool_name for tc in all_tool_calls]}" if all_tool_calls else "Direct response",
            tool_calls=all_tool_calls,
            result=final_text,
        )
        store_context(task_id, {"type": "conversation", "role": str(self.agent_type), "content": final_text[:500]})
        return step

    async def _demo_run(self, task_id: str, user_message: str, context: str = "") -> AgentStep:
        """Demo mode - returns mock responses without API calls."""
        demo_responses = {
            AgentType.ORCHESTRATOR: self._demo_orchestrator(user_message),
            AgentType.RESEARCH: self._demo_research(user_message),
            AgentType.CODE: self._demo_code(user_message),
            AgentType.ANALYSIS: self._demo_analysis(user_message),
            AgentType.ACTION: self._demo_action(user_message),
        }

        result = demo_responses.get(self.agent_type, f"[{self.agent_type}] Processed: {user_message[:100]}")

        step = AgentStep(
            agent=self.agent_type,
            thought=f"[DEMO MODE] Processing query for {self.agent_type}",
            action="demo_response",
            result=result,
        )
        store_context(task_id, {"type": "conversation", "role": str(self.agent_type), "content": result[:500]})
        return step

    def _demo_orchestrator(self, msg: str) -> str:
        keywords = msg.lower()
        if any(w in keywords for w in ["search", "find", "look up", "research"]):
            return "ROUTE:research|" + msg
        elif any(w in keywords for w in ["code", "write", "implement", "function", "class", "program"]):
            return "ROUTE:code|" + msg
        elif any(w in keywords for w in ["analyze", "data", "statistics", "compare", "trend"]):
            return "ROUTE:analysis|" + msg
        elif any(w in keywords for w in ["deploy", "run", "execute", "call", "api"]):
            return "ROUTE:action|" + msg
        return "ROUTE:research|" + msg

    def _demo_research(self, msg: str) -> str:
        return (
            f"Research results for: '{msg[:80]}'\n\n"
            "1. Found relevant information about the topic from multiple sources.\n"
            "2. Key findings: The subject has significant developments in 2025-2026.\n"
            "3. Recommended reading: Technical documentation and recent papers.\n"
            "4. Summary: The area is actively evolving with new tools and frameworks."
        )

    def _demo_code(self, msg: str) -> str:
        return (
            f"Code generated for: '{msg[:80]}'\n\n"
            "```python\n"
            "# Generated code example\n"
            "from typing import Any\n\n"
            "class Solution:\n"
            "    def process(self, data: Any) -> dict:\n"
            '        \"\"\"Process the input data and return results.\"\"\"\n'
            "        result = {'status': 'success', 'data': data}\n"
            "        return result\n"
            "```\n\n"
            "The code follows best practices with type hints and documentation."
        )

    def _demo_analysis(self, msg: str) -> str:
        return (
            f"Analysis of: '{msg[:80]}'\n\n"
            "Key Metrics:\n"
            "- Pattern detected: Positive growth trend\n"
            "- Confidence: 85%\n"
            "- Data points analyzed: 1,247\n"
            "- Recommendation: Proceed with the approach based on the data."
        )

    def _demo_action(self, msg: str) -> str:
        return (
            f"Action executed for: '{msg[:80]}'\n\n"
            "Status: Completed\n"
            "- API call successful (200 OK)\n"
            "- Response time: 145ms\n"
            "- Result: Operation completed successfully."
        )
