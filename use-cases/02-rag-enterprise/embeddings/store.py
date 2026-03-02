"""Vector store using ChromaDB with sentence-transformers embeddings."""

from __future__ import annotations

import logging
from typing import Any

import chromadb

from config import config
from models.schemas import Chunk, SearchResult

logger = logging.getLogger(__name__)

# Global ChromaDB client and collection
_client: chromadb.ClientAPI | None = None
_collection = None
_embedding_fn = None

COLLECTION_NAME = "enterprise_docs"


def _get_embedding_function():
    """Get or create the embedding function."""
    global _embedding_fn
    if _embedding_fn is not None:
        return _embedding_fn

    try:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        _embedding_fn = SentenceTransformerEmbeddingFunction(
            model_name=config.EMBEDDING_MODEL
        )
        logger.info(f"Loaded embedding model: {config.EMBEDDING_MODEL}")
        return _embedding_fn
    except Exception as e:
        logger.error(f"Failed to load embedding model: {e}")
        # Fallback: use default chromadb embeddings
        return None


def _get_collection():
    """Get or create the ChromaDB collection."""
    global _client, _collection
    if _collection is not None:
        return _collection

    import os
    os.makedirs(config.CHROMA_PERSIST_DIR, exist_ok=True)
    try:
        _client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)
    except Exception:
        # Fallback to ephemeral client if persistent fails
        _client = chromadb.EphemeralClient()
        logger.warning("Using ephemeral ChromaDB (data not persisted)")

    ef = _get_embedding_function()
    kwargs = {"name": COLLECTION_NAME}
    if ef:
        kwargs["embedding_function"] = ef

    _collection = _client.get_or_create_collection(**kwargs)
    logger.info(f"ChromaDB collection '{COLLECTION_NAME}' ready ({_collection.count()} chunks)")
    return _collection


def add_chunks(chunks: list[Chunk]) -> int:
    """Add document chunks to the vector store."""
    if not chunks:
        return 0

    collection = _get_collection()

    ids = [c.chunk_id for c in chunks]
    documents = [c.content for c in chunks]
    metadatas = [
        {
            "document_id": c.document_id,
            "filename": c.metadata.filename,
            "file_type": c.metadata.file_type,
            "page_number": c.metadata.page_number,
            "chunk_index": c.chunk_index,
        }
        for c in chunks
    ]

    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    logger.info(f"Added {len(chunks)} chunks to vector store")
    return len(chunks)


def search(query: str, top_k: int = 5, filter_dict: dict[str, Any] | None = None) -> list[SearchResult]:
    """Search the vector store for relevant chunks."""
    collection = _get_collection()

    kwargs: dict[str, Any] = {
        "query_texts": [query],
        "n_results": min(top_k, collection.count()) if collection.count() > 0 else top_k,
    }
    if filter_dict:
        kwargs["where"] = filter_dict

    try:
        results = collection.query(**kwargs)
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []

    search_results = []
    if results and results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            score = 1 - (results["distances"][0][i] if results["distances"] else 0)
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            search_results.append(SearchResult(
                chunk_id=results["ids"][0][i] if results["ids"] else "",
                content=doc,
                score=round(score, 4),
                metadata=metadata,
            ))

    return search_results


def get_stats() -> dict:
    """Get collection statistics."""
    collection = _get_collection()
    return {
        "total_chunks": collection.count(),
        "collection_name": COLLECTION_NAME,
    }


def delete_document(document_id: str) -> int:
    """Delete all chunks for a document."""
    collection = _get_collection()
    # Get chunks for this document
    results = collection.get(where={"document_id": document_id})
    if results and results["ids"]:
        collection.delete(ids=results["ids"])
        return len(results["ids"])
    return 0
