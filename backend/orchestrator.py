"""TulparAI orchestrator — drives the 4-agent pipeline as an SSE generator.

Flow:
  1. ANALYZER    → intent JSON  (Nemotron Nano)
  2. FAST-PATH   → greeting/thanks/identity get canned responses (no LLM call)
  3. REASONER    → tool-using loop (Nemotron Super 120B)
  4. VERIFIER    → strip unsupported [Tx] claims (Nemotron Nano JSON)
  5. FORMATTER   → safety note + sources panel
  6. emit `done` event

Every transition between agents emits an SSE `step` event so the frontend can
animate the agent badges. Tool calls inside the Reasoner loop emit `tool_call`
events for the ToolCallChip UI.
"""
from __future__ import annotations

import json
from datetime import date as _date
from typing import Iterator, Any

from backend.agents.analyzer import analyze
from backend.agents.reasoner import reason
from backend.agents.verifier import verify_llm
from backend.agents.formatter import format_response
from backend.db.repos import LogRepo
from backend.tools.weather import get as weather_get
from backend.i18n import get_prompts


class Orchestrator:
    """Stateful per-request orchestrator. Build one per request."""

    def run(
        self,
        user_message: str,
        athlete_id: str,
        profile: dict,
        history: list[dict] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yields a stream of SSE-shaped dicts. Caller wraps each as `data: <json>\\n\\n`."""
        language = profile.get("language", "tr")
        prompts = get_prompts(language)

        # ----- 1. Analyzer ------------------------------------------------
        yield {"type": "step", "step": 1, "name": "Analyzing"}
        a = analyze(user_message, language=language)
        if a.get("language") in ("tr", "en"):
            language = a["language"]
            prompts = get_prompts(language)

        # ----- 2. Fast-path -----------------------------------------------
        intent = a.get("intent")
        if intent in prompts.FAST_PATH:
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

        # Buffer tool_call events so we can yield them in order
        captured_calls: list[dict] = []

        def on_tool_call(name: str, args: dict, summary: str, ms: int) -> None:
            captured_calls.append({
                "type": "tool_call",
                "tool": name,
                "args": args,
                "summary": summary,
                "ms": ms,
            })

        answer, tool_trace = reason(
            user_message=user_message,
            profile=profile_for_reasoner,
            recent_activity=recent_activity,
            history_summary=history_summary,
            weather=weather_str,
            date=_date.today().isoformat(),
            language=language,
            on_tool_call=on_tool_call,
        )

        # Emit captured tool_call events
        for ev in captured_calls:
            yield ev

        # ----- 5. Verifier ------------------------------------------------
        yield {"type": "step", "step": 3, "name": "Verifying"}
        verified = verify_llm(answer, tool_trace, language=language)

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
