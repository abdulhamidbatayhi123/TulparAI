"""
Anomaly detector — inference-time module.

Uses the trained autoencoder to score new daily logs and determine
what type of anomaly was detected.
"""

from __future__ import annotations

import os
from datetime import date

import numpy as np
import torch

from backend.anomaly.data.schemas import AthleteProfile, DailyLog, AnomalyResult
from backend.anomaly.features.pipeline import extract_features, FeatureScaler, FEATURE_NAMES
from backend.anomaly.model.autoencoder import Autoencoder
import backend.anomaly.config as config


class AnomalyDetector:
    """
    End-to-end anomaly detector.

    Usage:
        detector = AnomalyDetector.load("saved_models/")
        result = detector.check(profile, daily_log)
        # result.is_anomaly, result.anomaly_score, result.anomaly_type
    """

    def __init__(
        self,
        model: Autoencoder,
        scaler: FeatureScaler,
        threshold: float,
        device: torch.device | None = None,
    ):
        self.model = model
        self.scaler = scaler
        self.threshold = threshold
        self.device = device or torch.device("cpu")
        self.model.to(self.device)
        self.model.eval()

    # ────────────────────────────────────────────────────
    # Core anomaly check
    # ────────────────────────────────────────────────────

    def check(self, profile: AthleteProfile, log: DailyLog) -> AnomalyResult:
        """Score a single daily log against the athlete's profile."""
        # Extract and scale features
        raw_vec = extract_features(profile, log)
        scaled_vec = self.scaler.transform(raw_vec.reshape(1, -1))

        # Compute reconstruction error
        x = torch.tensor(scaled_vec, dtype=torch.float32).to(self.device)
        with torch.no_grad():
            x_hat = self.model(x)
            per_feature_error = (x - x_hat).cpu().numpy().flatten() ** 2
            mse = float(per_feature_error.mean())

        # Map to 0-100 score
        anomaly_score = min(100.0, (mse / self.threshold) * 50.0)
        is_anomaly = mse > self.threshold

        # Determine anomaly type from per-feature errors
        anomaly_type = None
        details = {}
        if is_anomaly:
            anomaly_type, details = self._classify_anomaly(per_feature_error, profile, log)

        recommendation = self._generate_recommendation(anomaly_type, details, profile) if is_anomaly else None

        return AnomalyResult(
            athlete_id=profile.athlete_id,
            log_date=log.log_date,
            anomaly_score=round(anomaly_score, 1),
            is_anomaly=is_anomaly,
            anomaly_type=anomaly_type,
            details=details,
            recommendation=recommendation,
        )

    def check_batch(
        self, profile: AthleteProfile, logs: list[DailyLog]
    ) -> list[AnomalyResult]:
        """Score multiple logs for the same athlete."""
        return [self.check(profile, log) for log in logs]

    # ────────────────────────────────────────────────────
    # Anomaly classification via per-feature error
    # ────────────────────────────────────────────────────

    @staticmethod
    def _classify_anomaly(
        per_feature_error: np.ndarray,
        profile: AthleteProfile,
        log: DailyLog,
    ) -> tuple[str, dict]:
        """
        Determine the type of anomaly based on which features have the
        highest reconstruction error.
        """
        # Map feature groups to indices
        feature_groups = {
            "calorie":    [FEATURE_NAMES.index("cal_deviation_pct"), FEATURE_NAMES.index("calories_eaten")],
            "protein":    [FEATURE_NAMES.index("protein_deviation_pct"), FEATURE_NAMES.index("protein_g")],
            "carbs":      [FEATURE_NAMES.index("carbs_deviation_pct"), FEATURE_NAMES.index("carbs_g")],
            "fat":        [FEATURE_NAMES.index("fat_deviation_pct"), FEATURE_NAMES.index("fat_g")],
            "training":   [
                FEATURE_NAMES.index("training_duration_min"),
                FEATURE_NAMES.index("training_intensity"),
                FEATURE_NAMES.index("training_type_match"),
            ],
            "sleep":      [FEATURE_NAMES.index("sleep_hours")],
            "hydration":  [FEATURE_NAMES.index("hydration_liters")],
            "meal_timing":[FEATURE_NAMES.index("meal_timing_score")],
        }

        group_errors = {}
        for group, indices in feature_groups.items():
            group_errors[group] = float(np.mean(per_feature_error[indices]))

        # Find the group with highest error
        worst_group = max(group_errors, key=group_errors.get)

        # Detailed classification
        details = {"group_errors": {k: round(v, 4) for k, v in group_errors.items()}}

        cal_dev = (log.calories_eaten - profile.target_daily_calories) / profile.target_daily_calories

        if worst_group == "calorie":
            if cal_dev > 0.3:
                anomaly_type = "calorie_excess"
                details["actual_cal"] = log.calories_eaten
                details["target_cal"] = profile.target_daily_calories
                details["deviation_pct"] = round(cal_dev * 100, 1)
            elif cal_dev < -0.3:
                anomaly_type = "calorie_deficit"
                details["actual_cal"] = log.calories_eaten
                details["target_cal"] = profile.target_daily_calories
                details["deviation_pct"] = round(cal_dev * 100, 1)
            else:
                anomaly_type = "nutrition_irregular"

        elif worst_group in ("protein", "carbs", "fat"):
            anomaly_type = "macro_imbalance"
            details["protein_g"] = log.protein_g
            details["carbs_g"] = log.carbs_g
            details["fat_g"] = log.fat_g

        elif worst_group == "training":
            if log.training_duration_min > 180:
                anomaly_type = "overtraining"
            elif log.training_type_match < 0.3:
                anomaly_type = "wrong_training"
            else:
                anomaly_type = "training_irregular"
            details["duration_min"] = log.training_duration_min
            details["intensity"] = log.training_intensity

        elif worst_group == "sleep":
            anomaly_type = "under_recovery"
            details["sleep_hours"] = log.sleep_hours

        elif worst_group == "hydration":
            anomaly_type = "dehydration"
            details["hydration_liters"] = log.hydration_liters

        elif worst_group == "meal_timing":
            anomaly_type = "bad_meal_timing"
            details["meal_timing_score"] = log.meal_timing_score

        else:
            anomaly_type = "unknown"

        return anomaly_type, details

    # ────────────────────────────────────────────────────
    # Recommendation generator
    # ────────────────────────────────────────────────────

    @staticmethod
    def _generate_recommendation(
        anomaly_type: str | None,
        details: dict,
        profile: AthleteProfile,
    ) -> str:
        """Generate a human-readable recommendation based on anomaly type."""
        recs = {
            "calorie_excess": (
                f"You consumed {details.get('deviation_pct', '?')}% more calories than your "
                f"{profile.goal} target of {profile.target_daily_calories:.0f} kcal. "
                f"Consider reducing portion sizes or swapping high-calorie foods."
            ),
            "calorie_deficit": (
                f"You ate {abs(details.get('deviation_pct', 0))}% fewer calories than needed. "
                f"For your {profile.sport} training, under-fueling risks muscle loss and fatigue. "
                f"Add a protein-rich snack."
            ),
            "macro_imbalance": (
                f"Your macro split is off balance for a {profile.goal} goal. "
                f"Check your protein ({details.get('protein_g', '?')}g) and fat "
                f"({details.get('fat_g', '?')}g) intake."
            ),
            "overtraining": (
                f"Training for {details.get('duration_min', '?')} minutes at high intensity "
                f"risks overtraining. Schedule a recovery day."
            ),
            "wrong_training": (
                f"Today's training didn't match your {profile.sport} plan. "
                f"Stick to your sport-specific programme for optimal results."
            ),
            "training_irregular": (
                "Your training pattern was unusual today. Review your workout plan."
            ),
            "under_recovery": (
                f"Only {details.get('sleep_hours', '?')} hours of sleep. "
                f"Athletes in {profile.sport} need 7-9 hours for recovery. "
                f"Prioritize sleep tonight."
            ),
            "dehydration": (
                f"Only {details.get('hydration_liters', '?')}L of water today. "
                f"Aim for at least 2.5L, especially on training days."
            ),
            "bad_meal_timing": (
                "Your meals weren't timed well around training. "
                "Eat a balanced meal 2-3 hours before and a protein-rich snack within "
                "30 minutes after training."
            ),
            "nutrition_irregular": (
                "Your nutrition pattern was unusual today. Review your meal plan."
            ),
        }
        return recs.get(anomaly_type, "Unusual behaviour detected. Please review your daily plan.")

    # ────────────────────────────────────────────────────
    # Persistence
    # ────────────────────────────────────────────────────

    def save(self, directory: str) -> None:
        """Save model weights + scaler + threshold."""
        os.makedirs(directory, exist_ok=True)
        torch.save(self.model.state_dict(), os.path.join(directory, "autoencoder_best.pt"))
        np.save(os.path.join(directory, "scaler_mean.npy"), self.scaler.scaler.mean_)
        np.save(os.path.join(directory, "scaler_scale.npy"), self.scaler.scaler.scale_)
        np.save(os.path.join(directory, "threshold.npy"), np.array([self.threshold]))

    @classmethod
    def load(cls, directory: str) -> "AnomalyDetector":
        """Load a trained detector from disk."""
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Load model
        model = Autoencoder(
            input_dim=config.INPUT_DIM,
            encoding_dim=config.ENCODING_DIM,
            hidden_dims=config.HIDDEN_DIMS,
            dropout=0.0,  # no dropout at inference
        )
        model.load_state_dict(
            torch.load(os.path.join(directory, "autoencoder_best.pt"), weights_only=True, map_location=device)
        )

        # Load scaler
        scaler = FeatureScaler()
        scaler.scaler.mean_ = np.load(os.path.join(directory, "scaler_mean.npy"))
        scaler.scaler.scale_ = np.load(os.path.join(directory, "scaler_scale.npy"))
        scaler.scaler.var_ = scaler.scaler.scale_ ** 2
        scaler.scaler.n_features_in_ = len(scaler.scaler.mean_)
        scaler.is_fitted = True

        # Load threshold
        threshold = float(np.load(os.path.join(directory, "threshold.npy"))[0])

        return cls(model=model, scaler=scaler, threshold=threshold, device=device)
