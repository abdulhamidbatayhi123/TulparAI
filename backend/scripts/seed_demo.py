"""Seed 4 demo athletes for the 60-sec personalization demo.

Each athlete is from a different sport with a distinct sport_profile so the
'same question, four different answers' demo flow lights up the differentiator.

Run:
    cd backend
    ./.venv/Scripts/python.exe -m backend.scripts.seed_demo
"""
from __future__ import annotations

from backend.db.connection import init_db
from backend.db.repos import AthleteRepo

DEMO_ATHLETES = [
    {
        "athlete_id": "ahmet",
        "name": "Ahmet Yılmaz",
        "language": "tr",
        "city": "Istanbul",
        "age": 24, "sex": "male", "height_cm": 178, "weight_kg": 78,
        "sport": "football",
        "sport_profile": {
            "position": "striker",
            "level": "professional",
            "league": "Süper Lig",
        },
        "training_phase": "competition",
        "weekly_hours": 18, "training_days": 6,
        "conditions": [], "medications": [], "allergies": [],
        "injury_history": [], "current_injuries": [],
        "primary_goal": "performance",
        "specific_targets": {},
        "diet_type": "omnivore",
    },
    {
        "athlete_id": "ayse",
        "name": "Ayşe Demir",
        "language": "tr",
        "city": "Ankara",
        "age": 22, "sex": "female", "height_cm": 188, "weight_kg": 72,
        "sport": "volleyball",
        "sport_profile": {
            "position": "middle_blocker",
            "spike_reach_cm": 305,
        },
        "training_phase": "competition",
        "weekly_hours": 20, "training_days": 6,
        "conditions": [], "medications": [], "allergies": [],
        "injury_history": [
            {"type": "ankle_sprain", "side": "right", "date": "2025-09-10", "status": "recovered"}
        ],
        "current_injuries": [],
        "primary_goal": "performance",
        "specific_targets": {},
        "diet_type": "omnivore",
    },
    {
        "athlete_id": "mehmet",
        "name": "Mehmet Akın",
        "language": "tr",
        "city": "Konya",
        "age": 26, "sex": "male", "height_cm": 175, "weight_kg": 76,
        "sport": "wrestling",
        "sport_profile": {
            "weight_class": "74kg",
            "style": "freestyle",
        },
        "training_phase": "competition",
        "weekly_hours": 22, "training_days": 6,
        "conditions": [], "medications": [], "allergies": [],
        "injury_history": [],
        "current_injuries": [],
        "primary_goal": "weight_class",
        "specific_targets": {"cut_kg": 2, "days_to_weighin": 4},
        "diet_type": "omnivore",
    },
    {
        "athlete_id": "naim",
        "name": "Naim Süleyman",
        "language": "tr",
        "city": "Izmir",
        "age": 28, "sex": "male", "height_cm": 168, "weight_kg": 88,
        "sport": "weightlifting",
        "sport_profile": {
            "weight_class": "89kg",
            "current_lifts": {"snatch": 145, "clean_jerk": 180},
        },
        "training_phase": "preseason",
        "weekly_hours": 16, "training_days": 5,
        "conditions": [], "medications": [], "allergies": [],
        "injury_history": [
            {"type": "lower_back_strain", "date": "2024-11-02", "status": "recovered"}
        ],
        "current_injuries": [],
        "primary_goal": "performance",
        "specific_targets": {"target_snatch": 150, "target_cj": 188},
        "diet_type": "omnivore",
    },
]


def main() -> None:
    init_db()
    repo = AthleteRepo()
    for athlete in DEMO_ATHLETES:
        repo.upsert(athlete["athlete_id"], athlete)
        sport_info = athlete["sport"]
        sp = athlete.get("sport_profile") or {}
        detail = sp.get("position") or sp.get("weight_class") or ""
        print(f"  seeded: {athlete['athlete_id']:8s} - {athlete['name']:20s} ({sport_info} / {detail})")
    print(f"\n[seed_demo] {len(DEMO_ATHLETES)} demo athletes ready.")


if __name__ == "__main__":
    main()
