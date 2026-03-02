"""Document chunking with configurable size and overlap."""

from __future__ import annotations

import re
import uuid

from config import config
from models.schemas import Chunk, DocumentMetadata


def chunk_text(
    text: str,
    document_id: str,
    metadata: DocumentMetadata,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Chunk]:
    """Split text into overlapping chunks, respecting sentence boundaries."""
    chunk_size = chunk_size or config.CHUNK_SIZE
    chunk_overlap = chunk_overlap or config.CHUNK_OVERLAP

    # Clean the text
    text = re.sub(r'\n{3,}', '\n\n', text.strip())
    if not text:
        return []

    # Split by sentences first
    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current_chunk = ""
    chunk_index = 0

    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 > chunk_size and current_chunk:
            chunks.append(Chunk(
                document_id=document_id,
                content=current_chunk.strip(),
                metadata=metadata,
                chunk_index=chunk_index,
            ))
            chunk_index += 1

            # Keep overlap
            words = current_chunk.split()
            overlap_words = words[-chunk_overlap:] if len(words) > chunk_overlap else words
            current_chunk = " ".join(overlap_words) + " " + sentence
        else:
            current_chunk = current_chunk + " " + sentence if current_chunk else sentence

    # Last chunk
    if current_chunk.strip():
        chunks.append(Chunk(
            document_id=document_id,
            content=current_chunk.strip(),
            metadata=metadata,
            chunk_index=chunk_index,
        ))

    return chunks
