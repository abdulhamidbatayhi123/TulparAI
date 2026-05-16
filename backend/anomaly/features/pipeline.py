"""
Feature engineering pipeline.

Converts (AthleteProfile, DailyLog) pairs into normalised feature vectors
that the autoencoder can consume.
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np
from sklearn.preprocessing import StandardScaler

from backend.anomaly.data.schemas import AthleteProfile, DailyLog


# ────────────────────────────────────────────────────────
# Feature names (order matters — must match vector index)
# ────────────────────────────────────────────────────────
SPORT_NAMES = ["football", "wrestling", "weightlifting", "volleyball"]
GOAL_NAMES  = ["cut", "maintain", "bulk"]

FEATURE_NAMES = (
    # Profile — one-hot sport (4)
    [f"sport_{s}" for s in SPORT_NAMES]
    # Profile — one-hot goal (3)
    + [f"goal_{g}" for g in GOAL_NAMES]
    # Profile — numeric (4)
    + ["weight_kg", "height_cm", "age", "target_daily_calories"]
    # Daily — nutrition deviations (4)
    + ["cal_deviation_pct", "protein_deviation_pct", "carbs_deviation_pct", "fat_deviation_pct"]
    # Daily — absolute nutrition (4)
    + ["calories_eaten", "protein_g", "carbs_g", "fat_g"]
    # Daily — training (3)
    + ["training_duration_min", "training_intensity", "training_type_match"]
    # Daily — recovery (2)
    + ["sleep_hours", "hydration_liters"]
    # Daily — context (4)
    + ["rest_day", "meal_timing_score", "day_sin", "day_cos"]
)

NUM_FEATURES = len(FEATURE_NAMES)  # should be 28


def _deviation_pct(actual: float, target: float) -> float:
    """Calculate percentage deviation: (actual - target) / target."""
    if target == 0:
        return 0.0
    return (actual - target) / target


def extract_features(profile: AthleteProfile, log: DailyLog) -> np.ndarray:
    """
    Convert one (profile, log) pair into a raw feature vector.

    Returns: np.ndarray of shape (NUM_FEATURES,)
    """
    vec = []

    # Sport one-hot
    for s in SPORT_NAMES:
        vec.append(1.0 if profile.sport == s else 0.0)

    # Goal one-hot
    for g in GOAL_NAMES:
        vec.append(1.0 if profile.goal == g else 0.0)

    # Profile numeric
    vec.append(profile.weight_kg)
    vec.append(profile.height_cm)
    vec.append(float(profile.age))
    vec.append(profile.target_daily_calories)

    # Nutrition deviations
    vec.append(_deviation_pct(log.calories_eaten, profile.target_daily_calories))
    vec.append(_deviation_pct(log.protein_g, profile.target_protein_g))
    vec.append(_deviation_pct(log.carbs_g, profile.target_carbs_g))
    vec.append(_deviation_pct(log.fat_g, profile.target_fat_g))

    # Absolute nutrition
    vec.append(log.calories_eaten)
    vec.append(log.protein_g)
    vec.append(log.carbs_g)
    vec.append(log.fat_g)

    # Training
    vec.append(log.training_duration_min)
    vec.append(log.training_intensity)
    vec.append(log.training_type_match)

    # Recovery
    vec.append(log.sleep_hours)
    vec.append(log.hydration_liters)

    # Context
    vec.append(1.0 if log.rest_day else 0.0)
    vec.append(log.meal_timing_score)

    # Cyclical day-of-week
    vec.append(math.sin(2 * math.pi * log.day_of_week / 7))
    vec.append(math.cos(2 * math.pi * log.day_of_week / 7))

    return np.array(vec, dtype=np.float32)


def build_feature_matrix(
    profiles: list[AthleteProfile],
    logs: list[DailyLog],
) -> np.ndarray:
    """
    Build a (N, NUM_FEATURES) matrix from paired profiles and logs.

    Each log must have a matching profile (by athlete_id).
    """
    profile_map = {p.athlete_id: p for p in profiles}
    rows = []
    for log in logs:
        profile = profile_map[log.athlete_id]
        rows.append(extract_features(profile, log))
    return np.vstack(rows)


class FeatureScaler:
    """Wraps sklearn StandardScaler with save/load and feature-name awareness."""

    def __init__(self):
        self.scaler = StandardScaler()
        self.is_fitted = False

    def fit(self, X: np.ndarray) -> "FeatureScaler":
        self.scaler.fit(X)
        self.is_fitted = True
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Scaler not fitted yet")
        return self.scaler.transform(X).astype(np.float32)

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        self.fit(X)
        return self.transform(X)

    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        return self.scaler.inverse_transform(X)
