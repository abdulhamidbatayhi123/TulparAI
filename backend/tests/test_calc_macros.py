"""Tests for the macro calculator (stateless variant — no DB)."""
from backend.tools.calc_macros import _compute_for_profile, mifflin_st_jeor_bmr


def test_mifflin_male():
    # Mifflin-St Jeor for 24M, 178cm, 78kg:  10*78 + 6.25*178 - 5*24 + 5 = 1777.5
    bmr = mifflin_st_jeor_bmr("male", 78, 178, 24)
    assert round(bmr) == 1778


def test_mifflin_female():
    # Mifflin-St Jeor for 22F, 188cm, 72kg: 10*72 + 6.25*188 - 5*22 - 161 = 1624
    bmr = mifflin_st_jeor_bmr("female", 72, 188, 22)
    assert round(bmr) == 1624


def test_football_striker_competition_performance():
    profile = {
        "athlete_id": "ahmet", "sex": "male", "weight_kg": 78, "height_cm": 178, "age": 24,
        "sport": "football", "training_phase": "competition",
    }
    r = _compute_for_profile(profile, goal="performance")
    # BMR ~1778 × PAL 1.85 × goal 1.05 ≈ 3454
    assert 3300 < r["tdee_kcal"] < 3600
    # Protein 78kg × 1.7 = 133g
    assert r["protein_g"] == 133
    # Rationale mentions key values
    assert "Mifflin" in r["rationale"]
    assert "football/competition" in r["rationale"]


def test_wrestler_cut_goal():
    profile = {
        "athlete_id": "mehmet", "sex": "male", "weight_kg": 76, "height_cm": 175, "age": 26,
        "sport": "wrestling", "training_phase": "competition",
    }
    r = _compute_for_profile(profile, goal="cut")
    # Wrestling has higher protein (2.0 g/kg)
    assert r["protein_g"] == round(2.0 * 76)  # 152
    # Cut goal multiplier 0.85 lowers TDEE
    maintain = _compute_for_profile(profile, goal="maintain")
    assert r["tdee_kcal"] < maintain["tdee_kcal"]


def test_fat_floor_protects_low_fat():
    # Extreme cut shouldn't drop fat below 0.6 g/kg
    profile = {
        "athlete_id": "x", "sex": "male", "weight_kg": 80, "height_cm": 180, "age": 25,
        "sport": "wrestling", "training_phase": "competition",
    }
    r = _compute_for_profile(profile, goal="cut")
    assert r["fat_g"] >= round(0.6 * 80)


def test_missing_athlete_returns_error_via_compute():
    # `compute()` (the tool entry point) needs DB; here we just test the stateless variant
    profile = {}  # empty
    r = _compute_for_profile(profile, goal="maintain")
    # Should not crash, should use defaults
    assert r["tdee_kcal"] > 0
