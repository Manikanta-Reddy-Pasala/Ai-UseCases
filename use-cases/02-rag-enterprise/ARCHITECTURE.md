# Architecture — Enterprise RAG System

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI Server (:8001)                       │
│                                                                     │
│  POST /api/v1/ingest ──────► Ingestion Pipeline                    │
│  POST /api/v1/query  ──────► Query Pipeline                        │
│  GET  /api/v1/stats  ──────► Collection Statistics                 │
│  DELETE /api/v1/documents/{id}                                      │
│  GET  / ─────────────────► Interactive Web UI                      │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
            ┌────────────────────┴────────────────────┐
            │                                         │
┌───────────▼──────────┐                 ┌────────────▼────────────┐
│  INGESTION PIPELINE  │                 │    QUERY PIPELINE       │
│                      │                 │                         │
│  ┌────────────────┐  │                 │  ┌──────────────────┐  │
│  │  Parser        │  │                 │  │ Query Embedding  │  │
│  │  • PDF (pypdf) │  │                 │  │ (MiniLM-L6-v2)  │  │
│  │  • Markdown    │  │                 │  └────────┬─────────┘  │
│  │  • Text/Code   │  │                 │           │            │
│  └───────┬────────┘  │                 │  ┌────────▼─────────┐  │
│          │           │                 │  │ Semantic Search  │  │
│  ┌───────▼────────┐  │                 │  │ ChromaDB cosine  │  │
│  │  Chunker       │  │                 │  │ similarity       │  │
│  │  • 500 chars   │  │                 │  └────────┬─────────┘  │
│  │  • 50 overlap  │  │                 │           │            │
│  │  • Sentence-   │  │                 │  ┌────────▼─────────┐  │
│  │    aware split │  │                 │  │  Top-K Results   │  │
│  └───────┬────────┘  │                 │  │  (ranked by      │  │
│          │           │                 │  │   relevance)     │  │
│  ┌───────▼────────┐  │                 │  └────────┬─────────┘  │
│  │  Embedding     │  │                 │           │            │
│  │  MiniLM-L6-v2  │  │                 │  ┌────────▼─────────┐  │
│  │  384 dimensions│  │                 │  │ Answer Generator │  │
│  └───────┬────────┘  │                 │  │ Claude SDK       │  │
│          │           │                 │  │ (or demo mode)   │  │
│          ▼           │                 │  └──────────────────┘  │
│  ┌────────────────┐  │                 │                        │
│  │  ChromaDB      │◄─┼─────────────────┘                        │
│  │  Vector Store  │  │                                          │
│  │  (persistent)  │  │                                          │
│  └────────────────┘  │                                          │
└──────────────────────┘                                          │
                                                                   │
                         ┌─────────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │   QueryResponse      │
              │   • answer (text)    │
              │   • sources[] with   │
              │     - content        │
              │     - score          │
              │     - filename       │
              │     - page_number    │
              │   • duration_ms      │
              └──────────────────────┘
```

## Chunking Strategy

```
Original Document (2000 chars):
┌─────────────────────────────────────────────────────┐
│ Sentence 1. Sentence 2. Sentence 3. Sentence 4.     │
│ Sentence 5. Sentence 6. Sentence 7. Sentence 8.     │
│ Sentence 9. Sentence 10. Sentence 11. Sentence 12.  │
└─────────────────────────────────────────────────────┘

After chunking (500 chars, 50 word overlap):
┌──────────────────┐
│ Chunk 1          │  Sentences 1-4 (~500 chars)
│ S1. S2. S3. S4.  │
└────────┬─────────┘
         │ overlap (last 50 words of Chunk 1)
┌────────▼─────────┐
│ Chunk 2          │  ...S4. S5. S6. S7.
│ S4. S5. S6. S7.  │
└────────┬─────────┘
         │ overlap
┌────────▼─────────┐
│ Chunk 3          │  ...S7. S8. S9. S10.
│ S7. S8. S9. S10. │
└──────────────────┘

Benefits:
  • No sentence splitting (respects boundaries)
  • Overlap preserves context at chunk edges
  • Consistent chunk sizes for embedding quality
```

## Embedding + Search Flow

```
Query: "vector databases for RAG"
         │
         ▼
┌─────────────────┐     ┌───────────────────────────────┐
│ Embed query     │     │     ChromaDB Collection        │
│ MiniLM-L6-v2   │     │                               │
│ → [0.12, -0.34,│     │  Chunk 1: [0.08, -0.22, ...]  │
│    0.56, ...]   │────►│  Chunk 2: [0.45, 0.11, ...]   │
│ (384 dims)      │     │  Chunk 3: [0.13, -0.31, ...]  │ ◄── closest!
└─────────────────┘     │  Chunk 4: [0.67, 0.43, ...]   │
                        │  ...                           │
                        └───────────────────────────────┘
                                     │
                        Cosine similarity ranking:
                        Chunk 3: 0.89 ← best match
                        Chunk 1: 0.72
                        Chunk 7: 0.65
```

## Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Vector DB | ChromaDB (PersistentClient) | Embedded, no external service |
| Embeddings | sentence-transformers MiniLM-L6-v2 | Fast, 384d, good quality |
| PDF Parser | pypdf | Pure Python, no system deps |
| Generation | Anthropic Claude SDK | Best reasoning for cited answers |
| API | FastAPI | Async, auto-docs, Pydantic |
| Validation | Pydantic v2 | Type-safe schemas |
