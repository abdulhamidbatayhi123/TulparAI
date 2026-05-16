# TulparAI · NVIDIA Brev deployment

Step-by-step to get a public `https://…brevlab.com` URL for the FastAPI backend.
Target: live in ~15 min using the $350 NVIDIA Brev credit.

> **What this does and doesn't do.**
> Brev hosts your *backend container* (the FastAPI orchestrator + ChromaDB + SQLite).
> The actual LLM inference still runs at `build.nvidia.com` — Brev does NOT make
> individual answers faster. What Brev gives you is a **public URL judges can hit
> from any phone**, plus an always-on backend so you don't need to keep your
> laptop awake during the demo.

---

## 1. Brev account + credit (one-time, ~5 min)

1. Sign up at **<https://brev.dev>** (or **<https://nvidia.com/brev>**).
2. Apply the **$350 NVIDIA Brev credit code** in *Settings → Billing*.
   (If you don't see the code, it usually comes from your hackathon organiser's
   email or appears as a balance automatically.)
3. Verify the credit appears as available balance.

---

## 2. Create the instance (one-time, ~3 min)

| Setting | Value | Why |
|---|---|---|
| **Type** | GPU (cheapest: **L4 / A10 / T4**) | LLM inference is hosted at NVIDIA, so the GPU here just runs our local cross-encoder reranker. Anything > T4 is over-spec. |
| **Image** | `nvidia/cuda:12.2.0-runtime-ubuntu22.04` (or any Ubuntu 22.04) | Standard |
| **Disk** | 50 GB | Plenty for repo + venv + 2.4k-chunk ChromaDB |
| **Auto-stop** | **DISABLE** on the day of demo | Otherwise it'll sleep mid-pitch |

Brev calls this a "Launchable" or "Instance". Click *Launch* and wait ~2 min
for it to boot.

---

## 3. Set the secrets (~1 min)

In the Brev dashboard for your instance, find *Environment Variables* or
*Secrets* and add at least:

```env
NVIDIA_API_KEY=nvapi-…           # required — your build.nvidia.com key
TAVILY_API_KEY=tvly-…            # optional — enables web_search_trusted
OPENWEATHER_API_KEY=…            # optional — enables get_weather
USDA_API_KEY=…                   # optional — enables get_food_macros via USDA
```

(If Brev's UI doesn't let you add env vars, you can paste them into
`backend/.env` after the setup script runs — the script generates a stub if it
finds none.)

---

## 4. (Optional but recommended) Snapshot your KB locally

So the cloud instance doesn't have to re-download + re-embed all the PDFs:

```bash
# Run on YOUR laptop, where you already ingested 2,399 chunks
bash deployment/brev/snapshot-kb.sh
# → writes kb_snapshot.tar.gz (~30-80 MB)
```

Upload `kb_snapshot.tar.gz` to `/workspace/` on your Brev instance — use the
**Files** tab in Brev's web UI, or `scp` if you have SSH set up.

If you skip this step, `web_search_trusted` (Tavily) still works as a
fallback, but `search_sport_kb` will return empty until you upload PDFs and
run `python -m backend.data.ingest --all` manually on Brev.

---

## 5. Run the setup script (~5 min)

Open the Brev instance terminal (web UI → *Terminal* or *SSH*), then:

```bash
curl -fsSL https://raw.githubusercontent.com/abdulhamidbatayhi123/TulparAI/main/deployment/brev/setup.sh -o setup.sh
bash setup.sh
```

Or if you've already pulled the repo:

```bash
cd /workspace/tulparai
bash deployment/brev/setup.sh
```

The script:

1. Installs Python 3.11 + build deps
2. Clones / pulls the repo to `/workspace/tulparai`
3. Creates venv + installs requirements (incl. anomaly module's torch/sklearn)
4. Restores the KB snapshot from `/workspace/kb_snapshot.tar.gz` if present
5. Seeds the four demo athletes
6. Starts uvicorn under `nohup` on port 8000

When it finishes you'll see a green banner with the local URL. Verify:

```bash
curl http://127.0.0.1:8000/health
# → {"status":"ok",…}
```

---

## 6. Expose port 8000 publicly (~2 min)

In the Brev dashboard for your instance:

1. Go to **Secure Links** (or **Tunnels** / **Sharing**).
2. Click **Add Link** → enter port **8000** → name it `tulparai-backend`.
3. Brev gives you a URL like `https://tulparai-backend-xxxx.brevlab.com`.
4. Test it from your laptop:

```bash
curl https://tulparai-backend-xxxx.brevlab.com/health
```

5. *Edit Access* → **Public** (so judges' phones can hit it without auth).

---

## 7. Point the frontend at it

**If you're deploying frontend to Vercel:**
```
NEXT_PUBLIC_BACKEND_URL=https://tulparai-backend-xxxx.brevlab.com
NEXT_PUBLIC_DEFAULT_LANG=tr
NEXT_PUBLIC_DEFAULT_ATHLETE=ahmet
```
Redeploy the Vercel project.

**If you're still demoing from `npm run dev` locally:**
edit `frontend/.env.local` with the same `NEXT_PUBLIC_BACKEND_URL=…` and
restart the dev server.

---

## 8. Final smoke test

```bash
# From any device:
curl https://tulparai-backend-xxxx.brevlab.com/health
curl https://tulparai-backend-xxxx.brevlab.com/anomaly/demo | python -m json.tool | head -20

# Chat:
curl -X POST https://tulparai-backend-xxxx.brevlab.com/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"athlete_id":"ahmet","message":"Konkusyon sonrasi protokol nedir?","language":"tr"}' \
  --max-time 90
```

You should see the SSE stream with `step`, `tool_call`, `token`, `done`.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `curl` to the public URL hangs | Check Brev tunnel is on port **8000** (not 80). Toggle it off/on. |
| Chat returns "LLM client not available" | `NVIDIA_API_KEY` not set. `echo $NVIDIA_API_KEY` on Brev, then `pkill uvicorn` + rerun setup. |
| `search_sport_kb` returns `[]` | KB is empty. Either upload `kb_snapshot.tar.gz` and re-run setup, or ingest PDFs on Brev. |
| Instance keeps stopping | Disable auto-stop in the Brev dashboard. |
| Anomaly model not loading | Check `backend/anomaly/saved_models/` was uploaded with the repo (it should be — it's a tracked binary). |

---

## Cost expectation

L4 / A10 / T4 on Brev runs roughly $0.40-$1.00 per hour. A 24-hour
demo-window is $10-$24 — well within the $350 credit. **Stop the instance
right after the pitch** if you're billed hourly.

```bash
# In the Brev dashboard: instance → "Stop" button
# (You can restart it later without losing the disk content.)
```
