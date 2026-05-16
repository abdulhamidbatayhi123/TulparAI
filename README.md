# 🐎 TulparAI — Türk Sporcular için Doğrulanmış AI Antrenör

> A multi-agent, tool-using, **citation-verified** AI adviser for Turkish athletes — built for the
> **100 StartUP Bootcamp Hackathon (YTÜ × Türksat × NVIDIA), 15–17 May 2026.**

**Theme codes:** `A3 Kapsayıcılık · B2 Kamuda AI Dönüşümü · C1, C2, C3, C5, C7 · D7`

> *Tulpar* — the winged horse of Turkic mythology. Swift, fearless, and never lost.

---

## The pitch in one paragraph

Most agents call tools and trust the model. **TulparAI calls tools, makes the model cite each
tool's output by index `[T1] [T2]`, then runs a separate Verifier model that strips any claim
the tools didn't support.** Zero hallucinations is not a slogan — it's an enforced invariant.
Deployed on Türksat-compatible NVIDIA infrastructure, ready for the Gençlik ve Spor Bakanlığı
to give every athlete in Turkey a personal cited coach + dietitian via web, Telegram, or voice.

---

## What it does

A sport-specific (football · wrestling · weightlifting · volleyball), personalised
(profile + recent training/meal logs), verified (every factual claim cited and re-checked
against the tool that produced it) AI adviser for athletes.

| Capability | How |
|---|---|
| Chat (TR + EN) | SSE streamed, live agent badges, live tool-call chips |
| Vision | Photo a meal / injury / pose → NVIDIA VLM extracts info |
| Voice | Web Speech API mic, Türkçe + English |
| Personal RAG | Upload your own training plan / bloodwork → per-athlete KB |
| Multi-tenant | Telegram bot — each user gets their own profile |
| Cited answers | Every `[Tx]` claim resolves to a real tool response |
| Verified | A second LLM strips any claim its tool didn't support |
| Sport-filtered KB | ChromaDB metadata `where={"sport": ...}` — no cross-sport contamination |

**The wow demo:** the same question — *"Bugün antrenmandan önce ne yemeliyim?"* —
gets four different correct answers across four athletes with different sports,
weight classes, and goals. Same engine. Zero hallucinations.

---

## Architecture

```
Athlete → Frontend (Next.js 16 on Vercel)
            │ SSE
            ▼
        Backend (FastAPI on NVIDIA Brev Tunnel)
            │
   ┌────────┼─────────────────────────────────────────────┐
   │  [0] REGEX FAST-PATH  greetings / thanks / identity  │  <50ms, no LLM
   │  [1] ANALYZER         Nemotron Nano 9B (JSON)        │
   │  [2] REASONER         Nemotron 3 Super 120B (MoE)    │  + 7 tools
   │  [3] VERIFIER         Nemotron Nano 9B (JSON)        │  skipped if no [Tx]
   │  [4] FORMATTER        rule-based                     │
   └──────────────────────────────────────────────────────┘

7 tools the Reasoner can call (OpenAI-style function calling):

  • search_sport_kb         sport-filtered ChromaDB + cross-encoder reranker
  • get_food_macros         USDA FoodData + Open Food Facts
  • calc_macros             Mifflin-St Jeor × sport PAL × goal multiplier
  • get_weather             OpenWeather (outdoor training adjustments)
  • log_session             SQLite — logs influence future answers
  • web_search_trusted      Tavily + domain whitelist (FIFA/UEFA/IOC/BJSM/…)
  • analyze_image           NVIDIA VLM (llama-3.2-90b-vision → nemotron-nano-12b-vl)
```

**The novel contribution:** evidence markers `[T1] [T2]` tie claims to specific tool
*responses* (not static documents), and the Verifier strips any claim its corresponding
tool didn't actually support. Stronger guarantee than retrieval-only verification.

---

## Knowledge base

ChromaDB collection `sport_kb`, **1,236 chunks** across 4 sports, indexed from
authority-weighted PDFs:

| Sport | Files | Chunks | Sources |
|---|---|---|---|
| Football | 1 | 79 | UEFA Medical Regulations 2025 |
| Wrestling | 2 | 366 | UWW Medical Regs 2024, NSCA Long-Term Athletic Development |
| Weightlifting | 2 | 707 | IWF Technical & Competition Rules 2020, NSCA Youth Resistance Training |
| Volleyball | 1 | 84 | FIVB Medical Injury Prevention |

