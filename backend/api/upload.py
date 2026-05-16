"""POST /upload — athlete uploads a personal document (training plan, blood test,
coach notes, federation guideline). File is parsed, chunked, embedded, and
stored in the SAME ChromaDB collection as the curated sport KB, but tagged
with `athlete_id` so retrieval can scope to "this athlete's docs only" or
"sport KB + this athlete's docs".

Ported from OpenAgent's `/upload` endpoint (multi-format text extraction
pattern), with TulparAI improvements:
  - athlete_id metadata for per-user scoping (OpenAgent had global only)
  - source_type="personal" to distinguish from federation docs
  - returns chunk count + ID so the UI can show "12 chunks indexed"
"""
from __future__ import annotations

import hashlib
import io
from datetime import datetime, timezone

import chromadb
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pypdf import PdfReader
from bs4 import BeautifulSoup

from backend.config import settings
from backend.data.chunker import chunk_text
from backend.data.embedder import embed_batch
from backend.db.repos import AthleteRepo
from backend.tools.kb_search import COLLECTION_NAME

router = APIRouter(prefix="/upload")

ALLOWED_EXTS = {".pdf", ".txt", ".md", ".html", ".htm"}


def _extract(content: bytes, ext: str) -> str:
    """Multi-format text extraction (ported from OpenAgent's helper)."""
    ext = ext.lower()
    if ext == ".pdf":
        try:
            reader = PdfReader(io.BytesIO(content))
            return "\n\n".join((p.extract_text() or "") for p in reader.pages)
        except Exception as e:
            raise HTTPException(400, detail=f"PDF parse failed: {e}")
    if ext in (".html", ".htm"):
        return BeautifulSoup(content.decode("utf-8", errors="ignore"), "html.parser").get_text(" ")
    if ext in (".txt", ".md"):
        return content.decode("utf-8", errors="ignore")
    raise HTTPException(400, detail=f"Unsupported file extension: {ext}")


def _chunk_id(athlete_id: str, filename: str, chunk: str) -> str:
    return hashlib.sha1(f"{athlete_id}::{filename}::{chunk}".encode("utf-8")).hexdigest()[:16]


@router.post("")
async def upload_document(
    athlete_id: str = Form(...),
    file: UploadFile = File(...),
    topic: str = Form("personal"),
):
    """Upload + ingest a personal document for this athlete.

    Form fields:
      athlete_id   athlete who owns the doc
      file         the file itself (multipart)
      topic        free-form tag (default "personal")
    """
    # Validate file
    if not file.filename:
        raise HTTPException(400, detail="no filename")
    name = file.filename
    ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in ALLOWED_EXTS:
        raise HTTPException(
            400,
            detail=f"Unsupported file type: {ext}. Allowed: {sorted(ALLOWED_EXTS)}",
        )

    # Validate athlete exists
    if not AthleteRepo().get(athlete_id):
        raise HTTPException(404, detail=f"athlete '{athlete_id}' not found")

    # Read + extract
    content = await file.read()
    if not content:
        raise HTTPException(400, detail="empty file")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, detail="file too large (max 10MB)")

    text = _extract(content, ext)
    if not text.strip():
        raise HTTPException(400, detail="no text extracted from file")

    # Chunk + embed + upsert into ChromaDB with athlete_id metadata
    chunks = chunk_text(
        text,
        target=settings.chunk_size,
        overlap=settings.chunk_overlap,
    )
    if not chunks:
        raise HTTPException(400, detail="no usable chunks (too short)")

    embeddings = embed_batch(chunks, input_type="passage")
    if len(embeddings) != len(chunks):
        raise HTTPException(500, detail="embedding count mismatch")

    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    coll = client.get_or_create_collection(COLLECTION_NAME)

    profile = AthleteRepo().get(athlete_id)
    sport = profile.get("sport", "football") if profile else "football"
    now_iso = datetime.now(timezone.utc).isoformat()

    ids = [_chunk_id(athlete_id, name, c) for c in chunks]
    metas = [
        {
            "sport": sport,             # tagged with the athlete's sport so sport-filter still matches
            "athlete_id": athlete_id,   # NEW: enables per-user scoping
            "topic": topic,
            "lang": "tr",               # caller can override later
            "source_type": "personal",  # distinguishes from federation/IOC docs
            "source_name": f"Personal: {name}",
            "source_url": "",
            "chunk_id": cid,
            "ingested_at": now_iso,
            "authority_score": 0.7,     # personal docs ranked below federation/IOC
        }
        for cid, c in zip(ids, chunks)
    ]
    coll.upsert(ids=ids, documents=chunks, embeddings=embeddings, metadatas=metas)

    return {
        "ok": True,
        "athlete_id": athlete_id,
        "filename": name,
        "chunks_indexed": len(chunks),
        "sport_tag": sport,
        "text_length": len(text),
    }


@router.get("/{athlete_id}")
def list_personal_docs(athlete_id: str):
    """List a summary of personal docs uploaded by this athlete."""
    client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    coll = client.get_or_create_collection(COLLECTION_NAME)
    got = coll.get(where={"athlete_id": athlete_id}, limit=500)

    # Group chunks by source_name to give a per-file summary
    by_file: dict[str, dict] = {}
    for meta in (got.get("metadatas") or []):
        name = meta.get("source_name", "?")
        if name not in by_file:
            by_file[name] = {"source_name": name, "chunks": 0, "ingested_at": meta.get("ingested_at")}
        by_file[name]["chunks"] += 1

    return {"athlete_id": athlete_id, "files": list(by_file.values())}
