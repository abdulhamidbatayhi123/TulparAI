"""
Synthetic data generator for training the anomaly detection autoencoder.

Generates realistic "normal" athlete behaviour data + controlled anomalies
for testing and validation.
"""

from __future__ import annotations

import json
import math
import random
from datetime import date, timedelta
from typing import Literal

import numpy as np

from backend.anomaly.data.schemas import AthleteProfile, DailyLog

# ────────────────────────────────────────────────────────────────────
# Reference ranges per sport (realistic training norms)
# ────────────────────────────────────────────────────────────────────
SPORT_NORMS = {
    "football": {
        "training_duration_range": (60, 120),
        "training_intensity_range": (5, 8),
        "sleep_range": (7, 9),
        "hydration_range": (2.5, 4.0),
    },
    "wrestling": {
        "training_duration_range": (60, 150),
        "training_intensity_range": (6, 9),
        "sleep_range": (7, 9),
        "hydration_range": (2.0, 3.5),
    },
    "weightlifting": {
        "training_duration_range": (45, 120),
        "training_intensity_range": (7, 10),
        "sleep_range": (7, 9.5),
        "hydration_range": (2.5, 4.0),
    },
    "volleyball": {
        "training_duration_range": (60, 120),
        "training_intensity_range": (4, 7),
        "sleep_range": (7, 9),
        "hydration_range": (2.0, 3.5),
    },
}


def _mifflin_st_jeor(weight_kg: float, height_cm: float, age: int, pal: float) -> float:
    """Mifflin-St Jeor equation (male) * PAL."""
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    return round(bmr * pal)


SPORT_PAL = {
    "football":      1.725,
    "wrestling":     1.9,
    "weightlifting": 1.725,
    "volleyball":    1.6,
}

GOAL_MACROS = {
    "cut":      {"protein_pct": 0.35, "carbs_pct": 0.40, "fat_pct": 0.25},
    "maintain": {"protein_pct": 0.30, "carbs_pct": 0.45, "fat_pct": 0.25},
    "bulk":     {"protein_pct": 0.30, "carbs_pct": 0.50, "fat_pct": 0.20},
}


# ────────────────────────────────────────────────────────────────────
# Profile Generator
# ────────────────────────────────────────────────────────────────────

DEMO_PROFILES = [
    {"name": "Ahmet Yılmaz",   "sport": "football",      "age": 24, "weight_kg": 78,  "height_cm": 181, "goal": "maintain"},
    {"name": "Fatih Kaya",     "sport": "wrestling",      "age": 27, "weight_kg": 85,  "height_cm": 175, "goal": "cut"},
    {"name": "Emre Demir",     "sport": "weightlifting",  "age": 22, "weight_kg": 94,  "height_cm": 178, "goal": "bulk"},
    {"name": "Can Öztürk",     "sport": "volleyball",     "age": 20, "weight_kg": 82,  "height_cm": 192, "goal": "maintain"},
    {"name": "Mert Arslan",    "sport": "football",       "age": 30, "weight_kg": 75,  "height_cm": 176, "goal": "cut"},
    {"name": "Ali Şahin",      "sport": "wrestling",      "age": 25, "weight_kg": 74,  "height_cm": 170, "goal": "maintain"},
    {"name": "Burak Çelik",    "sport": "weightlifting",  "age": 28, "weight_kg": 105, "height_cm": 185, "goal": "bulk"},
    {"name": "Oğuz Koç",       "sport": "volleyball",     "age": 23, "weight_kg": 88,  "height_cm": 196, "goal": "maintain"},
]


