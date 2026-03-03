# Architecture — Agentic AI Platform

## System Architecture

```
                                    ┌─────────────────────────────────────────┐
                                    │            FastAPI Server               │
                                    │                                         │
                                    │  POST /api/v1/task ──► TaskRequest      │
                                    │  GET  /api/v1/agents                    │
                                    │  GET  /api/v1/health                    │
                                    │  GET  / ──► Interactive Web UI          │
                                    └──────────────┬──────────────────────────┘
                                                   │
                                    ┌──────────────▼──────────────────────────┐
                                    │           ORCHESTRATOR                   │
                                    │                                         │
                                    │  1. Receive user query                  │
                                    │  2. Classify intent (Claude/keywords)   │
                                    │  3. Generate ROUTE:agent|task lines     │
                                    │  4. Parse routing decisions             │
                                    │  5. Execute agents sequentially         │
                                    │  6. Aggregate results                   │
                                    └──┬───────┬───────┬───────┬─────────────┘
                                       │       │       │       │
                         ┌─────────────▼─┐ ┌───▼─────┐ │  ┌────▼──────────┐
                         │   RESEARCH    │ │  CODE   │ │  │    ACTION     │
                         │   AGENT      │ │  AGENT  │ │  │    AGENT      │
                         │              │ │         │ │  │               │
                         │ System:      │ │ System: │ │  │ System:       │
                         │ "You are a   │ │ "You    │ │  │ "You execute  │
                         │  researcher" │ │  write  │ │  │  operations"  │
                         │              │ │  code"  │ │  │               │
                         │ Tools:       │ │ Tools:  │ │  │ Tools:        │
                         │ • web_search │ │ • file  │ │  │ • api_call    │
                         │ • file_read  │ │ • shell │ │  │ • shell_exec  │
                         │ • file_write │ │ • read  │ │  │ • file_ops    │
                         └──────┬───────┘ └────┬────┘ │  └───────┬───────┘
                                │              │      │          │
                                │         ┌────▼──────▼──┐       │
                                │         │  ANALYSIS    │       │
                                │         │  AGENT       │       │
                                │         │              │       │
                                │         │ Tools:       │       │
                                │         │ • file_ops   │       │
                                │         │ • shell_exec │       │
                                │         └──────┬───────┘       │
                                │                │               │
                         ┌──────▼────────────────▼───────────────▼───────┐
                         │                TOOL LAYER                     │
                         │                                               │
                         │  ┌────────────┐  ┌────────────┐  ┌─────────┐ │
                         │  │ web_search │  │  file_ops  │  │  shell  │ │
                         │  │ DuckDuckGo │  │ Sandboxed  │  │  exec   │ │
                         │  │ HTML parse │  │ /tmp/agent │  │Whitelist│ │
                         │  └────────────┘  └────────────┘  └─────────┘ │
                         │  ┌────────────┐                              │
                         │  │  api_call  │  Blocks internal endpoints   │
                         │  │  HTTP/S    │  Timeout protection          │
                         │  └────────────┘                              │
                         └──────────────────────┬───────────────────────┘
                                                │
                         ┌──────────────────────▼───────────────────────┐
                         │              MEMORY STORE                    │
                         │                                              │
                         │  Redis (if available)  ←→  In-Memory (fallback)
                         │                                              │
                         │  • Per-task context (1hr TTL)                │
                         │  • Conversation history                      │
                         │  • Tool results cache                        │
                         └──────────────────────────────────────────────┘
```

## Agentic Loop (Tool Use Pattern)

Each agent executes Claude's tool use loop — the core of agentic behavior:

```
                    ┌──────────────────────┐
                    │  Agent receives task  │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  Send to Claude API   │
                    │  (system + tools +    │
                    │   user message)       │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  Claude responds      │◄─────────────────────┐
                    │  with content blocks  │                      │
                    └──────────┬───────────┘                      │
                               │                                   │
                    ┌──────────▼───────────┐                      │
                    │  Has tool_use blocks? │                      │
                    └──────┬──────┬────────┘                      │
                      NO   │      │   YES                         │
                           │      │                               │
              ┌────────────▼┐  ┌──▼────────────────┐             │
              │  Return     │  │  Execute each tool │             │
              │  final text │  │  (sandboxed)       │             │
              └─────────────┘  └──────────┬─────────┘             │
                                          │                       │
                               ┌──────────▼───────────┐          │
                               │  Append tool_results │          │
                               │  to messages         │──────────┘
                               └──────────────────────┘
                               (max 5 rounds)
```

## Data Flow

```
TaskRequest                    TaskResponse
  │                              ▲
  │ {query, context,             │ {task_id, status,
  │  max_steps}                  │  steps[], final_answer,
  │                              │  duration_ms}
  ▼                              │
Orchestrator ──► Route ──► Agent(s) ──► Aggregate
  │                  │          │
  │              ROUTE:research │
  │              ROUTE:code     │
  │                             │
  └──── Memory Store ◄──────────┘
        (context shared between steps)
```

## Security Model

```
┌─────────────────────────────────────────────────┐
│                 SECURITY LAYERS                  │
├─────────────────────────────────────────────────┤
│                                                  │
│  FILE OPS:                                       │
│  ├── Sandboxed to /tmp/agent-workspace           │
│  ├── Path traversal protection (normpath+check)  │
│  └── Output size limits (10KB)                   │
│                                                  │
│  SHELL EXEC:                                     │
│  ├── Whitelist: ls, cat, head, grep, python3...  │
│  ├── Blocked: rm -rf, mkfs, dd, chmod 777...     │
│  ├── 30s timeout per command                     │
│  └── Working dir locked to /tmp/agent-workspace  │
│                                                  │
│  API CALLS:                                      │
│  ├── Block localhost, 127.0.0.1, metadata IPs    │
│  ├── Block internal 10.x.x.x ranges             │
│  ├── Methods limited: GET, POST, PUT, PATCH      │
│  └── 15s timeout, 5KB response limit             │
│                                                  │
│  GENERAL:                                        │
│  ├── Tool results truncated (3KB per call)       │
│  ├── Max 5 tool rounds per agent                 │
│  └── Max 10 agent steps per task                 │
└─────────────────────────────────────────────────┘
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| API | FastAPI + Uvicorn | Async REST API |
| AI | Anthropic Claude SDK | Reasoning + tool use |
| Memory | Redis / In-memory | Agent context store |
| Tools | aiohttp, asyncio | Async tool execution |
| Models | Pydantic v2 | Data validation |
| Config | python-dotenv | Environment management |
