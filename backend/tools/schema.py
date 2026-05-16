"""OpenAI-style tool schemas + Python dispatch table.

The Reasoner is given `TOOL_SCHEMAS` so it can decide which functions to call.
When the LLM returns a tool_call, the orchestrator looks up the function in
`DISPATCH` and runs it with the parsed arguments.
"""
from __future__ import annotations

from typing import Callable, Dict, Any

from backend.tools import kb_search, food_macros, calc_macros, weather, logger, web_search

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_sport_kb",
            "description": (
                "Search the verified, sport-filtered knowledge base for evidence-based "
                "information on training, nutrition, recovery, or injury prevention. "
                "Always call this first for factual questions about the athlete's sport."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sport": {
                        "type": "string",
                        "enum": ["football", "wrestling", "weightlifting", "volleyball"],
                        "description": "The athlete's sport. Get it from their profile."
                    },
                    "query": {
                        "type": "string",
                        "description": "What you want to find out. Be specific."
                    },
                    "language": {
                        "type": "string",
                        "enum": ["tr", "en"],
                        "description": "Filter to this language only (optional)."
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of passages to return (default 5)."
                    },
                },
                "required": ["sport", "query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_food_macros",
            "description": (
                "Look up nutritional macros (kcal, protein, carbs, fat) for a food. "
                "Tries USDA first then Open Food Facts. Use whenever an athlete mentions "
                "a specific food and you need its macros."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "food_name": {"type": "string"},
                    "serving_grams": {"type": "number", "description": "Default 100."},
                },
                "required": ["food_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calc_macros",
            "description": (
                "Compute daily calorie + macronutrient targets for an athlete based on their "
                "profile (height, weight, age, sex, sport, training phase) and a goal. "
                "Use when the athlete asks about daily intake, bulking, cutting, or weight class targets."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "athlete_id": {"type": "string"},
                    "goal": {
                        "type": "string",
                        "enum": ["maintain", "performance", "bulk", "cut", "weight_class", "injury_recovery"],
                    },
                },
                "required": ["athlete_id", "goal"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": (
                "Get current weather for the athlete's city. Use when giving advice about outdoor "
                "training (hydration, intensity, clothing, heat acclimation)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "date": {"type": "string", "description": "Ignored — free tier returns current only."},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_session",
            "description": (
                "Save a log entry (training, meal, weight, or sleep) for the athlete. "
                "Use when the athlete tells you something to record."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "athlete_id": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": ["training", "meal", "weight", "sleep"],
                    },
                    "data": {"type": "object", "description": "Free-form payload appropriate to the type."},
                },
                "required": ["athlete_id", "type", "data"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search_trusted",
            "description": (
                "Search the live web ONLY in a curated whitelist of authoritative sport / medical / "
                "government domains (FIFA, UEFA, IOC, TFF, WHO, BJSM, etc.). Use for recent research, "
                "rule updates, federation announcements that may not be in the static knowledge base."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "language": {"type": "string", "enum": ["tr", "en"]},
                    "max_results": {"type": "integer", "description": "Default 5, max 10."},
                },
                "required": ["query"],
            },
        },
    },
]


# Maps tool name → Python callable. The orchestrator uses this to execute tool_calls.
DISPATCH: Dict[str, Callable[..., Any]] = {
    "search_sport_kb":      kb_search.search,
    "get_food_macros":      food_macros.lookup,
    "calc_macros":          calc_macros.compute,
    "get_weather":          weather.get,
    "log_session":          logger.write,
    "web_search_trusted":   web_search.search,
}


def schema_dispatch_consistent() -> bool:
    """Sanity check used by tests: every schema has a dispatch entry and vice versa."""
    schema_names = {t["function"]["name"] for t in TOOL_SCHEMAS}
    return schema_names == set(DISPATCH.keys())
