"""File operations tools - read, write, list files (sandboxed to /tmp/agent-workspace)."""

import os

WORKSPACE = "/tmp/agent-workspace"
os.makedirs(WORKSPACE, exist_ok=True)


def _safe_path(path: str) -> str:
    """Ensure path stays within workspace."""
    full = os.path.normpath(os.path.join(WORKSPACE, path.lstrip("/")))
    if not full.startswith(WORKSPACE):
        raise ValueError(f"Path escape attempt blocked: {path}")
    return full


async def _file_read(path: str) -> str:
    """Read a file from the agent workspace."""
    safe = _safe_path(path)
    if not os.path.exists(safe):
        return f"File not found: {path}"
    with open(safe) as f:
        content = f.read()
    return content[:10000]  # Limit output size


async def _file_write(path: str, content: str) -> str:
    """Write content to a file in the agent workspace."""
    safe = _safe_path(path)
    os.makedirs(os.path.dirname(safe), exist_ok=True)
    with open(safe, "w") as f:
        f.write(content)
    return f"Written {len(content)} bytes to {path}"


async def _file_list(path: str = ".") -> str:
    """List files in a directory of the agent workspace."""
    safe = _safe_path(path)
    if not os.path.isdir(safe):
        return f"Not a directory: {path}"
    entries = []
    for entry in sorted(os.listdir(safe)):
        full = os.path.join(safe, entry)
        kind = "dir" if os.path.isdir(full) else "file"
        size = os.path.getsize(full) if os.path.isfile(full) else 0
        entries.append(f"  [{kind}] {entry} ({size} bytes)")
    return f"Contents of {path}:\n" + "\n".join(entries) if entries else f"Empty directory: {path}"


file_read_tool = {
    "definition": {
        "name": "file_read",
        "description": "Read the contents of a file from the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative file path within workspace"}
            },
            "required": ["path"]
        }
    },
    "handler": _file_read
}

file_write_tool = {
    "definition": {
        "name": "file_write",
        "description": "Write content to a file in the workspace. Creates directories as needed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative file path within workspace"},
                "content": {"type": "string", "description": "Content to write to the file"}
            },
            "required": ["path", "content"]
        }
    },
    "handler": _file_write
}

file_list_tool = {
    "definition": {
        "name": "file_list",
        "description": "List files and directories in the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path to list (default: root)", "default": "."}
            }
        }
    },
    "handler": _file_list
}
