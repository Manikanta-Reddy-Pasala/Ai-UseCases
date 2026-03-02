"""Document parsers for different file types."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def parse_text(content: bytes, filename: str) -> list[dict]:
    """Parse plain text file."""
    text = content.decode("utf-8", errors="replace")
    return [{"text": text, "page": 1, "total_pages": 1}]


def parse_pdf(content: bytes, filename: str) -> list[dict]:
    """Parse PDF file using pypdf."""
    try:
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(content))
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append({"text": text, "page": i + 1, "total_pages": len(reader.pages)})
        return pages if pages else [{"text": "(Empty PDF)", "page": 1, "total_pages": 0}]
    except ImportError:
        logger.warning("pypdf not installed, treating PDF as text")
        return parse_text(content, filename)
    except Exception as e:
        logger.error(f"PDF parse error: {e}")
        return [{"text": f"Error parsing PDF: {e}", "page": 1, "total_pages": 0}]


def parse_markdown(content: bytes, filename: str) -> list[dict]:
    """Parse markdown file."""
    text = content.decode("utf-8", errors="replace")
    return [{"text": text, "page": 1, "total_pages": 1}]


PARSERS = {
    ".txt": parse_text,
    ".md": parse_markdown,
    ".pdf": parse_pdf,
    ".py": parse_text,
    ".java": parse_text,
    ".js": parse_text,
    ".json": parse_text,
    ".yaml": parse_text,
    ".yml": parse_text,
    ".xml": parse_text,
    ".html": parse_text,
    ".csv": parse_text,
}


def parse_document(content: bytes, filename: str) -> list[dict]:
    """Parse a document based on file extension."""
    ext = os.path.splitext(filename)[1].lower()
    parser = PARSERS.get(ext, parse_text)
    return parser(content, filename)
