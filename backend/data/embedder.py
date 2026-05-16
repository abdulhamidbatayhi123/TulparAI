"""NVIDIA hosted embeddings wrapper.

Uses `nvidia/nv-embedqa-e5-v5` by default (1024-dim, multilingual TR + EN).
Batches up to 32 texts per request (NVIDIA's safe limit).

Two entry points:
  - embed_batch(texts, input_type)  → list of float vectors
  - embed_query(text)               → single vector for retrieval
"""
from __future__ import annotations

import time
from typing import List
from openai import OpenAI

from backend.config import settings

# Lazy singleton client (one per process)
_client: OpenAI | None = None
BATCH_SIZE = 32


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.nvidia_api_key:
            raise RuntimeError("NVIDIA_API_KEY missing (add to backend/.env)")
        _client = OpenAI(
            api_key=settings.nvidia_api_key,
            base_url=settings.nvidia_base_url,
        )
    return _client


def embed_batch(texts: List[str], input_type: str = "passage", retries: int = 3) -> List[List[float]]:
    """Embed up to 32 texts in one request. Auto-batches if list is longer.

    input_type:
      - "passage" for documents being indexed
      - "query"   for retrieval queries
    """
    if not texts:
        return []

    client = _get_client()
    all_vectors: List[List[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        # nv-embedqa-e5-v5 has 512-token limit. Truncate aggressively for safety.
        batch = [t[:8000] for t in batch]  # ~2000 tokens at 4 chars/token avg

        attempt = 0
        while True:
            try:
                resp = client.embeddings.create(
                    model=settings.embedding_model,
                    input=batch,
                    extra_body={"input_type": input_type, "truncate": "END"},
                )
                all_vectors.extend(d.embedding for d in resp.data)
                break
            except Exception as e:
                attempt += 1
                if attempt >= retries:
                    raise
                wait = 2 ** attempt
                print(f"  [embedder] error on batch {i//BATCH_SIZE}, retry {attempt}/{retries} in {wait}s: {e}")
                time.sleep(wait)

    return all_vectors


def embed_query(text: str) -> List[float]:
    """Convenience: embed a single query string for retrieval."""
    vectors = embed_batch([text], input_type="query")
    return vectors[0] if vectors else []
