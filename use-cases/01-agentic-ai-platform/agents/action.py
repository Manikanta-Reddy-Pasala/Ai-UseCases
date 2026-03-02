"""Action Agent - executes operations like API calls, deployments, and system commands."""

from agents.base import BaseAgent
from models.schemas import AgentType
from tools import get_tools_for_agent


class ActionAgent(BaseAgent):
    agent_type = AgentType.ACTION
    system_prompt = """You are an Action Agent specialized in executing operations.

Your capabilities:
1. Make API calls to external services
2. Execute shell commands safely
3. Read and write files
4. Perform system operations

Guidelines:
- Always validate inputs before executing
- Report results with status codes and details
- Handle errors gracefully
- Never execute destructive operations without explicit confirmation
- Log all actions for audit trail
- Use api_call for HTTP requests
- Use shell_exec for system commands"""

    def __init__(self):
        super().__init__()
        self.tools = get_tools_for_agent(["api_call", "shell_exec", "file_read", "file_write", "file_list"])
