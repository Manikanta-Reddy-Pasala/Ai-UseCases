from tools.web_search import web_search_tool
from tools.file_ops import file_read_tool, file_write_tool, file_list_tool
from tools.shell_exec import shell_exec_tool
from tools.api_caller import api_call_tool

# Tool registry - maps tool names to their definitions and handlers
TOOL_REGISTRY = {
    "web_search": web_search_tool,
    "file_read": file_read_tool,
    "file_write": file_write_tool,
    "file_list": file_list_tool,
    "shell_exec": shell_exec_tool,
    "api_call": api_call_tool,
}


def get_tool_definitions() -> list[dict]:
    """Get Claude API tool definitions for all registered tools."""
    return [t["definition"] for t in TOOL_REGISTRY.values()]


def get_tools_for_agent(tool_names: list[str]) -> list[dict]:
    """Get tool definitions for specific tools."""
    return [TOOL_REGISTRY[n]["definition"] for n in tool_names if n in TOOL_REGISTRY]


async def execute_tool(tool_name: str, arguments: dict) -> str:
    """Execute a tool by name with given arguments."""
    if tool_name not in TOOL_REGISTRY:
        return f"Error: Unknown tool '{tool_name}'"
    handler = TOOL_REGISTRY[tool_name]["handler"]
    try:
        result = await handler(**arguments)
        return str(result)
    except Exception as e:
        return f"Error executing {tool_name}: {e}"
