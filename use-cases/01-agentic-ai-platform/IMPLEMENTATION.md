# Implementation Details — Agentic AI Platform

## Project Structure

```
01-agentic-ai-platform/
├── main.py                 # FastAPI app, routes, web UI (HTML embedded)
├── config.py               # Environment config (API key, mode, model, ports)
├── agents/
│   ├── base.py             # BaseAgent: Claude SDK tool-use loop + demo mode
│   ├── orchestrator.py     # Task routing, multi-step coordination, result aggregation
│   ├── research.py         # Web search + summarization agent
│   ├── code_agent.py       # Code generation/review/debug agent
│   ├── analysis.py         # Data analysis + insights agent
│   └── action.py           # API calls + system operations agent
├── tools/
│   ├── __init__.py         # Tool registry, get_tool_definitions(), execute_tool()
│   ├── web_search.py       # DuckDuckGo HTML scraping (no API key needed)
│   ├── file_ops.py         # Sandboxed file read/write/list (/tmp/agent-workspace)
│   ├── shell_exec.py       # Whitelisted command execution with timeout
│   └── api_caller.py       # HTTP requests with internal endpoint blocking
├── memory/
│   └── store.py            # Redis + in-memory fallback context store
├── models/
│   └── schemas.py          # Pydantic: TaskRequest/Response, AgentStep, ToolCall
├── .env.example            # Configuration template
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container image
└── docker-compose.yml      # Docker Compose with Redis
```

## Key Code Walkthrough

### 1. BaseAgent (`agents/base.py`) — The Core

The agentic loop that powers all agents:

```python
# Simplified flow from base.py:run()
messages = [{"role": "user", "content": user_message}]

for round in range(max_tool_rounds):          # Max 5 rounds
    response = client.messages.create(
        model=CLAUDE_MODEL,
        system=self.system_prompt,            # Agent-specific personality
        tools=self.tools,                      # Agent-specific tools
        messages=messages,
    )

    for block in response.content:
        if block.type == "text":
            final_text = block.text            # Capture text response
        elif block.type == "tool_use":
            result = await execute_tool(       # Run the tool
                block.name, block.input
            )
            # Feed result back to Claude
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result[:3000]       # Truncate for safety
            })

    if no_tool_uses:
        break                                  # Claude is done thinking

    messages.append(assistant_content)
    messages.append(tool_results)              # Continue the loop
```

### 2. Orchestrator (`agents/orchestrator.py`) — The Brain

```python
# Routing format Claude returns:
# ROUTE:research|Search for AI trends in UAE
# ROUTE:code|Write a summary report

routes = parse_routes(orchestrator_response)
# → [("research", "Search for AI trends"), ("code", "Write a summary")]

for agent_type, task in routes:
    agent = create_agent(agent_type)           # Factory pattern
    step = await agent.run(task_id, task, context)
    accumulated_context += step.result         # Chain context
```

### 3. Tool Registry (`tools/__init__.py`)

```python
TOOL_REGISTRY = {
    "web_search": {
        "definition": {                        # Claude API format
            "name": "web_search",
            "description": "Search the web...",
            "input_schema": {...}
        },
        "handler": _web_search                 # Async function
    },
    ...
}

async def execute_tool(name, args):
    handler = TOOL_REGISTRY[name]["handler"]
    return await handler(**args)
```

### 4. Demo Mode vs Real Mode

```python
# config.py
AGENT_MODE = "demo"  # or "real"

# base.py - agent switches behavior:
if not config.is_real_mode:
    return self._demo_run(...)   # Keyword-based routing, mock responses
else:
    return self._real_run(...)   # Claude API with tool use loop
```

## API Reference

### POST /api/v1/task
```json
// Request
{"query": "Search for AI trends", "context": {}, "max_steps": 10}

// Response
{
  "task_id": "a1b2c3d4",
  "status": "completed",
  "steps": [
    {"agent": "orchestrator", "result": "ROUTE:research|..."},
    {"agent": "research", "tool_calls": [...], "result": "..."}
  ],
  "final_answer": "Based on research...",
  "duration_ms": 4200
}
```

### GET /api/v1/agents
Returns list of 4 agents with capabilities, tools, and examples.

### GET /api/v1/health
Returns status, mode (demo/real), agent count, uptime.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (empty) | API key for real mode |
| `AGENT_MODE` | `demo` | `demo` or `real` |
| `CLAUDE_MODEL` | `claude-sonnet-4-20250514` | Model to use |
| `PORT` | `8000` | Server port |
| `REDIS_URL` | `redis://localhost:6379` | Redis for memory |
| `LOG_LEVEL` | `INFO` | Logging level |

## Running

```bash
# Demo mode (no API key)
AGENT_MODE=demo python3 main.py

# Real mode
ANTHROPIC_API_KEY=sk-ant-xxx AGENT_MODE=real python3 main.py

# Docker
docker-compose up --build
```

## Test Results

```
28/28 tests passed (all use cases)
Use Case 1 specific:
  ✓ Health check OK, 4 agents registered
  ✓ Research routing: "Search for AI" → research agent
  ✓ Code routing: "Write Python code" → code agent
  ✓ Analysis routing: "Analyze CPU data" → analysis agent
  ✓ Action routing: "Call the API" → action agent
```
