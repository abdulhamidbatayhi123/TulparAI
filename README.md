# 🐎 TulparAI — Türk Sporcular için Doğrulanmış AI Antrenör

> A multi-agent, tool-using, citation-verified AI adviser for Turkish athletes — built for the
> **100 StartUP Bootcamp Hackathon (YTÜ × Türksat × NVIDIA), 15–17 May 2026.**

**Theme codes:** `A3 Kapsayıcılık + B2 Kamuda AI Dönüşümü + C1, C2, C7 + D7`

> *Tulpar* — the winged horse of Turkic mythology. Swift, fearless, and never lost.

---

## What it does

Sport-specific (football · wrestling · weightlifting · volleyball), personalized
(profile + recent training/meal logs), verified (every factual claim cited & re-checked
against the tool that produced it) AI adviser for athletes.

**The wow demo:** the same question — *"Bugün antrenmandan önce ne yemeliyim?"* —
gets four different correct answers across four athletes with different sports, weight
classes, and goals. Same engine. Zero hallucinations.

## Architecture

```
Athlete → Frontend (Next.js on Vercel)
            │ SSE
            ▼
        Backend (FastAPI on Brev Tunnel)
            │
   ┌────────┼─────────────────────────────────┐
   │  [1] ANALYZER   Nemotron Nano 9B (JSON)  │
   │  [2] TOOL-USING REASONER                 │
   │       Nemotron 3 Super 49B + 6 tools    │
   │  [3] VERIFIER   Nemotron Nano 9B (JSON)  │
   │  [4] FORMATTER  rule-based               │
   └──────────────────────────────────────────┘

6 tools the Reasoner can call:
  • search_sport_kb (sport-filtered ChromaDB + reranker)
  • get_food_macros (USDA + Open Food Facts)
  • calc_macros (Mifflin-St Jeor + sport PAL)
  • get_weather (OpenWeather)
  • log_session (SQLite)
  • web_search_trusted (Tavily + domain whitelist)
```

The novel piece: evidence markers `[T1] [T2]` tie claims to specific tool *responses*,
and the Verifier strips any claim its tool didn't actually support.

## Stack

- **LLM:** NVIDIA Nemotron (build.nvidia.com), OpenRouter fallback
- **Embeddings:** `nvidia/nv-embedqa-e5-v5` — multilingual (TR+EN)
- **Backend:** Python 3.11 · FastAPI · ChromaDB · SQLite
- **Frontend:** Next.js 14 · Tailwind · shadcn/ui · SSE streaming
- **Deploy:** NVIDIA Brev (backend) + Vercel (frontend)

## Local setup

```bash
git clone https://github.com/abdulhamidbatayhi123/TulparAI.git
cd TulparAI

# ----- Backend -----
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
cp .env.example .env              # fill in NVIDIA_API_KEY etc.

# initialise DB + seed demo athletes
python -m backend.db.connection   # creates tulparai.db
python -m backend.scripts.seed_demo

# ingest sport knowledge bases (PDFs must be downloaded per MANIFEST.md first)
python -m backend.data.ingest --all

# start API server
uvicorn backend.main:app --reload --port 8000

# ----- Frontend (new terminal) -----
cd ../frontend
npm install
cp .env.example .env.local         # NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
npm run dev
# → http://localhost:3000
```

## Source documents

Sport PDFs and HTML files in `backend/data/sources/<sport>/` are **gitignored** (size +
copyright). See [`backend/data/sources/MANIFEST.md`](backend/data/sources/MANIFEST.md)
for the URL list and re-fetch instructions.

## Team

- **[Name]** — Backend / AI lead
- **[Name]** — Frontend lead
- **[Name]** — Data + Pitch lead

## License

MIT. See [LICENSE](LICENSE).
