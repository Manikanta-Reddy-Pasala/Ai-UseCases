# Enterprise RAG System

## AI-Powered Knowledge Base with Semantic Search

Upload company documents, ask questions in natural language, get accurate answers with cited sources. RAG (Retrieval-Augmented Generation) eliminates hallucinations by grounding AI responses in your actual data.

---

### How It Works

```
┌──────────────────────────────────────────────────────────────┐
│                     INGEST PHASE                              │
│                                                               │
│   PDF/MD/TXT ──► Parser ──► Chunker ──► Embedder ──► Store   │
│                    │          │            │            │      │
│               Extract      Split to    Convert to   ChromaDB  │
│               text       ~500 char    384-dim       vector    │
│                          chunks       vectors       storage   │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                     QUERY PHASE                               │
│                                                               │
│   "What are the best    ┌──────────┐   ┌──────────┐          │
│    vector databases?" ──► Semantic  ├──►│  Top-K   │          │
│                         │  Search   │   │ Results  │          │
│                         └──────────┘   └─────┬────┘          │
│                                              │               │
│                                        ┌─────▼─────┐        │
│                                        │  Claude    │        │
│                                        │  + Context │        │
│                                        └─────┬─────┘        │
│                                              │               │
│   "ChromaDB for prototyping,          ┌──────▼──────┐       │
│    Pinecone for production,     ◄─────│   Answer    │       │
│    Weaviate for hybrid search"        │ + Citations │       │
│    [Source 1] [Source 3]              └─────────────┘       │
└──────────────────────────────────────────────────────────────┘
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Multi-format ingestion** | PDF, Markdown, TXT, code files (Python, Java, JS, YAML) |
| **Smart chunking** | Sentence-aware splitting with configurable overlap |
| **Semantic search** | Find relevant passages by meaning, not just keywords |
| **Cited answers** | Every claim linked to source document and page |
| **Demo + Real mode** | Works without API key; Claude for production |

### Quick Demo

```bash
python3 main.py   # Port 8001

# Upload a document
curl -X POST http://localhost:8001/api/v1/ingest -F "file=@document.pdf"
# → {"chunks_created": 13}

# Ask a question
curl -X POST http://localhost:8001/api/v1/query \
  -d '{"question": "What are the best vector databases?", "top_k": 3}'
# → Answer with 3 cited sources, 24ms
```

### Live: http://135.181.93.114:8001

---

**Detailed Docs**: [ARCHITECTURE.md](ARCHITECTURE.md) | [IMPLEMENTATION.md](IMPLEMENTATION.md)
