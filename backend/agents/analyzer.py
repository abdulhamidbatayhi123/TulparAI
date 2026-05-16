"""Analyzer agent: turns a raw user message into structured intent JSON.

Uses the FAST Nemotron Nano model in JSON mode. Output shape:
  {
    "intent":          "question | greeting | identity | profile | thanks | log",
    "urgency":         "low | normal | high",
    "language":        "tr | en",
    "sport_override":  "football | wrestling | weightlifting | volleyball | null",
    "sub_queries":     ["..."],
    "needs_tools":     bool
  }

On any failure (timeout, malformed JSON, model error) we fall back to a default
"treat as a normal question" structure so the pipeline still moves forward.
"""
from __future__ import annotations

import json
from backend.llm.nvidia_client import chat
from backend.config import settings
from backend.i18n import get_prompts


def _default(language: str, message: str) -> dict:
    return {
        "intent": "question",
        "urgency": "normal",
        "language": language,
        "sport_override": None,
        "sub_queries": [message[:400]],
        "needs_tools": True,
    }


def analyze(user_message: str, language: str = "tr") -> dict:
    if not user_message or not user_message.strip():
        return {**_default(language, ""), "intent": "greeting"}

    prompts = get_prompts(language)
    try:
        resp = chat(
            messages=[
                {"role": "system", "content": prompts.ANALYZER_SYSTEM},
                {"role": "user", "content": user_message},
            ],
            model=settings.nemotron_fast,
            temperature=0.0,
            response_format={"type": "json_object"},
            # The Nano model emits a reasoning chain before the JSON;
            # need enough headroom for both.
            max_tokens=800,
        )
        msg = resp.choices[0].message
        body = (msg.content or "").strip()
        # Strip optional ```json fences (some models wrap output)
        if body.startswith("```"):
            body = body.strip("`").strip()
            if body.startswith("json"):
                body = body[4:].strip()

        if not body:
            return _default(language, user_message)

        data = json.loads(body)

        # Normalise / fill gaps
        return {
            "intent":         data.get("intent", "question"),
            "urgency":        data.get("urgency", "normal"),
            "language":       data.get("language", language),
            "sport_override": data.get("sport_override"),
            "sub_queries":    data.get("sub_queries") or [user_message[:400]],
            "needs_tools":    bool(data.get("needs_tools", True)),
        }
    except Exception:
        return _default(language, user_message)
