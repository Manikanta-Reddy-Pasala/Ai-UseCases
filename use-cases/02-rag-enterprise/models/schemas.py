from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    filename: str
    file_type: str = ""
    page_number: int = 0
    total_pages: int = 0
    ingested_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class Chunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    content: str
    metadata: DocumentMetadata
    chunk_index: int = 0


class IngestResponse(BaseModel):
    document_id: str
    filename: str
    chunks_created: int
    status: str = "success"


class SearchResult(BaseModel):
    chunk_id: str
    content: str
    score: float
    metadata: dict[str, Any] = {}


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    filter_filename: str | None = None


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: list[SearchResult] = []
    mode: str = "demo"
    duration_ms: int = 0


class CollectionStats(BaseModel):
    total_documents: int = 0
    total_chunks: int = 0
    collection_name: str = "enterprise_docs"


class HealthResponse(BaseModel):
    status: str = "ok"
    mode: str = "demo"
    embedding_model: str = ""
    total_chunks: int = 0
