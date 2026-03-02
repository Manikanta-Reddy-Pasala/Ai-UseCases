"""Agentic AI Platform - Multi-Agent Orchestration API.

This platform coordinates specialized AI agents (Research, Code, Analysis, Action)
through a central Orchestrator that routes tasks based on intent classification.

Built with:
- Anthropic Claude SDK for AI reasoning and tool use
- FastAPI for the REST API
- Pydantic for data validation
- Redis for agent memory (optional, falls back to in-memory)

Usage:
    # Demo mode (no API key needed):
    AGENT_MODE=demo python3 main.py

    # Real mode (requires Anthropic API key):
    ANTHROPIC_API_KEY=sk-ant-xxx AGENT_MODE=real python3 main.py

API Endpoints:
    POST /api/v1/task        - Submit a task for processing
    GET  /api/v1/agents      - List available agents
    GET  /api/v1/health      - Health check
    GET  /                   - Interactive demo page
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from config import config
from agents.orchestrator import Orchestrator
from models.schemas import (
    AgentCapability, HealthResponse, TaskRequest, TaskResponse
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Global state
start_time = time.time()
orchestrator: Orchestrator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator
    orchestrator = Orchestrator()
    mode = "REAL (Claude API)" if config.is_real_mode else "DEMO (mock responses)"
    logger.info(f"Agentic AI Platform started in {mode} mode")
    logger.info(f"Registered agents: {[a.name for a in orchestrator.get_registered_agents()]}")
    yield
    logger.info("Agentic AI Platform shutting down")


app = FastAPI(
    title="Agentic AI Platform",
    description="Multi-agent orchestration platform using Claude SDK",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/api/v1/task", response_model=TaskResponse)
async def submit_task(request: TaskRequest):
    """Submit a task for the multi-agent orchestrator to process."""
    return await orchestrator.process(request)


@app.get("/api/v1/agents", response_model=list[AgentCapability])
async def list_agents():
    """List all registered agents and their capabilities."""
    return orchestrator.get_registered_agents()


@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        mode=config.AGENT_MODE,
        agents_registered=len(orchestrator.get_registered_agents()),
        uptime_seconds=round(time.time() - start_time, 1),
    )


@app.get("/", response_class=HTMLResponse)
async def demo_page():
    """Interactive demo page for testing the platform."""
    mode = "REAL" if config.is_real_mode else "DEMO"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agentic AI Platform</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               background: #0f172a; color: #e2e8f0; min-height: 100vh; }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 2rem; }}
        h1 {{ font-size: 2rem; margin-bottom: 0.5rem; color: #38bdf8; }}
        .subtitle {{ color: #94a3b8; margin-bottom: 2rem; }}
        .mode-badge {{ display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 0.75rem;
                       background: {('#22c55e' if mode == 'REAL' else '#eab308')}; color: #000; font-weight: 600; }}
        .input-group {{ display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }}
        input {{ flex: 1; padding: 0.75rem 1rem; border: 1px solid #334155; border-radius: 8px;
                background: #1e293b; color: #e2e8f0; font-size: 1rem; outline: none; }}
        input:focus {{ border-color: #38bdf8; }}
        button {{ padding: 0.75rem 1.5rem; border: none; border-radius: 8px; background: #2563eb;
                 color: white; font-size: 1rem; cursor: pointer; font-weight: 600; }}
        button:hover {{ background: #1d4ed8; }}
        button:disabled {{ background: #475569; cursor: wait; }}
        .examples {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1.5rem; }}
        .example {{ padding: 4px 12px; border: 1px solid #334155; border-radius: 16px; font-size: 0.8rem;
                   cursor: pointer; color: #94a3b8; transition: all 0.2s; }}
        .example:hover {{ border-color: #38bdf8; color: #38bdf8; }}
        #result {{ background: #1e293b; border: 1px solid #334155; border-radius: 8px;
                  padding: 1.5rem; min-height: 200px; white-space: pre-wrap; font-family: monospace;
                  font-size: 0.9rem; line-height: 1.6; }}
        .step {{ margin: 0.5rem 0; padding: 0.5rem; border-left: 3px solid #38bdf8; padding-left: 1rem; }}
        .step-agent {{ color: #38bdf8; font-weight: 600; }}
        .agents-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-top: 1.5rem; }}
        .agent-card {{ background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 1rem; }}
        .agent-card h3 {{ color: #38bdf8; font-size: 0.9rem; margin-bottom: 0.25rem; }}
        .agent-card p {{ color: #94a3b8; font-size: 0.8rem; }}
        .spinner {{ display: none; }}
        .spinner.active {{ display: inline-block; animation: spin 1s linear infinite; }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Agentic AI Platform <span class="mode-badge">{mode}</span></h1>
        <p class="subtitle">Multi-agent orchestration powered by Claude SDK</p>

        <div class="input-group">
            <input type="text" id="query" placeholder="Ask anything... The orchestrator will route to the best agent"
                   onkeypress="if(event.key==='Enter') submitTask()">
            <button onclick="submitTask()" id="submitBtn">
                <span class="spinner" id="spinner">&#9696;</span> Run
            </button>
        </div>

        <div class="examples">
            <span class="example" onclick="setQuery('Search for the latest AI trends in UAE 2026')">Research</span>
            <span class="example" onclick="setQuery('Write a Python FastAPI endpoint for user authentication')">Code</span>
            <span class="example" onclick="setQuery('Analyze the performance metrics: CPU 78%, Memory 92%, Disk 45%')">Analysis</span>
            <span class="example" onclick="setQuery('Call the JSONPlaceholder API and get the first 3 posts')">Action</span>
            <span class="example" onclick="setQuery('Research Kubernetes best practices then write a deployment checklist')">Multi-Step</span>
        </div>

        <div id="result">Ready. Submit a task to see the multi-agent orchestration in action.

Available agents: Research, Code, Analysis, Action
Mode: {mode} {'(set ANTHROPIC_API_KEY and AGENT_MODE=real for live AI)' if mode == 'DEMO' else ''}</div>

        <div class="agents-grid">
            <div class="agent-card">
                <h3>Research Agent</h3>
                <p>Web search, information gathering, document analysis, summarization</p>
            </div>
            <div class="agent-card">
                <h3>Code Agent</h3>
                <p>Code generation, review, debugging, testing, documentation</p>
            </div>
            <div class="agent-card">
                <h3>Analysis Agent</h3>
                <p>Data analysis, pattern detection, statistics, recommendations</p>
            </div>
            <div class="agent-card">
                <h3>Action Agent</h3>
                <p>API calls, shell commands, deployments, system operations</p>
            </div>
        </div>
    </div>

    <script>
        function setQuery(q) {{ document.getElementById('query').value = q; }}

        async function submitTask() {{
            const query = document.getElementById('query').value.trim();
            if (!query) return;

            const btn = document.getElementById('submitBtn');
            const spinner = document.getElementById('spinner');
            const result = document.getElementById('result');

            btn.disabled = true;
            spinner.classList.add('active');
            result.textContent = 'Processing... Orchestrator is routing your task to the best agent(s)...\\n';

            try {{
                const resp = await fetch('/api/v1/task', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ query: query, max_steps: 5 }})
                }});
                const data = await resp.json();

                let output = `Task ID: ${{data.task_id}} | Status: ${{data.status}} | Duration: ${{data.duration_ms}}ms\\n`;
                output += '='.repeat(70) + '\\n\\n';

                for (const step of data.steps) {{
                    output += `[${{step.agent.toUpperCase()}}] ${{step.thought}}\\n`;
                    if (step.tool_calls && step.tool_calls.length > 0) {{
                        for (const tc of step.tool_calls) {{
                            output += `  Tool: ${{tc.tool_name}}(${{JSON.stringify(tc.arguments).substring(0, 100)}})\\n`;
                            output += `  Result: ${{(tc.result || '').substring(0, 200)}}\\n`;
                        }}
                    }}
                    output += `  Output: ${{step.result}}\\n\\n`;
                }}

                output += '='.repeat(70) + '\\n';
                output += 'FINAL ANSWER:\\n' + (data.final_answer || 'No answer generated');
                result.textContent = output;
            }} catch (e) {{
                result.textContent = 'Error: ' + e.message;
            }} finally {{
                btn.disabled = false;
                spinner.classList.remove('active');
            }}
        }}
    </script>
</body>
</html>"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=False)
