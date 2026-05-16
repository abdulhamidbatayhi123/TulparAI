"""
TulparAI Anomaly Detection — Configuration
"""

import os

# ──────────────── Model Hyper-parameters ────────────────
INPUT_DIM          = 28          # total features per daily record
ENCODING_DIM       = 8           # bottleneck size
HIDDEN_DIMS        = [64, 32]    # encoder hidden layers (decoder mirrors)
DROPOUT_RATE       = 0.2

# ──────────────── Training ──────────────────────────────
LEARNING_RATE      = 1e-3
BATCH_SIZE         = 32
EPOCHS             = 100
PATIENCE           = 10          # early-stopping patience
VALIDATION_SPLIT   = 0.2

# ──────────────── Anomaly Detection ─────────────────────
ANOMALY_THRESHOLD_PERCENTILE = 95   # reconstruction-error percentile
ANOMALY_SCORE_SCALE          = 100  # map 0-1 → 0-100 for dashboard

# ──────────────── Paths ─────────────────────────────────
BASE_DIR           = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR          = os.path.join(BASE_DIR, "saved_models")
DATA_DIR           = os.path.join(BASE_DIR, "data")

# ──────────────── Sport-specific PAL (Physical Activity Level) ──
SPORT_PAL = {
    "football":      1.725,
    "wrestling":     1.9,
    "weightlifting": 1.725,
    "volleyball":    1.6,
}

# ──────────────── Macro targets (% of calories) ────────
GOAL_MACROS = {
    "cut":      {"protein_pct": 0.35, "carbs_pct": 0.40, "fat_pct": 0.25},
    "maintain": {"protein_pct": 0.30, "carbs_pct": 0.45, "fat_pct": 0.25},
    "bulk":     {"protein_pct": 0.30, "carbs_pct": 0.50, "fat_pct": 0.20},
}

os.makedirs(MODEL_DIR, exist_ok=True)
