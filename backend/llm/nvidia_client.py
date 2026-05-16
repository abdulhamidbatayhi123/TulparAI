"""OpenAI-compatible wrapper around build.nvidia.com hosted Nemotron / Llama models.

NVIDIA's NIM inference endpoints speak the OpenAI Chat Completions protocol verbatim,
so we just point an OpenAI() client at integrate.api.nvidia.com/v1.
"""
from __future__ import annotations

from openai import OpenAI
from backend.config import settings

# Lazy singleton: one client per process. Created on first call so importing this
# module is cheap (handy for tests that mock chat()).
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.nvidia_api_key:
            raise RuntimeError(
                "NVIDIA_API_KEY not set. Add it to backend/.env "
                "(see backend/.env.example for the template)."
            )
        _client = OpenAI(
            api_key=settings.nvidia_api_key,
            base_url=settings.nvidia_base_url,
        )
    return _client


def chat(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.4,
    response_format: dict | None = None,
    tools: list[dict] | None = None,
    tool_choice: str | dict | None = None,
    stream: bool = False,
    max_tokens: int | None = None,
):
    """Single chat-completions entry point used by every agent.

    `model` defaults to the Reasoner model from settings. Pass `settings.nemotron_fast`
    for the small/JSON-mode agents (Analyzer, Verifier).

    `response_format={"type": "json_object"}` forces JSON output (use for Analyzer + Verifier).
    `tools=[...]` enables function calling (use for tool-using Reasoner).
    """
    client = _get_client()

    kwargs: dict = {
        "model": model or settings.nemotron_reasoner,
        "messages": messages,
        "temperature": temperature,
        "stream": stream,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if response_format is not None:
        kwargs["response_format"] = response_format
    if tools is not None:
        kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice

    return client.chat.completions.create(**kwargs)


def list_available_models() -> list[str]:
    """Diagnostic helper: hits the /models endpoint to confirm which IDs are valid for this account."""
    client = _get_client()
    try:
        result = client.models.list()
        return sorted(m.id for m in result.data)
    except Exception as e:
        return [f"<error listing models: {e}>"]
