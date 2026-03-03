# Implementation Details — Enterprise RAG System

## Project Structure

```
02-rag-enterprise/
├── main.py                  # FastAPI app, routes, web UI
├── config.py                # Env config (model, chunk size, ports)
├── ingestion/
│   ├── parser.py            # PDF/MD/TXT/code file parsing
│   └── chunker.py           # Sentence-aware text chunking
├── embeddings/
│   └── store.py             # ChromaDB vector store operations
├── generation/
│   └── answer.py            # Claude-powered answer generation
├── models/
│   └── schemas.py           # Pydantic models
├── data/
│   └── documents/           # Sample documents
│       └── sample-ai-architecture.md
├── .env.example
├── requirements.txt
└── Dockerfile
```

## Key Code Walkthrough

### 1. Document Parser (`ingestion/parser.py`)

```python
PARSERS = {
    ".pdf": parse_pdf,      # pypdf → list of {text, page, total_pages}
    ".md": parse_markdown,   # UTF-8 decode
    ".txt": parse_text,      # UTF-8 decode
    ".py": parse_text,       # Code files treated as text
    ".java": parse_text,
    ".json": parse_text,
}

def parse_document(content: bytes, filename: str) -> list[dict]:
    ext = os.path.splitext(filename)[1].lower()
    parser = PARSERS.get(ext, parse_text)
    return parser(content, filename)
    # Returns: [{"text": "...", "page": 1, "total_pages": 5}, ...]
```

### 2. Chunker (`ingestion/chunker.py`)

```python
def chunk_text(text, document_id, metadata, chunk_size=500, chunk_overlap=50):
    sentences = re.split(r'(?<=[.!?])\s+', text)  # Split at sentence boundaries

    chunks = []
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
            chunks.append(Chunk(content=current_chunk, ...))
            # Keep overlap: last N words
            words = current_chunk.split()
            current_chunk = " ".join(words[-chunk_overlap:]) + " " + sentence
        else:
            current_chunk += " " + sentence
    # Returns list of Chunk objects with metadata
```

### 3. Vector Store (`embeddings/store.py`)

```python
# Initialize ChromaDB with sentence-transformer embeddings
client = chromadb.PersistentClient(path="./data/chroma_db")
embedding_fn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
collection = client.get_or_create_collection("enterprise_docs", embedding_function=embedding_fn)

# Add chunks (embedding happens automatically)
collection.add(ids=[...], documents=[...], metadatas=[...])

# Search (query embedding + cosine similarity)
results = collection.query(query_texts=["vector databases"], n_results=5)
# Returns: documents, distances, metadatas, ids
```

### 4. Answer Generation (`generation/answer.py`)

```python
# Real mode: Claude with retrieved context
system = "Answer based ONLY on provided sources. Cite using [Source N]."
context = "\n".join(f"[Source {i}]: {source.content}" for i, source in enumerate(sources))

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    system=system,
    messages=[{"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}]
)

# Demo mode: formats source snippets directly as answer
```

## API Reference

| Endpoint | Method | Body | Returns |
|----------|--------|------|---------|
| `/api/v1/ingest` | POST | `file` (multipart) | `{document_id, chunks_created}` |
| `/api/v1/query` | POST | `{question, top_k, filter_filename}` | `{answer, sources[], duration_ms}` |
| `/api/v1/stats` | GET | - | `{total_chunks, collection_name}` |
| `/api/v1/documents/{id}` | DELETE | - | `{chunks_deleted}` |
| `/api/v1/health` | GET | - | `{status, mode, embedding_model, total_chunks}` |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `RAG_MODE` | `demo` | `demo` or `real` |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model |
| `CHUNK_SIZE` | `500` | Max characters per chunk |
| `CHUNK_OVERLAP` | `50` | Words overlap between chunks |
| `CHROMA_PERSIST_DIR` | `./data/chroma_db` | Vector DB path |
| `PORT` | `8001` | Server port |

## Test Results

```
✓ Health check: OK, 13 chunks, MiniLM-L6-v2
✓ Query "vector databases": 3 sources found, 24ms
✓ Query "ReAct pattern": 3 sources found
✓ Collection has 13 chunks from sample document
```