def generate_profiles() -> list[AthleteProfile]:
    """Generate 8 demo athlete profiles."""
    profiles = []
    for i, p in enumerate(DEMO_PROFILES):
        pal = SPORT_PAL[p["sport"]]
        tdee = _mifflin_st_jeor(p["weight_kg"], p["height_cm"], p["age"], pal)

        # Adjust for goal
        if p["goal"] == "cut":
            target_cal = tdee - 500
        elif p["goal"] == "bulk":
            target_cal = tdee + 400
        else:
            target_cal = tdee

        macros = GOAL_MACROS[p["goal"]]
        profile = AthleteProfile(
            athlete_id=f"ATH-{i+1:03d}",
            name=p["name"],
            sport=p["sport"],
            age=p["age"],
            weight_kg=p["weight_kg"],
            height_cm=p["height_cm"],
            goal=p["goal"],
            target_daily_calories=target_cal,
            target_protein_g=round(target_cal * macros["protein_pct"] / 4),
            target_carbs_g=round(target_cal * macros["carbs_pct"] / 4),
            target_fat_g=round(target_cal * macros["fat_pct"] / 9),
        )
        profiles.append(profile)
    return profiles


# ────────────────────────────────────────────────────────────────────
# Normal Log Generator
# ────────────────────────────────────────────────────────────────────

def _normal_log(profile: AthleteProfile, log_date: date) -> DailyLog:
    """Generate a single normal-behaviour daily log."""
    norms = SPORT_NORMS[profile.sport]
    dow = log_date.weekday()
    is_rest = dow in (5, 6) and random.random() < 0.6  # ~60% chance rest on weekends

    # Nutrition: small gaussian noise around targets (±10%)
    cal_noise = random.gauss(1.0, 0.06)
    prot_noise = random.gauss(1.0, 0.07)
    carb_noise = random.gauss(1.0, 0.07)
    fat_noise = random.gauss(1.0, 0.08)

    calories = max(800, profile.target_daily_calories * cal_noise)
    protein = max(30, profile.target_protein_g * prot_noise)
    carbs = max(50, profile.target_carbs_g * carb_noise)
    fat = max(15, profile.target_fat_g * fat_noise)

    # Training
    if is_rest:
        duration = random.uniform(0, 20)  # light stretch at most
        intensity = random.uniform(0, 2)
    else:
        lo, hi = norms["training_duration_range"]
        duration = random.uniform(lo, hi)
        lo_i, hi_i = norms["training_intensity_range"]
        intensity = random.uniform(lo_i, hi_i)

    # Recovery
    slo, shi = norms["sleep_range"]
    sleep = random.uniform(slo, shi)
    hlo, hhi = norms["hydration_range"]
    hydration = random.uniform(hlo, hhi)

    return DailyLog(
        athlete_id=profile.athlete_id,
        log_date=log_date,
        calories_eaten=round(calories),
        protein_g=round(protein),
        carbs_g=round(carbs),
        fat_g=round(fat),
        training_duration_min=round(duration, 1),
        training_intensity=round(intensity, 1),
        training_type_match=1.0 if random.random() < 0.9 else 0.5,
        sleep_hours=round(sleep, 1),
        hydration_liters=round(hydration, 1),
        rest_day=is_rest,
        meal_timing_score=round(random.uniform(0.7, 1.0), 2),
        day_of_week=dow,
    )


# ────────────────────────────────────────────────────────────────────
# Anomalous Log Generator
# ────────────────────────────────────────────────────────────────────

ANOMALY_TYPES = [
    "calorie_excess",
    "calorie_deficit",
    "macro_imbalance",
    "overtraining",
    "under_recovery",
    "dehydration",
    "wrong_training",
    "bad_meal_timing",
]


