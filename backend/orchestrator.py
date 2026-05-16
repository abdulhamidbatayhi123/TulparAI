"""TulparAI orchestrator — drives the 4-agent pipeline as an SSE generator.

Flow (with lazy-execution optimizations):
  0. REGEX FAST-PATH (no LLM)  → greeting/thanks/identity respond in <50ms
  1. ANALYZER     → intent JSON  (Nemotron Nano)
  2. FAST-PATH    → LLM-classified greeting/thanks/identity get canned responses
  3. REASONER     → tool-using loop (Nemotron Super 120B), auto-injects image bytes
  4. VERIFIER     → only fires when [Tx] markers exist (skips empty answers)
  5. FORMATTER    → safety note + sources panel
  6. emit `done` event

Every transition between agents emits an SSE `step` event so the frontend can
animate the agent badges. Tool calls inside the Reasoner loop emit `tool_call`
events for the ToolCallChip UI.
"""
from __future__ import annotations

import json
import re
import threading
import queue
from datetime import date as _date
from typing import Iterator, Any

from backend.agents.analyzer import analyze
from backend.agents.reasoner import reason
from backend.agents.verifier import verify_llm
from backend.agents.formatter import format_response
from backend.db.repos import LogRepo
from backend.tools.weather import get as weather_get
from backend.i18n import get_prompts

# Regex fast-path: matches obvious trivial inputs (greetings, thanks, identity)
# in TR + EN. No LLM call → response in <50ms.
_RE_GREETING = re.compile(
    r"^\s*(merhaba|selam|selamlar|s\.a|hi|hello|hey|hola|good\s*(morning|evening)|merhaba\s+t[uü]lpar)\W{0,5}$",
    re.IGNORECASE,
)
_RE_THANKS = re.compile(
    r"^\s*(te[sş]ekk[uü]rler|te[sş]ekk[uü]r|sa[gğ]ol(un)?|thanks?|thank\s+you|ty)\W{0,5}$",
    re.IGNORECASE,
)
_RE_IDENTITY = re.compile(
    r"^\s*(sen\s+kimsin|kimsin|ne\s+yapabilirsin|who\s+are\s+you|what\s+are\s+you|what\s+can\s+you\s+do)\??\W*$",
    re.IGNORECASE,
)
# Match any [Tx] citation marker — verifier skipped if none present
_RE_TX_MARKER = re.compile(r"\[T\d+\]")


