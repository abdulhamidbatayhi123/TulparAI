"""log_session tool — writes a training/meal/weight/sleep entry to SQLite.

Closes the loop in the pipeline: the Reasoner can log athlete events that then
flow back into the next turn's RECENT ACTIVITY block.
"""
from __future__ import annotations


def write(athlete_id: str, type: str, data: dict) -> dict:
    """Append a log row. Lazy import so tests can run without DB module loaded."""
    from backend.db.repos import LogRepo

    if type not in ("training", "meal", "weight", "sleep"):
        return {"ok": False, "error": f"invalid log type: {type}"}
    if not isinstance(data, dict):
        return {"ok": False, "error": "data must be an object"}

    log_id = LogRepo().add(athlete_id, type, data)
    return {"ok": True, "log_id": log_id, "type": type, "saved_keys": list(data.keys())}
