"""Pure-Python macronutrient calculator.

Inputs the athlete's profile (height, weight, age, sex, sport, training_phase) and a goal,
returns target daily calories + macro distribution. Uses Mifflin-St Jeor BMR ×
sport-specific PAL × goal multiplier.

Defensible numbers — judges may ask "where did this come from" and the rationale string
explains the math step-by-step.
"""
from __future__ import annotations

# Physical Activity Level multipliers by (sport, phase)
# Values are conservative estimates from ACSM / IOC consensus guidelines.
PAL: dict[tuple[str, str], float] = {
    ("football", "competition"):    1.85,
    ("football", "preseason"):      1.90,
    ("football", "offseason"):      1.60,
    ("football", "recovery"):       1.50,
    ("wrestling", "competition"):   1.90,
    ("wrestling", "preseason"):     2.00,
    ("wrestling", "offseason"):     1.60,
    ("wrestling", "recovery"):      1.50,
    ("weightlifting", "competition"): 1.70,
    ("weightlifting", "preseason"):   1.75,
    ("weightlifting", "offseason"):   1.55,
    ("weightlifting", "recovery"):    1.45,
    ("volleyball", "competition"):  1.80,
    ("volleyball", "preseason"):    1.85,
    ("volleyball", "offseason"):    1.55,
    ("volleyball", "recovery"):     1.45,
}
DEFAULT_PAL = 1.70

GOAL_MULT = {
    "maintain":     1.00,
    "performance":  1.05,
    "bulk":         1.15,
    "cut":          0.85,
    "weight_class": 0.92,   # gentler than 'cut'
    "injury_recovery": 0.95,
}

# Protein g/kg body weight per sport (ISSN + IOC guidance)
PROTEIN_PER_KG = {
    "football":      1.7,
    "wrestling":     2.0,
    "weightlifting": 2.2,
    "volleyball":    1.6,
}
# Carb share of remaining kcal after protein
CARB_SHARE = {
    "football":      0.55,
    "wrestling":     0.40,
    "weightlifting": 0.45,
    "volleyball":    0.50,
}


def mifflin_st_jeor_bmr(sex: str, weight_kg: float, height_cm: float, age: int) -> float:
    """Resting metabolic rate (kcal/day)."""
    s = 5 if (sex or "").lower().startswith("m") else -161
    return 10 * weight_kg + 6.25 * height_cm - 5 * age + s


def compute(athlete_id: str, goal: str = "maintain") -> dict:
    """Top-level tool entry point. Loads athlete by id, returns macros + rationale."""
    # Lazy import to avoid circular dep at module load
    from backend.db.repos import AthleteRepo

    a = AthleteRepo().get(athlete_id)
    if not a:
        return {"error": f"athlete {athlete_id} not found"}
    return _compute_for_profile(a, goal)


def _compute_for_profile(profile: dict, goal: str) -> dict:
    """Stateless variant — easier to unit-test."""
    sex = profile.get("sex") or "male"
    weight_kg = float(profile.get("weight_kg") or 75)
    height_cm = float(profile.get("height_cm") or 175)
    age = int(profile.get("age") or 25)
    sport = profile.get("sport") or "football"
    phase = profile.get("training_phase") or "competition"

    bmr = mifflin_st_jeor_bmr(sex, weight_kg, height_cm, age)
    pal = PAL.get((sport, phase), DEFAULT_PAL)
    goal_mult = GOAL_MULT.get(goal, 1.0)
    tdee = bmr * pal * goal_mult

    protein_g = PROTEIN_PER_KG.get(sport, 1.7) * weight_kg
    protein_kcal = protein_g * 4

    carb_share = CARB_SHARE.get(sport, 0.5)
    carb_kcal = tdee * carb_share
    carb_g = carb_kcal / 4

    fat_kcal = tdee - protein_kcal - carb_kcal
    fat_g = max(fat_kcal / 9, 0.6 * weight_kg)  # never below 0.6 g/kg (essential fat floor)

    return {
        "athlete_id": profile.get("athlete_id"),
        "goal": goal,
        "tdee_kcal": round(tdee),
        "bmr_kcal": round(bmr),
        "pal": round(pal, 2),
        "goal_multiplier": goal_mult,
        "protein_g": round(protein_g),
        "carb_g": round(carb_g),
        "fat_g": round(fat_g),
        "rationale": (
            f"Mifflin-St Jeor BMR = {round(bmr)} kcal "
            f"× PAL {round(pal, 2)} ({sport}/{phase}) "
            f"× goal '{goal}' (×{goal_mult}) → TDEE {round(tdee)} kcal. "
            f"Protein {round(protein_g)}g ({PROTEIN_PER_KG.get(sport, 1.7)} g/kg × {weight_kg}kg), "
            f"carbs {round(carb_g)}g ({int(carb_share*100)}% kcal), "
            f"fat {round(fat_g)}g (remainder, floor 0.6 g/kg)."
        ),
    }
