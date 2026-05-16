#!/usr/bin/env bash
#
# Snapshot the locally-built ChromaDB into a tarball you can upload to Brev.
# Skips re-ingesting 2,399 chunks on the cloud instance.
#
# Run this LOCALLY (on the machine where you ran `python -m backend.data.ingest`):
#
#   bash deployment/brev/snapshot-kb.sh
#
# Then upload kb_snapshot.tar.gz to /workspace/ on your Brev instance and the
# setup.sh script will pick it up automatically.

set -euo pipefail

CHROMA_DIR="${CHROMA_DIR:-backend/data/chroma}"
OUT="${OUT:-kb_snapshot.tar.gz}"

if [[ ! -d "$CHROMA_DIR" ]]; then
    echo "✗ No ChromaDB at $CHROMA_DIR — run `python -m backend.data.ingest --all` first."
    exit 1
fi

tar czf "$OUT" -C "$(dirname "$CHROMA_DIR")" "$(basename "$CHROMA_DIR")"
size=$(du -h "$OUT" | cut -f1)
echo "✓ wrote $OUT ($size)"
echo ""
echo "Upload to Brev:  scp $OUT brev:/workspace/   (or use Brev's file UI)"
