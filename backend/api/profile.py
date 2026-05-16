"""Profile CRUD endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend.db.repos import AthleteRepo

router = APIRouter(prefix="/profile")


class ProfileIn(BaseModel):
    athlete_id: str
    name: str
    language: str = "tr"
    city: str | None = None
    age: int | None = None
    sex: str | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    sport: str
    sport_profile: dict = Field(default_factory=dict)
    training_phase: str | None = None
    weekly_hours: int | None = None
    training_days: int | None = None
    conditions: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    injury_history: list[dict] = Field(default_factory=list)
    current_injuries: list[dict] = Field(default_factory=list)
    primary_goal: str | None = None
    specific_targets: dict = Field(default_factory=dict)
    diet_type: str = "omnivore"
    religious_fasting: str | None = None


@router.post("")
def upsert_profile(p: ProfileIn):
    AthleteRepo().upsert(p.athlete_id, p.model_dump())
    return {"ok": True, "athlete_id": p.athlete_id}


@router.get("/{athlete_id}")
def get_profile(athlete_id: str):
    a = AthleteRepo().get(athlete_id)
    if not a:
        raise HTTPException(404, detail=f"Athlete '{athlete_id}' not found")
    return a
