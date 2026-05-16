"""Formatter agent: rule-based post-processing on the verified answer.

  - Appends the bilingual safety disclaimer
  - Builds a structured `sources` list from the tool_trace
  - Returns the dict shape that the SSE `done` event sends to the frontend
"""
from __future__ import annotations

from typing import Any
from backend.i18n import get_prompts


def format_response(
    verified_answer: str,
    tool_trace: list[dict],
    language: str = "tr",
) -> dict[str, Any]:
    """Build the final response dict.

    Args:
      verified_answer: text from the Verifier (unsupported claims already stripped)
      tool_trace:      ordered list of {tool, args, result, ms} from the Reasoner loop
      language:        "tr" or "en" — controls safety note language

    Returns:
      { "answer": str, "sources": list[{marker, tool, text, url, source_name}] }
    """
    prompts = get_prompts(language)
    final = verified_answer.strip()
    if not final:
        # Verifier stripped everything → graceful refusal
        if language == "tr":
            final = (
                "Bu soru için doğrulanmış kaynak bulamadım. "
                "Halüsinasyon riski yerine sessiz kalmayı tercih ediyorum. "
                "Lütfen sorunu farklı ifade et veya bilgi tabanına daha fazla kaynak ekleyelim."
            )
        else:
            final = (
                "I couldn't find any verified source for this question. "
                "I'd rather stay silent than risk hallucinating. "
                "Please rephrase, or add more sources to the knowledge base."
            )
    final += prompts.FORMATTER_SAFETY_NOTE

    sources: list[dict] = []
    marker_idx = 0
    for trace_item in tool_trace:
        tool = trace_item.get("tool")
        result = trace_item.get("result")

        if tool == "search_sport_kb" and isinstance(result, list):
            for hit in result[:2]:  # top 2 per call to keep panel readable
                marker_idx += 1
                sources.append({
                    "marker":       f"T{marker_idx}",
                    "tool":         tool,
                    "text":         (hit.get("text", "") or "")[:400],
                    "url":          hit.get("source_url", ""),
                    "source_name":  hit.get("source_name", ""),
                    "page_number":  hit.get("page_number"),
                })

        elif tool == "web_search_trusted" and isinstance(result, dict):
            for hit in (result.get("results") or [])[:2]:
                marker_idx += 1
                sources.append({
                    "marker":       f"T{marker_idx}",
                    "tool":         tool,
                    "text":         (hit.get("snippet", "") or "")[:400],
                    "url":          hit.get("url", ""),
                    "source_name":  hit.get("title", ""),
                })

        elif tool == "get_food_macros" and isinstance(result, dict) and not result.get("error"):
            marker_idx += 1
            sources.append({
                "marker":       f"T{marker_idx}",
                "tool":         tool,
                "text":         (
                    f"{result.get('food', '?')}: "
                    f"{result.get('kcal', 0)} kcal · "
                    f"P {result.get('protein_g', 0)}g / "
                    f"C {result.get('carb_g', 0)}g / "
                    f"F {result.get('fat_g', 0)}g per {result.get('serving_g', 100)}g"
                ),
                "url":          "",
                "source_name":  result.get("source", "Food DB"),
            })

        elif tool == "calc_macros" and isinstance(result, dict) and not result.get("error"):
            marker_idx += 1
            sources.append({
                "marker":       f"T{marker_idx}",
                "tool":         tool,
                "text":         result.get("rationale", ""),
                "url":          "",
                "source_name":  "Macro Calculator (Mifflin-St Jeor)",
            })

        elif tool == "get_weather" and isinstance(result, dict) and not result.get("error"):
            marker_idx += 1
            sources.append({
                "marker":       f"T{marker_idx}",
                "tool":         tool,
                "text":         result.get("summary", ""),
                "url":          "",
                "source_name":  "OpenWeather",
            })

    return {"answer": final, "sources": sources}
