"""Answer generation using Claude SDK with retrieved context."""

from __future__ import annotations

import logging
from typing import Any

import anthropic

from config import config
from models.schemas import SearchResult

logger = logging.getLogger(__name__)


def generate_answer(question: str, sources: list[SearchResult]) -> str:
    """Generate an answer using Claude with retrieved context."""

    if not config.is_real_mode:
        return _demo_answer(question, sources)

    # Build context from sources
    context_parts = []
    for i, source in enumerate(sources, 1):
        meta = source.metadata
        filename = meta.get("filename", "unknown")
        context_parts.append(
            f"[Source {i} - {filename} (relevance: {source.score:.2f})]:\n{source.content}"
        )
    context = "\n\n".join(context_parts)

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    system_prompt = """You are an enterprise knowledge assistant. Answer questions based ONLY on the provided context.

Rules:
1. Only use information from the provided sources
2. Cite sources using [Source N] format
3. If the context doesn't contain enough info, say so clearly
4. Be concise but thorough
5. Structure your answer with clear sections if appropriate"""

    message = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=2048,
        system=system_prompt,
        messages=[{
            "role": "user",
            "content": f"Context from knowledge base:\n\n{context}\n\nQuestion: {question}"
        }]
    )

    return message.content[0].text


def _demo_answer(question: str, sources: list[SearchResult]) -> str:
    """Generate a demo answer using source content directly."""
    if not sources:
        return (
            f"I don't have enough information in the knowledge base to answer: '{question}'\n\n"
            "Please ingest relevant documents first using POST /api/v1/ingest."
        )

    # Build answer from sources
    answer = f"Based on the knowledge base, here's what I found about '{question[:80]}':\n\n"

    for i, source in enumerate(sources[:3], 1):
        filename = source.metadata.get("filename", "unknown")
        snippet = source.content[:300].strip()
        answer += f"**[Source {i} - {filename}]** (relevance: {source.score:.2f}):\n{snippet}\n\n"

    answer += "---\n*Note: Running in DEMO mode. Set ANTHROPIC_API_KEY and RAG_MODE=real for Claude-powered answers.*"
    return answer
