# Use Case 2: Enterprise RAG System

## Retrieval-Augmented Generation for Knowledge Management

Production-grade RAG system that ingests documents, creates semantic embeddings, and answers questions using Claude with cited sources.

## Architecture

```
                    ┌──────────────┐
                    │  Upload API  │
                    │ POST /ingest │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   Parser     │  PDF, MD, TXT, Code
                    │  (pypdf)     │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   Chunker    │  Sentence-aware splitting
                    │  (overlap)   │  with configurable size
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  Embedding   │  sentence-transformers
                    │  (MiniLM)    │  all-MiniLM-L6-v2
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   ChromaDB   │  Vector storage
                    │  (persist)   │  with metadata
                    └──────┬───────┘
                           │
User Question ─────► Semantic Search ──► Top-K Results ──► Claude SDK ──► Answer with Citations
```

## Components

| Component | File | Purpose |
|-----------|------|---------|
| **Document Parser** | `ingestion/parser.py` | PDF, Markdown, text, code file parsing |
| **Chunker** | `ingestion/chunker.py` | Sentence-aware text splitting with overlap |
| **Vector Store** | `embeddings/store.py` | ChromaDB with sentence-transformer embeddings |
| **Answer Generator** | `generation/answer.py` | Claude SDK for generating cited answers |
| **API Server** | `main.py` | FastAPI with web UI |
| **Schemas** | `models/schemas.py` | Pydantic models |

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/ingest` | Upload and ingest a document (multipart form) |
| POST | `/api/v1/query` | Ask a question with `{"question": "...", "top_k": 5}` |
| GET | `/api/v1/stats` | Collection statistics |
| DELETE | `/api/v1/documents/{id}` | Delete a document |
| GET | `/api/v1/health` | Health check |
| GET | `/` | Interactive web UI |

## Quick Start

```bash
pip install -r requirements.txt
RAG_MODE=demo python3 main.py    # Port 8001

# Ingest a document
curl -X POST http://localhost:8001/api/v1/ingest -F "file=@document.pdf"

# Ask a question
curl -X POST http://localhost:8001/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the best vector databases?", "top_k": 5}'
```

## Key Design Decisions

1. **Sentence-aware chunking**: Respects sentence boundaries to avoid splitting context
2. **ChromaDB**: Embedded vector DB, no external service needed
3. **MiniLM embeddings**: Fast, good quality, runs on CPU
4. **Demo + Real mode**: Works without API key, Claude for production answers
5. **Metadata preservation**: Filename, page number, chunk index tracked for citations

## Tested & Running

```
VM: 135.181.93.114:8001
Status: 13 chunks from sample doc, semantic search working
Query latency: ~36ms (demo mode)
```