def _anomalous_log(
    profile: AthleteProfile,
    log_date: date,
    anomaly_type: str | None = None,
) -> tuple[DailyLog, str]:
    """Generate an anomalous daily log and return (log, anomaly_type)."""
    # Start from a normal log, then corrupt specific features
    log_dict = _normal_log(profile, log_date).model_dump()

    if anomaly_type is None:
        anomaly_type = random.choice(ANOMALY_TYPES)

    if anomaly_type == "calorie_excess":
        log_dict["calories_eaten"] = round(profile.target_daily_calories * random.uniform(1.5, 2.2))
        log_dict["fat_g"] = round(profile.target_fat_g * random.uniform(1.8, 3.0))

    elif anomaly_type == "calorie_deficit":
        log_dict["calories_eaten"] = round(profile.target_daily_calories * random.uniform(0.3, 0.55))
        log_dict["protein_g"] = round(profile.target_protein_g * random.uniform(0.2, 0.4))

    elif anomaly_type == "macro_imbalance":
        # Swap protein and fat percentages drastically
        log_dict["protein_g"] = round(profile.target_protein_g * random.uniform(0.2, 0.35))
        log_dict["fat_g"] = round(profile.target_fat_g * random.uniform(2.5, 4.0))

    elif anomaly_type == "overtraining":
        log_dict["training_duration_min"] = random.uniform(200, 360)
        log_dict["training_intensity"] = random.uniform(8.5, 10)
        log_dict["rest_day"] = False

    elif anomaly_type == "under_recovery":
        log_dict["sleep_hours"] = random.uniform(2, 4.5)
        log_dict["training_intensity"] = random.uniform(7, 10)

    elif anomaly_type == "dehydration":
        log_dict["hydration_liters"] = random.uniform(0.2, 0.8)

    elif anomaly_type == "wrong_training":
        log_dict["training_type_match"] = 0.0
        log_dict["training_intensity"] = random.uniform(1, 3)
        log_dict["training_duration_min"] = random.uniform(15, 40)

    elif anomaly_type == "bad_meal_timing":
        log_dict["meal_timing_score"] = random.uniform(0, 0.2)

    return DailyLog(**log_dict), anomaly_type


# ────────────────────────────────────────────────────────────────────
# Dataset Builder
# ────────────────────────────────────────────────────────────────────

def generate_dataset(
    days: int = 90,
    anomaly_ratio: float = 0.0,
    seed: int = 42,
) -> tuple[list[AthleteProfile], list[DailyLog], list[dict]]:
    """
    Generate full dataset.

    Args:
        days: number of days of logs per athlete
        anomaly_ratio: fraction of logs that should be anomalous (0.0 for pure training set)
        seed: random seed for reproducibility

    Returns:
        (profiles, logs, labels)
        labels is a list of dicts: {"athlete_id", "log_date", "is_anomaly", "anomaly_type"}
    """
    random.seed(seed)
    np.random.seed(seed)

    profiles = generate_profiles()
    logs: list[DailyLog] = []
    labels: list[dict] = []

    start_date = date(2026, 1, 1)

    for profile in profiles:
        for d in range(days):
            log_date = start_date + timedelta(days=d)
            is_anomaly = random.random() < anomaly_ratio

            if is_anomaly:
                log, a_type = _anomalous_log(profile, log_date)
                labels.append({
                    "athlete_id": profile.athlete_id,
                    "log_date": str(log_date),
                    "is_anomaly": True,
                    "anomaly_type": a_type,
                })
            else:
                log = _normal_log(profile, log_date)
                labels.append({
                    "athlete_id": profile.athlete_id,
                    "log_date": str(log_date),
                    "is_anomaly": False,
                    "anomaly_type": None,
                })

            logs.append(log)

    return profiles, logs, labels


# ────────────────────────────────────────────────────────────────────
# CLI entry point
# ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    profiles, logs, labels = generate_dataset(days=90, anomaly_ratio=0.0)
    print(f"Generated {len(profiles)} profiles, {len(logs)} normal logs")

    # Also generate a test set with anomalies
    _, test_logs, test_labels = generate_dataset(days=30, anomaly_ratio=0.15, seed=99)
    anomaly_count = sum(1 for l in test_labels if l["is_anomaly"])
    print(f"Generated {len(test_logs)} test logs ({anomaly_count} anomalies)")

    # Save profiles
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(out_dir, "sample_profiles.json"), "w", encoding="utf-8") as f:
        json.dump([p.model_dump() for p in profiles], f, indent=2, ensure_ascii=False)
    print(f"Profiles saved to {out_dir}/sample_profiles.json")
