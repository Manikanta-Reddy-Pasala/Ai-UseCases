# Use Case 1: Agentic AI Platform

## Multi-Agent Orchestration using Claude SDK

A production-ready multi-agent orchestration platform that coordinates specialized AI agents to complete complex enterprise workflows autonomously. Built with Anthropic Claude SDK and FastAPI.

## Architecture

```
                              ┌─────────────────────┐
                              │   FastAPI REST API   │
                              │   POST /api/v1/task  │
                              └──────────┬──────────┘
                                         │
                              ┌──────────▼──────────┐
                              │    Orchestrator      │
                              │  (Intent Classifier  │
                              │   + Task Router)     │
                              └──────────┬──────────┘
                                         │
                    ┌────────────┬───────┴────────┬────────────┐
                    ▼            ▼                ▼            ▼
            ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
            │ Research  │  │   Code   │  │ Analysis │  │  Action  │
            │  Agent    │  │  Agent   │  │  Agent   │  │  Agent   │
            └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘
                  │             │             │             │
            ┌─────▼────┐  ┌─────▼────┐  ┌─────▼────┐  ┌─────▼────┐
            │web_search│  │file_write│  │shell_exec│  │ api_call │
            │file_read │  │shell_exec│  │file_write│  │shell_exec│
            │file_write│  │file_read │  │file_read │  │file_write│
            └──────────┘  └──────────┘  └──────────┘  └──────────┘
                                   │
                          ┌────────▼────────┐
                          │  Memory Store   │
                          │ (Redis/In-Mem)  │
                          └─────────────────┘
```

## How It Works

### 1. Task Submission
User submits a natural language request via REST API or web UI.

### 2. Intent Classification & Routing
The **Orchestrator** uses Claude to classify the intent and route to the best agent(s):
- Research queries → **Research Agent** (web search, info gathering)
- Code tasks → **Code Agent** (generation, review, debugging)
- Data tasks → **Analysis Agent** (patterns, statistics, insights)
- Operations → **Action Agent** (API calls, commands, deployments)
- Complex tasks → **Multi-step pipeline** across multiple agents

### 3. Agent Execution (Agentic Loop)
Each agent runs Claude with **tool use** in a loop:
```
Claude decides → Tool call → Execute tool → Feed result back → Claude decides again → ...
```
This continues until Claude has enough information to respond (up to 5 rounds).

### 4. Result Aggregation
Results from all agents are aggregated into a final response with full execution trace.

## Components

| Component | File | Purpose |
|-----------|------|---------|
| **Base Agent** | `agents/base.py` | Claude SDK integration, tool use loop, demo mode |
| **Orchestrator** | `agents/orchestrator.py` | Intent routing, multi-step coordination |
| **Research Agent** | `agents/research.py` | Web search & information synthesis |
| **Code Agent** | `agents/code_agent.py` | Code generation, review, debugging |
| **Analysis Agent** | `agents/analysis.py` | Data analysis & insights |
| **Action Agent** | `agents/action.py` | API calls & system operations |
| **Web Search Tool** | `tools/web_search.py` | DuckDuckGo search (no API key) |
| **File Ops Tool** | `tools/file_ops.py` | Sandboxed file read/write/list |
| **Shell Exec Tool** | `tools/shell_exec.py` | Sandboxed command execution |
| **API Caller Tool** | `tools/api_caller.py` | HTTP requests to external APIs |
| **Memory Store** | `memory/store.py` | Redis/in-memory context storage |
| **Schemas** | `models/schemas.py` | Pydantic models for all data types |
| **Config** | `config.py` | Environment-based configuration |
| **Main App** | `main.py` | FastAPI app with web UI |

## API Reference

### POST /api/v1/task
Submit a task for processing.

**Request:**
```json
{
  "query": "Search for the latest AI trends in UAE 2026",
  "context": {},
  "max_steps": 10
}
```

**Response:**
```json
{
  "task_id": "a1b2c3d4",
  "query": "Search for the latest AI trends in UAE 2026",
  "status": "completed",
  "steps": [
    {
      "agent": "orchestrator",
      "thought": "Routing to research agent",
      "action": "ROUTE:research",
      "result": "ROUTE:research|Search for latest AI trends in UAE 2026"
    },
    {
      "agent": "research",
      "thought": "Processed with 2 tool calls in 3400ms",
      "action": "Used tools: ['web_search', 'web_search']",
      "tool_calls": [...],
      "result": "Based on my research, here are the key AI trends..."
    }
  ],
  "final_answer": "Based on my research, here are the key AI trends...",
  "duration_ms": 4200
}
```

### GET /api/v1/agents
List all registered agents and their capabilities.

### GET /api/v1/health
Health check with uptime and mode info.

### GET /
Interactive web UI for testing the platform.

## Quick Start

### Demo Mode (no API key needed)
```bash
cd use-cases/01-agentic-ai-platform
pip install -r requirements.txt
AGENT_MODE=demo python3 main.py
# Open http://localhost:8000
```

### Real Mode (with Claude API)
```bash
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY and AGENT_MODE=real
python3 main.py
```

### Docker
```bash
docker-compose up --build
# Open http://localhost:8000
```

## Key Design Decisions

1. **Claude SDK for tool use**: Native tool_use API (not LangChain) for maximum control
2. **Agentic loop pattern**: Agent keeps calling tools until it has enough info
3. **Sandboxed tools**: All file/shell operations restricted to `/tmp/agent-workspace`
4. **Demo mode**: Full platform works without API key using mock responses
5. **Memory store**: Redis with in-memory fallback for zero-dependency testing
6. **Safety guardrails**: Allowed command whitelist, blocked patterns, path escape prevention

## Security

- File operations sandboxed to `/tmp/agent-workspace`
- Shell commands restricted to whitelist (no rm, no destructive ops)
- API calls block internal/metadata endpoints
- Tool results truncated to prevent context overflow
- Path traversal protection on all file operations

## Testing on VM

```bash
# SSH to VM
ssh root@135.181.93.114

# Run the platform
cd /opt/ai-usecases/01-agentic-ai-platform
AGENT_MODE=demo python3 main.py &

# Test via curl
curl -X POST http://localhost:8000/api/v1/task \
  -H "Content-Type: application/json" \
  -d '{"query": "Search for AI jobs in UAE"}'

curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/agents
```
