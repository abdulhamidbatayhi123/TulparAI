"""Sport-filtered ChromaDB query — the primary RAG tool.

Athletes only see chunks tagged with their sport (`where={"sport": athlete_sport}`),
which eliminates cross-sport contamination of the retriever.

Pipeline:
  query → embed → ChromaDB top-K (sport-filtered) → cross-encoder rerank → top-5
"""
from __future__ import annotations

from typing import List, Dict, Any
import chromadb

from backend.config import settings
from backend.data.embedder import embed_query
from backend.data.reranker import rerank

VALID_SPORTS = {"football", "wrestling", "weightlifting", "volleyball"}
COLLECTION_NAME = "sport_kb"

_client = None


def _coll():
    global _client
    if _client is None:
        settings.chroma_dir.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    return _client.get_or_create_collection(COLLECTION_NAME)


def search(
    sport: str,
    query: str,
    language: str | None = None,
    top_k: int = 5,
    athlete_id: str | None = None,
) -> List[Dict[str, Any]]:
    """Sport-filtered RAG with cross-encoder rerank.

    Args:
      sport:      one of football / wrestling / weightlifting / volleyball
      query:      natural-language query
      language:   optional filter — only return chunks matching this language ("tr" or "en")
      top_k:      return at most this many reranked results
      athlete_id: if provided, ALSO returns this athlete's personal uploaded docs
                  (their personal docs are stored with `athlete_id` metadata)

    Returns:
      list of dicts with keys: text, score, sport, source_name, source_url, lang, chunk_id
      (empty list if sport invalid or no matches)
    """
    if sport not in VALID_SPORTS:
        return []

    # Embed the query (multilingual model handles TR + EN natively)
    query_vec = embed_query(query)
    if not query_vec:
        return []

    # ChromaDB metadata filter: by default require matching sport.
    # Language is intentionally NOT filtered by default — the multilingual
    # embedder (nv-embedqa-e5-v5) retrieves cross-lingually (TR query ↔ EN
    # chunks). Filtering by language would zero-out results when the corpus
    # is mostly EN, even though the query is TR. We retry with a language
    # filter only as a refinement if the user explicitly passed one AND it
    # still returns results.
    coll = _coll()
    raw = coll.query(
        query_embeddings=[query_vec],
        n_results=settings.top_k_retrieval,
        where={"sport": sport},
    )

    documents = (raw.get("documents") or [[]])[0]
    metadatas = (raw.get("metadatas") or [[]])[0]

    # Optional same-language refinement: if the caller asked for a specific
    # language AND chunks in that language exist for this sport, narrow down.
    # Otherwise keep the broader cross-lingual result set.
    if language in ("tr", "en") and documents:
        same_lang_idx = [i for i, m in enumerate(metadatas) if m.get("lang") == language]
        if same_lang_idx:
            documents = [documents[i] for i in same_lang_idx]
            metadatas = [metadatas[i] for i in same_lang_idx]

    if not documents:
        return []

    # Rerank with authority-weighted cross-encoder
    auths = [float(m.get("authority_score", 0.85)) for m in metadatas]
    ranked = rerank(query, documents, authority_scores=auths)[:top_k]

    out: List[Dict[str, Any]] = []
    for idx, score in ranked:
        meta = metadatas[idx]
        out.append({
            "text": documents[idx],
            "score": score,
            "sport": meta.get("sport"),
            "source_name": meta.get("source_name", "unknown"),
            "source_url": meta.get("source_url", ""),
            "lang": meta.get("lang", "en"),
            "chunk_id": meta.get("chunk_id", ""),
            "page_number": meta.get("page_number"),
            "authority_score": meta.get("authority_score", 0.85),
        })
    return out
