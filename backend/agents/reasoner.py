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
from typing import Callable, Any

from backend.llm.nvidia_client import chat
from backend.config import settings
from backend.i18n import get_prompts
from backend.tools.schema import TOOL_SCHEMAS, DISPATCH

MAX_TOOL_ITERATIONS = 5
# Cap each tool result by chars before feeding back into the conversation so we
# don't blow the model's context window.
MAX_TOOL_RESULT_CHARS = 4000


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


def _build_system_prompt(
    profile: dict,
    recent_activity: str,
    history_summary: str,
    weather: str,
    date: str,
    language: str,
) -> str:
    prompts = get_prompts(language)
    return prompts.REASONER_SYSTEM_TEMPLATE.format(
        profile_block=_build_profile_block(profile),
        activity_block=recent_activity or "(no recent activity)",
        date=date,
        city=profile.get("city", "Istanbul"),
        weather=weather or "(unknown)",
        history_summary=history_summary or "(none)",
    )


def reason(
    user_message: str,
    profile: dict,
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
        profile, recent_activity, history_summary, weather, date, language
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

        # No more tool calls → final answer. If a streaming callback was
        # supplied, RE-ISSUE the request with stream=True so tokens flow to
        # the UI instead of arriving as one batch. This is the
        # "perceived speed" optimisation.
        tool_calls = msg.tool_calls or []
        if not tool_calls:
            if on_token:
                # Re-run, this time streaming (no tools — we know none are needed)
                try:
                    stream_resp = chat(
                        messages=messages,
                        model=settings.nemotron_reasoner,
                        temperature=0.3,
                        max_tokens=2000,
                        stream=True,
                    )
                    parts: list[str] = []
                    for chunk in stream_resp:
                        if not chunk.choices:
                            continue
                        delta = chunk.choices[0].delta
                        token = (getattr(delta, "content", None) or "")
                        if token:
                            parts.append(token)
                            on_token(token)
                    return "".join(parts), tool_trace
                except Exception:
                    # Fall back to the non-streamed answer
                    pass
            content = (msg.content or "") or (getattr(msg, "reasoning_content", "") or "")
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
            ms = int((time.time() - t0) * 1000)

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
    return content, tool_trace
