"""Shell execution tool - runs commands in a sandboxed environment."""

import asyncio
import shlex


ALLOWED_COMMANDS = {"ls", "cat", "head", "tail", "wc", "grep", "find", "echo",
                    "date", "whoami", "pwd", "df", "free", "uname", "python3",
                    "pip3", "curl", "wget"}

BLOCKED_PATTERNS = ["rm -rf", "mkfs", "dd if=", "> /dev/", ":(){ :|:", "chmod 777 /"]


async def _shell_exec(command: str, timeout: int = 30) -> str:
    """Execute a shell command with safety restrictions."""
    # Safety checks
    cmd_name = command.split()[0] if command.split() else ""
    base_cmd = cmd_name.split("/")[-1]

    if base_cmd not in ALLOWED_COMMANDS:
        return f"Blocked: '{base_cmd}' not in allowed commands: {sorted(ALLOWED_COMMANDS)}"

    for pattern in BLOCKED_PATTERNS:
        if pattern in command:
            return f"Blocked: dangerous pattern detected"

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="/tmp/agent-workspace"
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

        output = stdout.decode()[:5000]
        errors = stderr.decode()[:1000]

        result = f"Exit code: {proc.returncode}\n"
        if output:
            result += f"Output:\n{output}\n"
        if errors:
            result += f"Stderr:\n{errors}"
        return result.strip()

    except asyncio.TimeoutError:
        return f"Command timed out after {timeout}s"
    except Exception as e:
        return f"Execution error: {e}"


shell_exec_tool = {
    "definition": {
        "name": "shell_exec",
        "description": f"Execute a shell command. Allowed commands: {sorted(ALLOWED_COMMANDS)}. Working directory is /tmp/agent-workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)", "default": 30}
            },
            "required": ["command"]
        }
    },
    "handler": _shell_exec
}
