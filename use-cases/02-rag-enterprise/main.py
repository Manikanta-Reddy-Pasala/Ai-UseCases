"""Enterprise RAG System - Retrieval-Augmented Generation API.

Ingest documents, create embeddings, and query with AI-powered answers.

Built with:
- ChromaDB for vector storage
- Sentence-Transformers for embeddings
- Anthropic Claude SDK for answer generation
- FastAPI for the REST API

Usage:
    RAG_MODE=demo python3 main.py                    # Demo mode (port 8001)
    ANTHROPIC_API_KEY=sk-xxx RAG_MODE=real python3 main.py  # Real mode

API:
    POST /api/v1/ingest     - Upload and ingest a document
    POST /api/v1/query      - Ask a question
    GET  /api/v1/documents  - List ingested documents
    DELETE /api/v1/documents/{id} - Delete a document
    GET  /api/v1/stats      - Collection statistics
    GET  /api/v1/health     - Health check
    GET  /                  - Interactive demo page
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse

from config import config
from models.schemas import (
    CollectionStats, HealthResponse, IngestResponse,
    QueryRequest, QueryResponse,
)
from ingestion.parser import parse_document
from ingestion.chunker import chunk_text
from models.schemas import DocumentMetadata
from embeddings.store import add_chunks, search, get_stats, delete_document
from generation.answer import generate_answer

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, "INFO"),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    mode = "REAL (Claude API)" if config.is_real_mode else "DEMO (mock answers)"
    logger.info(f"Enterprise RAG System started in {mode} mode on port {config.PORT}")
    logger.info(f"Embedding model: {config.EMBEDDING_MODEL}")
    yield
    logger.info("Enterprise RAG System shutting down")


app = FastAPI(
    title="Enterprise RAG System",
    description="Retrieval-Augmented Generation for enterprise knowledge management",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/api/v1/ingest", response_model=IngestResponse)
async def ingest_document(file: UploadFile = File(...)):
    """Upload and ingest a document into the knowledge base."""
    content = await file.read()
    filename = file.filename or "unknown"
    document_id = str(uuid.uuid4())[:12]

    logger.info(f"Ingesting: {filename} ({len(content)} bytes)")

    # Parse document
    pages = parse_document(content, filename)

    # Chunk and embed
    all_chunks = []
    for page_data in pages:
        metadata = DocumentMetadata(
            filename=filename,
            file_type=filename.rsplit(".", 1)[-1] if "." in filename else "txt",
            page_number=page_data.get("page", 1),
            total_pages=page_data.get("total_pages", 1),
        )
        chunks = chunk_text(page_data["text"], document_id, metadata)
        all_chunks.extend(chunks)

    # Store in vector DB
    stored = add_chunks(all_chunks)
    logger.info(f"Ingested {filename}: {stored} chunks created")

    return IngestResponse(
        document_id=document_id,
        filename=filename,
        chunks_created=stored,
    )


@app.post("/api/v1/query", response_model=QueryResponse)
async def query_knowledge_base(request: QueryRequest):
    """Ask a question and get an AI-powered answer from the knowledge base."""
    start = time.time()

    # Build filter
    filter_dict = None
    if request.filter_filename:
        filter_dict = {"filename": request.filter_filename}

    # Search for relevant chunks
    sources = search(request.question, top_k=request.top_k, filter_dict=filter_dict)

    # Generate answer
    answer = generate_answer(request.question, sources)

    return QueryResponse(
        question=request.question,
        answer=answer,
        sources=sources,
        mode=config.RAG_MODE,
        duration_ms=int((time.time() - start) * 1000),
    )


@app.get("/api/v1/stats", response_model=CollectionStats)
async def get_collection_stats():
    """Get statistics about the knowledge base."""
    stats = get_stats()
    return CollectionStats(**stats)


@app.delete("/api/v1/documents/{document_id}")
async def remove_document(document_id: str):
    """Delete all chunks for a document."""
    deleted = delete_document(document_id)
    return {"document_id": document_id, "chunks_deleted": deleted}


@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    stats = get_stats()
    return HealthResponse(
        status="ok",
        mode=config.RAG_MODE,
        embedding_model=config.EMBEDDING_MODEL,
        total_chunks=stats["total_chunks"],
    )


@app.get("/", response_class=HTMLResponse)
async def demo_page():
    mode = "REAL" if config.is_real_mode else "DEMO"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enterprise RAG System</title>
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
               background:#0f172a; color:#e2e8f0; min-height:100vh; }}
        .container {{ max-width:900px; margin:0 auto; padding:2rem; }}
        h1 {{ font-size:2rem; margin-bottom:0.5rem; color:#a78bfa; }}
        .subtitle {{ color:#94a3b8; margin-bottom:2rem; }}
        .badge {{ display:inline-block; padding:2px 10px; border-radius:12px; font-size:0.75rem;
                  background:{('#22c55e' if mode=='REAL' else '#eab308')}; color:#000; font-weight:600; }}
        .section {{ background:#1e293b; border:1px solid #334155; border-radius:8px; padding:1.5rem; margin-bottom:1.5rem; }}
        h2 {{ color:#a78bfa; margin-bottom:1rem; font-size:1.1rem; }}
        .upload {{ border:2px dashed #334155; border-radius:8px; padding:2rem; text-align:center; margin-bottom:1rem; }}
        input[type="file"] {{ margin:0.5rem 0; }}
        input[type="text"] {{ width:100%; padding:0.75rem; border:1px solid #334155; border-radius:8px;
                             background:#1e293b; color:#e2e8f0; font-size:1rem; outline:none; margin-bottom:0.5rem; }}
        input[type="text"]:focus {{ border-color:#a78bfa; }}
        button {{ padding:0.75rem 1.5rem; border:none; border-radius:8px; background:#7c3aed;
                 color:white; font-size:1rem; cursor:pointer; font-weight:600; }}
        button:hover {{ background:#6d28d9; }}
        button:disabled {{ background:#475569; cursor:wait; }}
        #result {{ background:#0f172a; border:1px solid #334155; border-radius:8px;
                  padding:1rem; min-height:150px; white-space:pre-wrap; font-family:monospace;
                  font-size:0.85rem; line-height:1.6; margin-top:1rem; }}
        .stats {{ display:grid; grid-template-columns:repeat(3,1fr); gap:1rem; }}
        .stat {{ text-align:center; padding:1rem; background:#0f172a; border-radius:8px; }}
        .stat-value {{ font-size:1.5rem; color:#a78bfa; font-weight:700; }}
        .stat-label {{ font-size:0.8rem; color:#94a3b8; }}
    </style>
</head>
<body>
<div class="container">
    <h1>Enterprise RAG System <span class="badge">{mode}</span></h1>
    <p class="subtitle">Ingest documents, search knowledge base, get AI-powered answers</p>

    <div class="stats" id="stats">
        <div class="stat"><div class="stat-value" id="totalChunks">-</div><div class="stat-label">Chunks</div></div>
        <div class="stat"><div class="stat-value" id="embModel">-</div><div class="stat-label">Embedding Model</div></div>
        <div class="stat"><div class="stat-value" id="sysMode">{mode}</div><div class="stat-label">Mode</div></div>
    </div>

    <div class="section">
        <h2>1. Ingest Documents</h2>
        <div class="upload">
            <p>Upload PDF, TXT, MD, or code files</p>
            <input type="file" id="fileInput" accept=".pdf,.txt,.md,.py,.java,.js,.json,.yaml,.yml,.xml,.html,.csv">
            <br><button onclick="ingestFile()">Upload & Ingest</button>
        </div>
        <div id="ingestResult" style="font-size:0.85rem; color:#94a3b8;"></div>
    </div>

    <div class="section">
        <h2>2. Ask Questions</h2>
        <input type="text" id="question" placeholder="Ask a question about your documents..."
               onkeypress="if(event.key==='Enter') askQuestion()">
        <button onclick="askQuestion()" id="askBtn">Ask</button>
        <div id="result">Upload some documents, then ask questions about them.</div>
    </div>
</div>

<script>
async function loadStats() {{
    try {{
        const r = await fetch('/api/v1/health');
        const d = await r.json();
        document.getElementById('totalChunks').textContent = d.total_chunks;
        document.getElementById('embModel').textContent = d.embedding_model.split('/').pop();
    }} catch(e) {{ console.error(e); }}
}}

async function ingestFile() {{
    const input = document.getElementById('fileInput');
    if (!input.files.length) return;
    const fd = new FormData();
    fd.append('file', input.files[0]);
    const res = document.getElementById('ingestResult');
    res.textContent = 'Ingesting...';
    try {{
        const r = await fetch('/api/v1/ingest', {{ method:'POST', body:fd }});
        const d = await r.json();
        res.textContent = `Ingested "${{d.filename}}": ${{d.chunks_created}} chunks created (ID: ${{d.document_id}})`;
        loadStats();
    }} catch(e) {{ res.textContent = 'Error: '+e.message; }}
}}

async function askQuestion() {{
    const q = document.getElementById('question').value.trim();
    if (!q) return;
    const btn = document.getElementById('askBtn');
    const result = document.getElementById('result');
    btn.disabled = true;
    result.textContent = 'Searching knowledge base...';
    try {{
        const r = await fetch('/api/v1/query', {{
            method:'POST', headers:{{'Content-Type':'application/json'}},
            body: JSON.stringify({{question:q, top_k:5}})
        }});
        const d = await r.json();
        let out = `Question: ${{d.question}}\\nMode: ${{d.mode}} | Duration: ${{d.duration_ms}}ms | Sources: ${{d.sources.length}}\\n${'='.repeat(60)}\\n\\n`;
        out += d.answer + '\\n\\n';
        if (d.sources.length) {{
            out += '${'='.repeat(60)}\\nSOURCES:\\n';
            d.sources.forEach((s,i) => {{
                out += `\\n[${{i+1}}] ${{s.metadata.filename || 'unknown'}} (score: ${{s.score}})\\n${{s.content.substring(0,200)}}...\\n`;
            }});
        }}
        result.textContent = out;
    }} catch(e) {{ result.textContent = 'Error: '+e.message; }}
    btn.disabled = false;
}}

loadStats();
</script>
</body>
</html>"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=False)
