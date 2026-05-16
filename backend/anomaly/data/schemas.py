"""
Pydantic schemas for athlete profiles and daily logs.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal
from datetime import date


class AthleteProfile(BaseModel):
    """Static athlete profile — defines what *normal* looks like."""

    athlete_id: str
    name: str
    sport: Literal["football", "wrestling", "weightlifting", "volleyball"]
    age: int = Field(ge=14, le=60)
    weight_kg: float = Field(ge=40, le=200)
    height_cm: float = Field(ge=140, le=220)
    goal: Literal["cut", "maintain", "bulk"]
    target_daily_calories: float
    target_protein_g: float
    target_carbs_g: float
    target_fat_g: float


class DailyLog(BaseModel):
    """One day's worth of athlete behaviour data."""

    athlete_id: str
    log_date: date

    # Nutrition
    calories_eaten: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)

    # Training
    training_duration_min: float = Field(ge=0, le=480)
    training_intensity: float = Field(ge=0, le=10)
    training_type_match: float = Field(ge=0, le=1)  # 1 = matches plan

    # Recovery
    sleep_hours: float = Field(ge=0, le=24)
    hydration_liters: float = Field(ge=0, le=15)

    # Context
    rest_day: bool = False
    meal_timing_score: float = Field(ge=0, le=1, default=0.8)
    day_of_week: int = Field(ge=0, le=6)  # 0 = Monday


class AnomalyResult(BaseModel):
    """Returned by the anomaly detector."""

    athlete_id: str
    log_date: date
    anomaly_score: float = Field(ge=0, le=100)
    is_anomaly: bool
    anomaly_type: str | None = None
    details: dict = Field(default_factory=dict)
    recommendation: str | None = None
