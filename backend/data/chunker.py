"""Sentence-aware text chunker for RAG ingestion.

Goals:
  - Chunks are coherent (don't break mid-sentence)
  - Configurable target size (chars) with overlap
  - Drop chunks below a min length (noise filter)
  - Stable: same input → same chunks (so chunk_id hashes are deterministic)
"""
from __future__ import annotations

import re
from typing import List

# Splits on sentence-ending punctuation followed by whitespace.
# Covers TR (.!?) and EN. Doesn't cover abbreviations perfectly — that's fine for RAG.
_SENT_BOUND = re.compile(r"(?<=[.!?])\s+")


def chunk_text(
    text: str,
    target: int = 600,
    overlap: int = 120,
    min_len: int = 80,
) -> List[str]:
    """Split `text` into chunks of ~`target` chars, with `overlap` carryover, dropping <`min_len`."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= target:
        return [text] if len(text) >= min_len else []

    sentences = _SENT_BOUND.split(text)
    chunks: List[str] = []
    buf = ""

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if len(buf) + len(sent) + 1 <= target:
            buf = (buf + " " + sent).strip() if buf else sent
        else:
            if len(buf) >= min_len:
                chunks.append(buf)
            # carry the tail of the previous buffer as overlap context
            tail = buf[-overlap:] if len(buf) > overlap else buf
            buf = (tail + " " + sent).strip()

    if buf and len(buf) >= min_len:
        chunks.append(buf)
    return chunks
