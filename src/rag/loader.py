"""Document loader for HVAC standards and reference documents."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DocumentChunk:
    """A chunk of a document with metadata."""
    chunk_id: str
    text: str
    source: str  # e.g., "ashrae_90.1", "gb_50189"
    page: int = 0
    section: str = ""
    chunk_index: int = 0


def chunk_text(
    text: str,
    source: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    section: str = "",
) -> List[DocumentChunk]:
    """Split text into overlapping chunks.

    Args:
        text: Raw text to split.
        source: Document source identifier.
        chunk_size: Target chunk size in characters.
        chunk_overlap: Overlap between chunks in characters.
        section: Optional section name for metadata.

    Returns:
        List of DocumentChunk objects.
    """
    if not text.strip():
        return []

    chunks = []
    start = 0
    idx = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence-ending punctuation within the last 20% of the chunk
            search_start = max(start, end - chunk_size // 5)
            for sep in [". ", "。", "\n\n", "\n", "。 "]:
                last_sep = text.rfind(sep, search_start, end)
                if last_sep > search_start:
                    end = last_sep + len(sep)
                    break

        chunk_text_content = text[start:end].strip()
        if chunk_text_content:
            chunks.append(DocumentChunk(
                chunk_id=f"{source}_chunk_{idx:04d}",
                text=chunk_text_content,
                source=source,
                section=section,
                chunk_index=idx,
            ))
            idx += 1

        start = end - chunk_overlap if end < len(text) else len(text)

    return chunks


def load_text_document(filepath: str, source: str) -> List[DocumentChunk]:
    """Load a text file and split into chunks.

    This is a simple file-based loader. In production, this would be
    extended to handle PDF, DOCX, etc.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
        return chunk_text(text, source=source)
    except FileNotFoundError:
        return []
    except Exception:
        return []


def load_documents_from_dir(
    directory: str,
    source_prefix: str = "doc",
) -> List[DocumentChunk]:
    """Load all .txt files from a directory as document chunks."""
    import os
    all_chunks = []
    try:
        for filename in sorted(os.listdir(directory)):
            if filename.endswith('.txt') or filename.endswith('.md'):
                filepath = os.path.join(directory, filename)
                source = f"{source_prefix}/{filename.replace('.txt', '').replace('.md', '')}"
                chunks = load_text_document(filepath, source)
                all_chunks.extend(chunks)
    except FileNotFoundError:
        pass
    return all_chunks
