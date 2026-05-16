#!/usr/bin/env bash
#
# TulparAI · Brev one-shot setup
# ===============================
# Paste this whole block into a fresh Brev container's terminal (or run as a
# `.brev/setup.sh`).  It is idempotent — safe to re-run.
#
# What it does:
#   1. Installs system deps (Python 3.11, build tools)
#   2. Clones / pulls the repo
#   3. Creates a Python venv and installs requirements
#   4. Pulls the latest ChromaDB snapshot if you uploaded one to /workspace/kb_snapshot.tar.gz
#      (otherwise leaves the KB empty — you can ingest later from data/sources/<sport>/)
#   5. Seeds the four demo athletes
#   6. Boots uvicorn on 0.0.0.0:8000 inside `nohup` so the tunnel stays alive
#
# After it finishes:
#   • Open Brev's "Secure Links" tab → expose port 8000 → copy the public URL
#   • Paste that URL into Vercel as NEXT_PUBLIC_BACKEND_URL (frontend env)
#
# Requires these env vars in your Brev instance (set them in the dashboard or .env):
#   NVIDIA_API_KEY    — required, from build.nvidia.com
#   TAVILY_API_KEY    — optional but recommended for the web-search tool
#   OPENWEATHER_API_KEY — optional
#   USDA_API_KEY      — optional
#
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/abdulhamidbatayhi123/TulparAI.git}"
REPO_DIR="${REPO_DIR:-/workspace/tulparai}"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"
PORT="${PORT:-8000}"

log() { printf "\n\033[1;34m▶ %s\033[0m\n" "$*"; }
ok()  { printf "\033[1;32m✓ %s\033[0m\n" "$*"; }

# ── 1. System deps ────────────────────────────────────────────────────────
log "Installing system dependencies"
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    git curl ca-certificates build-essential \
    python3.11 python3.11-venv python3.11-dev \
    >/dev/null
ok "system deps ready"

# ── 2. Repo ───────────────────────────────────────────────────────────────
log "Syncing repo at $REPO_DIR"
if [[ -d "$REPO_DIR/.git" ]]; then
    git -C "$REPO_DIR" fetch --quiet
    git -C "$REPO_DIR" reset --hard origin/main
else
    mkdir -p "$(dirname "$REPO_DIR")"
    git clone --quiet "$REPO_URL" "$REPO_DIR"
fi
cd "$REPO_DIR"
ok "repo at $(git -C "$REPO_DIR" rev-parse --short HEAD)"

# ── 3. Python venv + requirements ─────────────────────────────────────────
log "Setting up Python venv"
if [[ ! -d backend/.venv ]]; then
    "$PYTHON_BIN" -m venv backend/.venv
fi
# shellcheck disable=SC1091
source backend/.venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r backend/requirements.txt
ok "venv ready ($(python --version))"

# ── 4. Environment ────────────────────────────────────────────────────────
log "Validating environment"
if [[ -z "${NVIDIA_API_KEY:-}" ]]; then
    echo "  ⚠  NVIDIA_API_KEY is not set in your environment."
    echo "     Either export it in your Brev shell or create backend/.env."
    if [[ ! -f backend/.env ]]; then
        echo "     Creating a stub backend/.env — fill it in then re-run this script."
        cp backend/.env.example backend/.env 2>/dev/null || cat > backend/.env <<EOF
NVIDIA_API_KEY=
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
OPENROUTER_API_KEY=
TAVILY_API_KEY=
OPENWEATHER_API_KEY=
USDA_API_KEY=
NEMOTRON_REASONER=nvidia/nemotron-3-super-120b-a12b
NEMOTRON_FAST=nvidia/nvidia-nemotron-nano-9b-v2
EMBEDDING_MODEL=nvidia/nv-embedqa-e5-v5
EOF
        exit 1
    fi
else
    if [[ ! -f backend/.env ]]; then
        cat > backend/.env <<EOF
NVIDIA_API_KEY=$NVIDIA_API_KEY
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-}
TAVILY_API_KEY=${TAVILY_API_KEY:-}
OPENWEATHER_API_KEY=${OPENWEATHER_API_KEY:-}
USDA_API_KEY=${USDA_API_KEY:-}
NEMOTRON_REASONER=nvidia/nemotron-3-super-120b-a12b
NEMOTRON_FAST=nvidia/nvidia-nemotron-nano-9b-v2
EMBEDDING_MODEL=nvidia/nv-embedqa-e5-v5
EOF
    fi
fi
ok "backend/.env present"

# ── 5. KB snapshot (optional) ─────────────────────────────────────────────
SNAPSHOT="/workspace/kb_snapshot.tar.gz"
if [[ -f "$SNAPSHOT" && ! -d backend/data/chroma ]]; then
    log "Restoring ChromaDB from $SNAPSHOT"
    tar xzf "$SNAPSHOT" -C backend/data/
    ok "KB restored ($(find backend/data/chroma -type f | wc -l) files)"
elif [[ ! -d backend/data/chroma ]]; then
    log "No KB snapshot found — leaving the KB empty"
    echo "     Web search fallback (web_search_trusted) will still work."
    echo "     To populate: upload PDFs to backend/data/sources/<sport>/ and run:"
    echo "       python -m backend.data.ingest --all"
fi

# ── 6. Seed demo athletes (idempotent) ────────────────────────────────────
log "Seeding demo athletes"
python -m backend.scripts.seed_demo >/dev/null 2>&1 || true
ok "athletes seeded"

# ── 7. Boot uvicorn under nohup so the tunnel survives shell exits ────────
log "Launching uvicorn on 0.0.0.0:$PORT"
pkill -f "uvicorn backend.main:app" 2>/dev/null || true
sleep 1
nohup python -m uvicorn backend.main:app --host 0.0.0.0 --port "$PORT" \
    > /workspace/uvicorn.log 2>&1 &
sleep 4
if curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null; then
    ok "uvicorn is up — tail /workspace/uvicorn.log for live output"
else
    echo "  ✗ uvicorn didn't respond. Last 40 log lines:"
    tail -40 /workspace/uvicorn.log
    exit 1
fi

cat <<EOF

────────────────────────────────────────────────────────────────────
  TulparAI backend is live on http://0.0.0.0:$PORT
  Expose it: Brev dashboard → Secure Links → add port $PORT → copy URL
  Then in Vercel: set NEXT_PUBLIC_BACKEND_URL to that URL and redeploy.

  Routes: /health · /chat/stream · /profile · /log · /upload
          /anomaly/{check,check-batch,demo} · /anomaly-dashboard

  Live logs:  tail -f /workspace/uvicorn.log
  Restart:    pkill -f 'uvicorn backend.main' && nohup python -m uvicorn \\
                backend.main:app --host 0.0.0.0 --port $PORT \\
                > /workspace/uvicorn.log 2>&1 &
────────────────────────────────────────────────────────────────────
EOF
