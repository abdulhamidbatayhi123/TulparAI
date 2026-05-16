"""Local cross-encoder reranker.

Takes the top-K results from the embedding-based retrieval and re-scores each
(query, document) pair using a small cross-encoder model. Cross-encoders are
much more accurate than cosine similarity because they look at the query and
document together, but they're too slow to use as the primary retriever.

Model: `cross-encoder/ms-marco-MiniLM-L-6-v2`
  - ~90 MB, downloaded on first use (cached in ~/.cache/huggingface)
  - CPU is fine (no GPU needed)
  - Multilingual via the underlying mBERT-derived weights
  - Reranks 15 docs in ~150 ms on a modern laptop
"""
from __future__ import annotations

from typing import List, Tuple

_model = None
MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def _get_model():
    """Lazy-load the cross-encoder. First call downloads ~90MB."""
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder
        _model = CrossEncoder(MODEL_NAME)
    return _model


def rerank(
    query: str,
    docs: List[str],
    authority_scores: List[float] | None = None,
    score_floor: float = -1e9,
) -> List[Tuple[int, float]]:
    """Score every (query, doc) pair and return [(original_index, combined_score), ...] sorted desc.

    Args:
      query:            the user's question
      docs:             list of document strings to rank
      authority_scores: optional per-doc trust weights (multiplied into the rerank score).
                        Higher = more authoritative. Typical range 0.8-1.0.
      score_floor:      drop results below this combined score (default: keep all)

    Returns:
      list of (index_into_docs, combined_score) sorted by score descending.
    """
    if not docs:
        return []
    model = _get_model()
    pairs = [(query, d) for d in docs]
    raw = model.predict(pairs).tolist()

    if authority_scores is None:
        combined = raw
    else:
        if len(authority_scores) != len(docs):
            authority_scores = [0.85] * len(docs)
        combined = [s * a for s, a in zip(raw, authority_scores)]

    ranked = sorted(enumerate(combined), key=lambda x: x[1], reverse=True)
    return [(i, float(s)) for i, s in ranked if s > score_floor]
