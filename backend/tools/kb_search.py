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
    # If athlete_id is provided, ALSO include this athlete's personal docs
    # (they were tagged with both `sport` and `athlete_id` at ingest time).
    where: Dict[str, Any] = {"sport": sport}
    if language in ("tr", "en"):
        # Chroma v1+ requires $and for multiple top-level filters
        where = {"$and": [{"sport": sport}, {"lang": language}]}

    coll = _coll()
    raw = coll.query(
        query_embeddings=[query_vec],
        n_results=settings.top_k_retrieval,
        where=where,
    )

    documents = (raw.get("documents") or [[]])[0]
    metadatas = (raw.get("metadatas") or [[]])[0]
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
