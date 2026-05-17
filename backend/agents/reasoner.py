"""Reasoner agent — the core thinker.

V2 (tool-using): the Reasoner is given the 6 tool schemas and decides which to call.
For each tool call, the orchestrator (via the `on_tool_call` callback) emits an SSE
event so the frontend can display the live ToolCallChip. Loop terminates when the
LLM returns a final answer with no further tool calls (or when MAX_TOOL_ITERATIONS
is exhausted, in which case we force a final completion without tools).
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any

from backend.llm.nvidia_client import chat
from backend.config import settings
from backend.i18n import get_prompts
from backend.tools.schema import TOOL_SCHEMAS, DISPATCH

MAX_TOOL_ITERATIONS = 3   # was 5 — tighter cap = faster demos (3 is enough for most flows)
# Cap each tool result by chars before feeding back into the conversation so we
# don't blow the model's context window.
MAX_TOOL_RESULT_CHARS = 3000   # was 4000 — tighter context = faster generation


def _build_profile_block(profile: dict) -> str:
    sp = profile.get("sport_profile") or {}
    return (
        f"Name: {profile.get('name', '-')}\n"
        f"Sport: {profile.get('sport', '-')} · profile: {sp}\n"
        f"Age {profile.get('age', '-')} · Sex {profile.get('sex', '-')} · "
        f"{profile.get('height_cm', '-')}cm · {profile.get('weight_kg', '-')}kg\n"
        f"Phase: {profile.get('training_phase', '-')} · "
        f"Goal: {profile.get('primary_goal', '-')} · "
        f"Diet: {profile.get('diet_type', '-')}\n"
        f"Conditions: {profile.get('conditions', [])} · "
        f"Allergies: {profile.get('allergies', [])} · "
        f"Medications: {profile.get('medications', [])}"
    )


# Fields that need to be filled before we consider the profile "ready" enough
# to skip onboarding.  We're permissive — if these 5 are set the agent can
# personalise well; everything else is gravy.
_PROFILE_CORE_FIELDS = ("name", "sport", "age", "height_cm", "weight_kg")


def _profile_status(profile: dict, language: str) -> str:
    """Return a one-line directive for the system prompt that tells the LLM
    whether to run onboarding or to act normally."""
    missing: list[str] = []
    for f in _PROFILE_CORE_FIELDS:
        v = profile.get(f)
        if v is None or v == "" or v == "-":
            missing.append(f)
    # sport_profile is a JSON dict — treat empty dict as missing
    sp = profile.get("sport_profile") or {}
    if not sp:
        missing.append("sport_profile")

    if not missing:
        return ("TAMAM — profil dolu, doğrudan hizmete geç."
                if language == "tr"
                else "READY — profile is complete, proceed normally.")

    fields_str = ", ".join(missing)
    if language == "tr":
        return f"EKSİK — şu alanlar eksik: {fields_str}. Adım adım sor, update_profile ile kaydet."
    return f"INCOMPLETE — these fields are missing: {fields_str}. Ask step-by-step and persist via update_profile."


def _build_system_prompt(
    profile: dict,
    athlete_id: str,
    recent_activity: str,
    history_summary: str,
    weather: str,
    date: str,
    language: str,
) -> str:
    prompts = get_prompts(language)
    status = _profile_status(profile, language)

    # Conditional onboarding section — only injected when the profile is missing
    # required fields.  For the common case (complete profile), this saves
    # ~200 tokens per request, which shaves real time off the Reasoner's
    # generation latency on every turn.
    is_incomplete = status.startswith(("EKSİK", "INCOMPLETE"))
    if is_incomplete:
        onboarding_block = "\n" + prompts.REASONER_ONBOARDING_BLOCK + "\n"
    else:
        onboarding_block = ""

    return prompts.REASONER_SYSTEM_TEMPLATE.format(
        athlete_id=athlete_id,
        profile_block=_build_profile_block(profile),
        profile_status=status,
        onboarding_block=onboarding_block,
        activity_block=recent_activity or "(no recent activity)",
        date=date,
        city=profile.get("city", "Istanbul"),
        weather=weather or "(unknown)",
        history_summary=history_summary or "(none)",
    )


def reason(
    user_message: str,
    profile: dict,
    athlete_id: str = "",
    recent_activity: str = "",
    history_summary: str = "",
    weather: str = "",
    date: str = "",
    language: str = "tr",
    on_tool_call: Callable[[str, dict, str, int], None] | None = None,
    on_token: Callable[[str], None] | None = None,  # reserved for future streaming
    image_base64: str | None = None,
) -> tuple[str, list[dict]]:
    """Run the tool-using reasoner loop.

    Returns (answer_text, tool_trace).
    `tool_trace` is the ordered list of {tool, args, result, ms} executed.
    The answer's [T1][T2]... markers correspond to this list (1-indexed).
    """
    sys_prompt = _build_system_prompt(
        profile, athlete_id, recent_activity, history_summary, weather, date, language
    )
    messages: list[dict] = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_message},
    ]
    tool_trace: list[dict] = []

    for iteration in range(MAX_TOOL_ITERATIONS):
        resp = chat(
            messages=messages,
            model=settings.nemotron_reasoner,
            temperature=0.3,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            max_tokens=2000,
        )
        msg = resp.choices[0].message

        # No more tool calls → final answer
        tool_calls = msg.tool_calls or []
        if not tool_calls:
            content = (msg.content or "") or (getattr(msg, "reasoning_content", "") or "")
            # If a streaming sink is set, emit the answer in word-sized chunks
            # so the frontend can render progressively. This isn't *real* token
            # streaming (the model already finished) — but the perceived effect
            # is the same and it lets us reuse the UI's streaming code path
            # without re-issuing an expensive duplicate request.
            if on_token and content:
                # split on whitespace but keep separators
                import re as _re
                words = _re.findall(r"\S+\s*", content)
                for w in words:
                    on_token(w)
            return content, tool_trace

        # Persist the assistant's tool-call message in the conversation so the
        # OpenAI-style flow stays valid for the next turn
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in tool_calls
            ],
        })

        # ---- Pre-process tool calls (parse args, inject image) ----
        parsed_calls: list[tuple[Any, str, dict]] = []  # [(tc, name, args), ...]
        for tc in tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            # IMAGE INJECTION: if the model called analyze_image but used a
            # placeholder/empty value for `image`, swap in the real base64 that
            # was attached to the chat request. The LLM never sees the blob.
            if name == "analyze_image" and image_base64:
                if not args.get("image") or args.get("image") in (
                    "{{attached_image}}", "attached", "user_image", "<image>",
                ):
                    args["image"] = image_base64

            parsed_calls.append((tc, name, args))

        # ---- Execute tool calls (parallel when 2+) ----
        # Each tool is I/O-bound (HTTP to NVIDIA / USDA / Tavily / OpenWeather)
        # so threads beat sequential execution even under the GIL. We preserve
        # the original LLM-emitted order so [T1][T2] markers in the answer
        # still line up with the tool_trace indexes.
        def _exec(name: str, args: dict) -> tuple[Any, int]:
            t0 = time.time()
            try:
                fn = DISPATCH.get(name)
                if fn is None:
                    result: Any = {"error": f"unknown tool: {name}"}
                else:
                    result = fn(**args)
            except TypeError as e:
                result = {"error": f"bad args for {name}: {e}"}
            except Exception as e:
                result = {"error": f"{type(e).__name__}: {e}"}
            return result, int((time.time() - t0) * 1000)

        if len(parsed_calls) >= 2:
            with ThreadPoolExecutor(max_workers=min(8, len(parsed_calls))) as pool:
                futures = [pool.submit(_exec, name, args) for _, name, args in parsed_calls]
                exec_results = [f.result() for f in futures]
        else:
            exec_results = [_exec(name, args) for _, name, args in parsed_calls]

        # ---- Post-process: emit chips, append to trace + messages, in LLM order ----
        for (tc, name, args), (result, ms) in zip(parsed_calls, exec_results):
            # Build a redacted args view (drop huge image base64 strings)
            args_for_trace = dict(args)
            if name == "analyze_image" and len(str(args_for_trace.get("image", ""))) > 200:
                args_for_trace["image"] = "<image bytes redacted>"

            tool_trace.append({"tool": name, "args": args_for_trace, "result": result, "ms": ms})

            if on_tool_call:
                summary = json.dumps(result, ensure_ascii=False, default=str)
                if len(summary) > 200:
                    summary = summary[:200] + "..."
                on_tool_call(name, args_for_trace, summary, ms)

            # Feed the tool result back to the model
            result_text = json.dumps(result, ensure_ascii=False, default=str)
            if len(result_text) > MAX_TOOL_RESULT_CHARS:
                result_text = result_text[:MAX_TOOL_RESULT_CHARS] + " ...[truncated]"
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_text,
            })

    # Loop budget exhausted — force a final answer with tools disabled
    resp = chat(
        messages=messages,
        model=settings.nemotron_reasoner,
        temperature=0.3,
        max_tokens=2000,
    )
    msg = resp.choices[0].message
    content = (msg.content or "") or (getattr(msg, "reasoning_content", "") or "")
    # Also emit chunked tokens for the budget-exhausted path
    if on_token and content:
        import re as _re
        for w in _re.findall(r"\S+\s*", content):
            on_token(w)
    return content, tool_trace