All sources are **open-access**, **federation/IOC-authored**, classified at authority
**0.9–1.0**. Multilingual embedder (`nvidia/nv-embedqa-e5-v5`) means a Turkish query
retrieves matching English chunks natively — no translation step.

See [`backend/data/sources/MANIFEST.md`](backend/data/sources/MANIFEST.md) for re-fetch URLs.

---

## Stack

| Layer | Tech |
|---|---|
| LLM (primary) | NVIDIA Nemotron via [build.nvidia.com](https://build.nvidia.com) |
| LLM (fallback) | OpenRouter |
| Embeddings | `nvidia/nv-embedqa-e5-v5` (multilingual, 1024-dim) |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` (local CPU) |
| Backend | Python 3.11 · FastAPI · ChromaDB · SQLite |
| Frontend | Next.js 16 · React 19 · Tailwind 4 · @base-ui/react · Fraunces + Geist |
| Streaming | Server-Sent Events |
| Deploy | NVIDIA Brev Tunnel (backend) · Vercel (frontend) |

---

## Local setup

```bash
git clone https://github.com/abdulhamidbatayhi123/TulparAI.git
cd TulparAI

# ----- Backend -----
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
cp .env.example .env              # add NVIDIA_API_KEY, TAVILY_API_KEY, etc.

# initialise SQLite + seed demo athletes (Ahmet, Ayşe, Mehmet, Naim)
python -m backend.scripts.seed_demo

# (optional) ingest sport KB after dropping PDFs into backend/data/sources/<sport>/
python -m backend.data.ingest --all

# start API server
uvicorn backend.main:app --reload --port 8000
#   GET  /health        → status + configured model IDs
#   POST /chat/stream   → SSE chat
#   POST /profile       → upsert athlete
#   POST /upload        → personal doc ingestion
#   POST /log           → training/meal/weight/sleep logs

# ----- Frontend (new terminal) -----
cd ../frontend
npm install
cp .env.example .env.local        # NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
npm run dev                       # http://localhost:3000

# ----- Telegram (optional) -----
# Put TELEGRAM_BOT_TOKEN in backend/.env
python -m backend.telegram_bot
```

---

## Smoke tests

```bash
# Backend
PYTHONIOENCODING=utf-8 ./backend/.venv/Scripts/python.exe -m pytest backend/tests/ -q
# 24 passed

# End-to-end chat (Türkçe)
curl -X POST http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"athlete_id":"ahmet","message":"Konkusyon sonrasi futbolcu maca ne zaman doner?","language":"tr"}'
```

---

## Demo athletes

Seeded by `backend/scripts/seed_demo.py`:

| ID | Name | Sport | Detail |
|---|---|---|---|
| `ahmet` | Ahmet Yılmaz | football | striker · Süper Lig pro · Istanbul |
| `ayse` | Ayşe Demir | volleyball | middle blocker · F · Ankara |
| `mehmet` | Mehmet Akın | wrestling | 74 kg freestyle · 2 kg cut in 4 days · Konya |
| `naim` | Naim Süleyman | weightlifting | 89 kg · snatch 145 / C&J 180 · İzmir |

---

## Theme code coverage

| Code | How TulparAI hits it |
|---|---|
| **A3 Kapsayıcılık** | Every athlete in Turkey (800+ elite, 350K+ federated, 5M+ recreational) gets a personal coach — not just the ones who can afford a ₺1,500/session dietitian |
| **B2 Kamuda AI Dönüşümü** | Built for GSB / Türksat deployment; legally defensible because of the Verifier guardrail |
| **C1 Çoklu Ajan** | 4-agent pipeline: Analyzer → Reasoner → Verifier → Formatter |
| **C2 Tool kullanan** | OpenAI-style function calling, 7 tools, up to 3 iterations per turn |
| **C3 RAG** | Sport-filtered ChromaDB + authority-weighted reranker + multilingual embedder |
| **C5 Multimodal** | Vision (NVIDIA VLM) for meal photos, injury images; voice via Web Speech API |
| **C7 Doğrulama** | Verifier model strips unsupported `[Tx]` claims — the differentiator |
| **D7 Türkiye altyapısı** | NVIDIA build (Türksat-compatible), Turkish-first UX, Turkish federations (TFF / TWF / THF / TVF) in the whitelist |

---

## License

MIT. See [LICENSE](LICENSE).

---

## Team

- **Abdulhamid Batayhi** — Backend / AI / Frontend / Data / everything ([@abdulhamidbatayhi123](https://github.com/abdulhamidbatayhi123))
- with Claude as build partner
