# Agentic AI Platform

## Multi-Agent Orchestration for Enterprise Workflows

An intelligent platform that coordinates specialized AI agents to solve complex tasks autonomously. Instead of a single AI handling everything, tasks are routed to expert agents — each with its own tools and capabilities.

---

### What It Does

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER REQUEST                             │
│           "Research AI trends then write a summary"             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │     ORCHESTRATOR       │
              │                        │
              │  • Understands intent  │
              │  • Plans execution     │
              │  • Routes to agents    │
              └───────────┬────────────┘
                          │
            ┌─────────────┼─────────────┐
            │             │             │
            ▼             ▼             ▼
    ┌──────────────┐ ┌──────────┐ ┌──────────────┐
    │   RESEARCH   │ │   CODE   │ │   ANALYSIS   │
    │    AGENT     │ │  AGENT   │ │    AGENT     │
    │              │ │          │ │              │
    │ • Web search │ │ • Write  │ │ • Patterns   │
    │ • Summarize  │ │ • Review │ │ • Statistics │
    │ • Cite       │ │ • Debug  │ │ • Insights   │
    └──────────────┘ └──────────┘ └──────────────┘
            │             │             │
            └─────────────┼─────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │    AGGREGATED RESULT   │
              │  with full audit trail │
              └────────────────────────┘
```

### Why This Matters

| Problem | Solution |
|---------|----------|
| Single AI can't do everything well | Specialized agents with focused expertise |
| No visibility into AI reasoning | Full step-by-step audit trail |
| Unsafe tool execution | Sandboxed tools with whitelists |
| Hard to extend | Add new agents without changing core |
| Expensive API calls | Route to cheapest capable agent |

### Key Capabilities

- **4 Specialized Agents**: Research, Code, Analysis, Action
- **6 Built-in Tools**: Web search, file ops, shell exec, API calls
- **Smart Routing**: Orchestrator classifies intent and picks the best agent
- **Multi-Step Workflows**: Chain agents for complex tasks
- **Memory**: Shared context across agent steps (Redis or in-memory)
- **Safety**: Sandboxed execution, command whitelists, path traversal protection

### Quick Demo

```bash
# Start the platform
python3 main.py   # Port 8000

# Ask it anything
curl -X POST http://localhost:8000/api/v1/task \
  -H "Content-Type: application/json" \
  -d '{"query": "Write a Python fibonacci function"}'

# → Orchestrator routes to Code Agent → generates code → returns result
```

### Live Instance

- **URL**: http://135.181.93.114:8000
- **Web UI**: Interactive demo with example queries
- **API Docs**: http://135.181.93.114:8000/docs

---

**Detailed Docs**: [ARCHITECTURE.md](ARCHITECTURE.md) | [IMPLEMENTATION.md](IMPLEMENTATION.md)
