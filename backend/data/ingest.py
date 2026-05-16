"""PDF/HTML → chunks → ChromaDB ingestion CLI.

Usage:
    cd backend
    ./.venv/Scripts/python.exe -m backend.data.ingest --sport football
    ./.venv/Scripts/python.exe -m backend.data.ingest --all

Files in `backend/data/sources/<sport>/*.{pdf,html,htm}` are processed:
  extract → detect language → chunk → embed → upsert to ChromaDB.

Idempotent: chunk IDs are sha1(source_url_or_name + chunk_text)[:16], so re-running
the same PDF doesn't create duplicates.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import chromadb
from pypdf import PdfReader
from bs4 import BeautifulSoup
from langdetect import detect, LangDetectException, DetectorFactory

# Make langdetect deterministic
DetectorFactory.seed = 0

from backend.config import settings
from backend.data.chunker import chunk_text
from backend.data.embedder import embed_batch
from backend.tools.kb_search import COLLECTION_NAME, VALID_SPORTS

# Filename-token → (source_type, authority_score)
AUTHORITY: dict[str, tuple[str, float]] = {
    "ioc":          ("ioc", 1.0),
    "olympic":      ("ioc", 1.0),
    "who":          ("ioc", 1.0),
    "cdc":          ("ioc", 1.0),
    "nih":          ("ioc", 1.0),
    "wada":         ("ioc", 1.0),
    "gsb":          ("government", 1.0),
    "gov_tr":       ("government", 1.0),
    "tff":          ("federation", 0.9),
    "twf":          ("federation", 0.9),
    "thf":          ("federation", 0.9),
    "tvf":          ("federation", 0.9),
    "fifa":         ("federation", 0.9),
    "uefa":         ("federation", 0.9),
    "iwf":          ("federation", 0.9),
    "fivb":         ("federation", 0.9),
    "uww":          ("federation", 0.9),
    "nsca":         ("federation", 0.9),
    "acsm":         ("federation", 0.9),
    "bjsm":         ("journal", 0.85),
    "jissn":        ("journal", 0.85),
    "pubmed":       ("journal", 0.85),
    "frontiers":    ("journal", 0.85),
    "ais":          ("national_institute", 0.8),
    "usa_wrestling": ("national_institute", 0.8),
    "usoc":         ("national_institute", 0.8),
}


def _extract_text(path: Path) -> str:
    """Read text from PDF / HTML / TXT."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            reader = PdfReader(str(path))
            return "\n".join((p.extract_text() or "") for p in reader.pages)
        except Exception as e:
            print(f"  [WARN] PDF extract failed for {path.name}: {e}")
            return ""
    if suffix in (".html", ".htm"):
        html = path.read_text(encoding="utf-8", errors="ignore")
        return BeautifulSoup(html, "html.parser").get_text(" ")
    if suffix in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="ignore")
    return ""


def _detect_lang(text: str) -> str:
    sample = text.strip()[:1500]
    if not sample:
        return "en"
    try:
        d = detect(sample)
        return "tr" if d == "tr" else ("en" if d == "en" else "en")
    except LangDetectException:
        return "en"


def _classify_authority(filename_stem: str) -> tuple[str, float]:
    lower = filename_stem.lower()
    for token, (kind, score) in AUTHORITY.items():
        if token in lower:
            return kind, score
    return "federation", 0.85  # default trust


def _chunk_id(source_key: str, chunk_idx: int, chunk: str) -> str:
    """Hash source + chunk index + text → 16-char ID.

    Including `chunk_idx` prevents duplicate-ID collisions when a single PDF
    contains repeated text (e.g. headers, empty sections) that produce
    identical chunks. Idempotent: re-running the same file in the same order
    yields the same IDs.
    """
    return hashlib.sha1(f"{source_key}::{chunk_idx}::{chunk}".encode("utf-8")).hexdigest()[:16]


def ingest_sport(sport: str, source_dir: Path) -> dict:
    """Process every file in `source_dir`, returns summary dict."""
    if sport not in VALID_SPORTS:
        print(f"  [SKIP] unknown sport: {sport}")
        return {"sport": sport, "files": 0, "chunks": 0}
    if not source_dir.exists():
        print(f"  [SKIP] {source_dir} does not exist")
        return {"sport": sport, "files": 0, "chunks": 0}

    print(f"\n[ingest] sport={sport} from {source_dir}")
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    coll = client.get_or_create_collection(COLLECTION_NAME)

    files = sorted([
        p for p in source_dir.iterdir()
        if p.is_file() and p.suffix.lower() in (".pdf", ".html", ".htm", ".txt", ".md")
    ])
    if not files:
        print(f"  [SKIP] no PDF/HTML/TXT files in {source_dir}")
        return {"sport": sport, "files": 0, "chunks": 0}

    all_ids: list[str] = []
    all_texts: list[str] = []
    all_metas: list[dict] = []

    for path in files:
        text = _extract_text(path)
        if not text.strip():
            print(f"  [skip] empty/unreadable: {path.name}")
            continue

        lang = _detect_lang(text)
        source_type, authority = _classify_authority(path.stem)

        chunks = chunk_text(
            text,
            target=settings.chunk_size,
            overlap=settings.chunk_overlap,
        )
        for chunk_idx, c in enumerate(chunks):
            cid = _chunk_id(path.name, chunk_idx, c)
            all_ids.append(cid)
            all_texts.append(c)
            all_metas.append({
                "sport":           sport,
                "topic":           "general",
                "lang":            lang,
                "source_type":     source_type,
                "source_name":     path.stem.replace("_", " "),
                "source_url":      "",
                "chunk_id":        cid,
                "ingested_at":     datetime.now(timezone.utc).isoformat(),
                "authority_score": authority,
            })
        print(f"  + {path.name}: {len(chunks)} chunks ({lang}, auth {authority})")

    if not all_texts:
        print("  [ingest] nothing to embed")
        return {"sport": sport, "files": len(files), "chunks": 0}

    # Embed + upsert in batches
    print(f"  [embed] {len(all_texts)} chunks via {settings.embedding_model}...")
    embeddings = embed_batch(all_texts, input_type="passage")
    if len(embeddings) != len(all_texts):
        print(f"  [WARN] embedding count mismatch: got {len(embeddings)}, expected {len(all_texts)}")

    print(f"  [chroma] upserting {len(all_ids)} chunks...")
    coll.upsert(
        ids=all_ids,
        documents=all_texts,
        embeddings=embeddings,
        metadatas=all_metas,
    )
    print(f"[ingest] DONE — {sport}: {len(files)} files, {len(all_ids)} chunks")
    return {"sport": sport, "files": len(files), "chunks": len(all_ids)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingest sport documents into ChromaDB")
    ap.add_argument("--sport", choices=list(VALID_SPORTS), help="Single sport to ingest")
    ap.add_argument("--source-dir", help="Override source directory")
    ap.add_argument("--all", action="store_true", help="Ingest all 4 sports")
    args = ap.parse_args()

    root = Path("backend/data/sources")
    summary: list[dict] = []
    if args.all:
        for sport in VALID_SPORTS:
            summary.append(ingest_sport(sport, root / sport))
    elif args.sport:
        directory = Path(args.source_dir) if args.source_dir else (root / args.sport)
        summary.append(ingest_sport(args.sport, directory))
    else:
        ap.print_help()
        return 2

    print("\n=== INGESTION SUMMARY ===")
    for s in summary:
        print(f"  {s['sport']:15s} {s['files']:3d} files  {s['chunks']:5d} chunks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
