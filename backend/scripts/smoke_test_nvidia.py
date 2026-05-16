"""Smoke test for the NVIDIA-hosted LLM client.

Run with:
    cd backend
    ./.venv/Scripts/python.exe -m backend.scripts.smoke_test_nvidia

What it does:
  1. Lists all model IDs accessible to your API key (so we know which to put in .env).
  2. Calls the configured `NEMOTRON_FAST` model in JSON mode  — proves Analyzer/Verifier path.
  3. Calls the configured `NEMOTRON_REASONER` model in free-form mode — proves Reasoner path.
  4. Calls the embedding model.

If any step fails with `model_not_found`, the listing in step 1 tells us what to switch to.

NB: no emoji prints — Windows cp1252 console can't render them and crashes the script.
"""
from __future__ import annotations

import io
import json
import sys
from backend.config import settings
from backend.llm.nvidia_client import chat, list_available_models

# Force UTF-8 stdout on Windows so we can print Turkish chars (ı, ç, ş, ğ, ü)
if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def safe(s: str) -> str:
    """Return s with characters the stdout can't render replaced by '?'."""
    if s is None:
        return ""
    try:
        s.encode(sys.stdout.encoding or "utf-8")
        return s
    except UnicodeEncodeError:
        return s.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8")


def banner(msg: str) -> None:
    print(f"\n{'=' * 60}\n {msg}\n{'=' * 60}")


def main() -> int:
    print("TulparAI -- NVIDIA LLM smoke test")
    print(f"  endpoint:  {settings.nvidia_base_url}")
    print(f"  fast:      {settings.nemotron_fast}")
    print(f"  reasoner:  {settings.nemotron_reasoner}")
    print(f"  embed:     {settings.embedding_model}")
    key_view = settings.nvidia_api_key[:10] + "..." if settings.nvidia_api_key else "MISSING"
    print(f"  api key:   set ({key_view})")

    # --- 1. List models ---------------------------------------------------
    banner("STEP 1 -- list available models")
    models = list_available_models()
    if models and models[0].startswith("<error"):
        print(models[0])
        return 1
    print(f"  {len(models)} models accessible.")
    configured_ids = {settings.nemotron_fast, settings.nemotron_reasoner, settings.embedding_model}
    missing = configured_ids - set(models)
    if missing:
        print(f"\n  [WARN] Configured but NOT in catalog: {missing}")
        print("  Pick replacements from the catalog and update backend/.env")
    else:
        print("\n  [OK] All 3 configured model IDs exist in the catalog.")

    # --- 2. Call NEMOTRON_FAST in JSON mode -----------------------------
    banner(f"STEP 2 -- JSON mode call to {settings.nemotron_fast}")
    try:
        resp = chat(
            messages=[
                {"role": "system", "content": "Output ONLY this JSON: {\"ok\": true, \"sport\": \"<echo back what sport the user names>\"}"},
                {"role": "user", "content": "I play football."},
            ],
            model=settings.nemotron_fast,
            temperature=0.0,
            response_format={"type": "json_object"},
            max_tokens=400,
        )
        msg = resp.choices[0].message
        content = msg.content
        reasoning = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None)
        print(f"  content:           {safe(content) if content else '<None>'}")
        if reasoning:
            r = reasoning if len(reasoning) < 200 else reasoning[:200] + "..."
            print(f"  reasoning_content: {safe(r)}")
        print(f"  finish_reason:     {resp.choices[0].finish_reason}")

        # Try parsing whichever field contains JSON
        body = content or reasoning or ""
        # Reasoning models sometimes wrap JSON in code fences
        body = body.strip()
        if body.startswith("```"):
            body = body.strip("`").strip()
            if body.startswith("json"):
                body = body[4:].strip()
        try:
            parsed = json.loads(body)
            print(f"  parsed:            {parsed}")
            print("  [OK] Fast/JSON path works.")
        except json.JSONDecodeError:
            print(f"  [WARN] Couldn't parse as JSON. Maybe try a different fast model (e.g. meta/llama-3.1-8b-instruct).")
    except Exception as e:
        print(f"  [FAIL] Fast model failed: {type(e).__name__}: {safe(str(e))}")
        print("     -> likely model ID wrong. Check catalog and update NEMOTRON_FAST in .env.")

    # --- 3. Call NEMOTRON_REASONER in free-form mode --------------------
    banner(f"STEP 3 -- free-form call to {settings.nemotron_reasoner}")
    try:
        resp = chat(
            messages=[
                {"role": "system", "content": "You are a helpful sports nutrition assistant. Reply in Turkish, one sentence."},
                {"role": "user", "content": "Bir futbolcu maçtan 3 saat önce ne yemeli?"},
            ],
            model=settings.nemotron_reasoner,
            temperature=0.3,
            max_tokens=200,
        )
        msg = resp.choices[0].message
        text = msg.content or getattr(msg, "reasoning_content", "") or ""
        print(f"  response ({len(text)} chars): {safe(text)}")
        print(f"  finish_reason:                {resp.choices[0].finish_reason}")
        print("  [OK] Reasoner path works.")
    except Exception as e:
        print(f"  [FAIL] Reasoner model failed: {type(e).__name__}: {safe(str(e))}")
        print("     -> likely model ID wrong. Check catalog and update NEMOTRON_REASONER in .env.")

    # --- 4. Embedding check --------------------------------------------
    banner(f"STEP 4 -- embeddings call to {settings.embedding_model}")
    try:
        from openai import OpenAI
        c = OpenAI(api_key=settings.nvidia_api_key, base_url=settings.nvidia_base_url)
        r = c.embeddings.create(
            model=settings.embedding_model,
            input=["mac oncesi karbonhidrat", "post-match recovery protein"],
            extra_body={"input_type": "query", "truncate": "END"},
        )
        dims = [len(d.embedding) for d in r.data]
        print(f"  got {len(r.data)} embeddings, dims={dims}")
        print("  [OK] Embedding path works.")
    except Exception as e:
        print(f"  [FAIL] Embedding model failed: {type(e).__name__}: {safe(str(e))}")
        print("     -> likely embedding model ID wrong. Update EMBEDDING_MODEL in .env.")

    banner("SMOKE TEST DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
