"""`update_profile` tool — the Reasoner calls this during onboarding (or any
time the athlete shares a new fact) to merge changes into the SQLite profile.

The tool is intentionally permissive: it accepts a partial `fields` dict and
deep-merges it into the existing profile so the Reasoner doesn't have to
re-send fields it isn't changing.
"""
from __future__ import annotations

from typing import Any

from backend.db.repos import AthleteRepo


# Top-level columns the LLM may update directly.  `sport_profile` is a JSON
# dict — we deep-merge instead of replacing so partial updates are non-destructive.
_ALLOWED_FIELDS = {
    "name", "language", "city", "age", "sex", "height_cm", "weight_kg",
    "sport", "training_phase", "weekly_hours", "training_days",
    "primary_goal", "diet_type", "religious_fasting",
    "conditions", "medications", "allergies",
    "injury_history", "current_injuries",
    "sport_profile", "specific_targets",
}


def update_profile(athlete_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    """Merge `fields` into the athlete profile.

    Returns the updated profile (or an error dict if the athlete is unknown).
    Unknown field names are silently dropped — we don't fail the call, we
    just don't honour fields the schema can't store.
    """
    repo = AthleteRepo()
    current = repo.get(athlete_id)
    if not current:
        return {"error": f"athlete '{athlete_id}' not found"}

    accepted: dict[str, Any] = {}
    rejected: list[str] = []

    for key, value in (fields or {}).items():
        if key not in _ALLOWED_FIELDS:
            rejected.append(key)
            continue
        if key == "sport_profile" and isinstance(value, dict):
            # Deep-merge sport_profile so partial updates (e.g. only `position`)
            # don't wipe out other sport-specific fields.
            merged = dict(current.get("sport_profile") or {})
            merged.update(value)
            accepted[key] = merged
        else:
            accepted[key] = value

    if not accepted:
        return {
            "ok": False,
            "message": "No accepted fields in update",
            "rejected": rejected,
        }

    merged_profile = {**current, **accepted}
    repo.upsert(athlete_id, merged_profile)

    return {
        "ok": True,
        "updated_fields": list(accepted.keys()),
        "rejected_fields": rejected,
        "profile": {k: merged_profile.get(k) for k in accepted.keys()},
    }