class Orchestrator:
    """Stateful per-request orchestrator. Build one per request."""

    def run(
        self,
        user_message: str,
        athlete_id: str,
        profile: dict,
        history: list[dict] | None = None,
        image_base64: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yields a stream of SSE-shaped dicts. Caller wraps each as `data: <json>\\n\\n`.

        If `image_base64` is provided, it's auto-injected into any
        `analyze_image` tool call's `image` arg by the Reasoner — the LLM
        doesn't need to carry the base64 blob itself.
        """
        language = profile.get("language", "tr")
        prompts = get_prompts(language)

        # ----- 0. REGEX FAST-PATH (no LLM, <50ms) -------------------------
        # Skip only when no image attached — otherwise we always want vision.
        if not image_base64:
            stripped = (user_message or "").strip()
            if _RE_GREETING.match(stripped):
                yield {"type": "done", "answer": prompts.FAST_PATH["greeting"],
                       "sources": [], "trace": [], "removed_claims": [], "verification_score": 1.0}
                return
            if _RE_THANKS.match(stripped):
                yield {"type": "done", "answer": prompts.FAST_PATH["thanks"],
                       "sources": [], "trace": [], "removed_claims": [], "verification_score": 1.0}
                return
            if _RE_IDENTITY.match(stripped):
                yield {"type": "done", "answer": prompts.FAST_PATH["identity"],
                       "sources": [], "trace": [], "removed_claims": [], "verification_score": 1.0}
                return

        # ----- 1. Analyzer ------------------------------------------------
        yield {"type": "step", "step": 1, "name": "Analyzing"}
        a = analyze(user_message, language=language)
        if a.get("language") in ("tr", "en"):
            language = a["language"]
            prompts = get_prompts(language)

        # ----- 2. LLM Fast-path (intent-classified greetings) -------------
        intent = a.get("intent")
        if intent in prompts.FAST_PATH and not image_base64:
            yield {
                "type": "done",
                "answer": prompts.FAST_PATH[intent],
                "sources": [],
                "trace": [],
                "removed_claims": [],
                "verification_score": 1.0,
            }
            return

        # ----- 3. Build dynamic context for the Reasoner -----------------
        sport = a.get("sport_override") or profile.get("sport", "football")
        # Override the athlete's sport temporarily if the analyzer flagged one
        profile_for_reasoner = {**profile, "sport": sport}

        recent_logs = LogRepo().recent(athlete_id, hours=48)
        recent_activity = "\n".join(
            f"- {log['type']} @ {log['timestamp'][:16]} :: "
            f"{json.dumps(log['data'], ensure_ascii=False)[:120]}"
            for log in recent_logs[:5]
        )

        # Don't crash if no weather key / city
        weather_data = weather_get(profile.get("city") or "Istanbul")
        weather_str = weather_data.get("summary") or "(unavailable)"

        history_summary = " | ".join(
            f"{m['role']}: {m['content'][:80]}" for m in (history or [])[-6:]
        )

        # ----- 4. Reasoner (tool-using loop) ------------------------------
        yield {"type": "step", "step": 2, "name": "Reasoning + using tools"}

        # If user attached an image, nudge the Reasoner to call analyze_image first
        message_with_image_hint = user_message
        if image_base64:
            message_with_image_hint = (
                f"{user_message}\n\n"
                f"[Bir görsel ekledim — lütfen analiz et]"
                if language == "tr"
                else f"{user_message}\n\n[I attached an image — please analyze it]"
            )

        # Run reason() on a worker thread, pump tool_call + token events
        # through a thread-safe queue so they reach the SSE consumer in
        # real time (not buffered until the function returns).
        q: queue.Queue = queue.Queue()
        SENTINEL = object()
        result_holder: dict = {}

        def on_tool_call(name: str, args: dict, summary: str, ms: int) -> None:
            q.put({"type": "tool_call", "tool": name, "args": args, "summary": summary, "ms": ms})

        def on_token(token: str) -> None:
            q.put({"type": "token", "content": token})

        def worker():
            try:
                answer, trace = reason(
                    user_message=message_with_image_hint,
                    profile=profile_for_reasoner,
                    athlete_id=athlete_id,
                    recent_activity=recent_activity,
                    history_summary=history_summary,
                    weather=weather_str,
                    date=_date.today().isoformat(),
                    language=language,
                    on_tool_call=on_tool_call,
                    on_token=on_token,
                    image_base64=image_base64,
                )
                result_holder["answer"] = answer
                result_holder["trace"] = trace
            except Exception as e:
                result_holder["error"] = f"{type(e).__name__}: {e}"
            finally:
                q.put(SENTINEL)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

        # Pump events until reason() finishes
        while True:
            ev = q.get()
            if ev is SENTINEL:
                break
            yield ev

        t.join(timeout=2)

        if "error" in result_holder:
            yield {"type": "error", "message": result_holder["error"]}
            return

        answer = result_holder.get("answer", "")
        tool_trace = result_holder.get("trace", [])

        # ----- 5. Verifier ------------------------------------------------
        # Optimization: skip the LLM verifier when the answer has no [Tx] markers
        # AND no tool was called (nothing to verify against). Saves ~3s.
        needs_verify = bool(_RE_TX_MARKER.search(answer)) or bool(tool_trace)
        if needs_verify:
            yield {"type": "step", "step": 3, "name": "Verifying"}
            verified = verify_llm(answer, tool_trace, language=language)
        else:
            verified = {
                "verified_answer": answer,
                "removed_claims": [],
                "verification_score": 1.0,
            }

        # ----- 6. Formatter -----------------------------------------------
        yield {"type": "step", "step": 4, "name": "Formatting"}
        formatted = format_response(
            verified.get("verified_answer", answer),
            tool_trace,
            language=language,
        )

        # ----- 7. Done ----------------------------------------------------
        yield {
            "type": "done",
            "answer": formatted["answer"],
            "sources": formatted["sources"],
            "trace": [
                {"tool": t["tool"], "args": t["args"], "ms": t["ms"]}
                for t in tool_trace
            ],
            "removed_claims": verified.get("removed_claims", []),
            "verification_score": float(verified.get("verification_score", 1.0)),
        }
