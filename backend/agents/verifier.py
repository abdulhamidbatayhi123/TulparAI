"""Verifier agent: checks each [Tx] marker in the answer against tool_trace[x-1].result.

Two modes:
  - verify_offline: pure Python, no LLM. Drops sentences with out-of-range [Tx] markers.
    Used as fallback if LLM verifier fails. Also useful in tests.
  - verify_llm: Nemotron Nano JSON call. Used by default in the pipeline.

Returns dict with: verified_answer, removed_claims, verification_score.
"""
from __future__ import annotations

import json
import re
from typing import Any

TX_RE = re.compile(r"\[T(\d+)\]")
# Splits on sentence-ending punctuation followed by whitespace OR end of string
_SENT_BOUND = re.compile(r"(?<=[.!?])\s+")


def verify_offline(answer: str, tool_trace: list[dict]) -> dict:
    """Strip sentences whose [Tx] index is out of trace bounds.

    Doesn't check semantic support — just index validity. Used as fallback or in tests.
    """
    if not answer.strip():
        return {"verified_answer": "", "removed_claims": [], "verification_score": 1.0}

    sentences = _SENT_BOUND.split(answer)
    kept: list[str] = []
    removed: list[str] = []
    n_tools = len(tool_trace)

    for sent in sentences:
        if not sent.strip():
            continue
        markers = [int(m) for m in TX_RE.findall(sent)]
        # Sentence is invalid if any of its markers indexes outside tool_trace
        invalid_marker = any(m < 1 or m > n_tools for m in markers)
        if invalid_marker:
            removed.append(sent.strip())
        else:
            kept.append(sent)

    total = len(sentences)
    score = len(kept) / total if total > 0 else 1.0
    return {
        "verified_answer": " ".join(kept).strip(),
        "removed_claims": removed,
        "verification_score": round(score, 3),
    }


def verify_llm(answer: str, tool_trace: list[dict], language: str = "tr") -> dict:
    """LLM-based verifier. Falls back to verify_offline on any error."""
    try:
        # Lazy import — only required when LLM mode is used (i.e. NVIDIA key present)
        from backend.llm.nvidia_client import chat
        from backend.config import settings
        from backend.i18n import get_prompts

        prompts = get_prompts(language)
        trace_view = "\n".join(
            f"[T{i+1}] tool={t.get('tool', '?')} result={json.dumps(t.get('result', {}), ensure_ascii=False)[:600]}"
            for i, t in enumerate(tool_trace)
        )
        user = f"ANSWER:\n{answer}\n\nTOOL TRACE:\n{trace_view or '(no tool calls)'}"
        resp = chat(
            messages=[
                {"role": "system", "content": prompts.VERIFIER_SYSTEM},
                {"role": "user", "content": user},
            ],
            model=settings.nemotron_fast,
            temperature=0.0,
            response_format={"type": "json_object"},
            max_tokens=1500,
        )
        data: dict[str, Any] = json.loads(resp.choices[0].message.content or "{}")
        if (
            isinstance(data, dict)
            and "verified_answer" in data
            and "verification_score" in data
        ):
            return data
    except Exception:
        pass

    return verify_offline(answer, tool_trace)
