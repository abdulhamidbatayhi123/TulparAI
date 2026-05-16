"""Food macros lookup tool.

Primary:  USDA FoodData Central (free, US foods + many international items)
Fallback: Open Food Facts (free, no key — strong on Turkish supermarket products)

Returns kcal + protein/carb/fat in grams for the requested `serving_grams`.
"""
from __future__ import annotations

import httpx
from backend.config import settings

USDA_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
OFF_URL = "https://world.openfoodfacts.org/cgi/search.pl"


def _try_usda(food_name: str, serving_g: float) -> dict | None:
    if not settings.usda_api_key:
        return None
    try:
        with httpx.Client(timeout=10) as c:
            r = c.get(USDA_URL, params={
                "api_key": settings.usda_api_key,
                "query": food_name,
                "pageSize": 1,
                "dataType": "Foundation,SR Legacy,Survey (FNDDS),Branded",
            })
            r.raise_for_status()
            foods = r.json().get("foods", [])
            if not foods:
                return None

            food = foods[0]
            n = {nu["nutrientName"]: nu["value"] for nu in food.get("foodNutrients", [])}
            scale = serving_g / 100.0
            return {
                "source": "USDA FoodData Central",
                "food": food.get("description", food_name),
                "serving_g": serving_g,
                "kcal":      round(n.get("Energy", 0) * scale, 1),
                "protein_g": round(n.get("Protein", 0) * scale, 1),
                "carb_g":    round(n.get("Carbohydrate, by difference", 0) * scale, 1),
                "fat_g":     round(n.get("Total lipid (fat)", 0) * scale, 1),
            }
    except Exception:
        return None


def _try_off(food_name: str, serving_g: float) -> dict | None:
    """Open Food Facts — no API key needed. Good for Turkish branded products."""
    try:
        with httpx.Client(timeout=10) as c:
            r = c.get(OFF_URL, params={
                "search_terms": food_name,
                "json": 1,
                "page_size": 1,
                "fields": "product_name,nutriments,brands,countries_tags",
            })
            r.raise_for_status()
            products = r.json().get("products", [])
            if not products:
                return None

            p = products[0]
            n = p.get("nutriments", {})
            scale = serving_g / 100.0
            return {
                "source": "Open Food Facts",
                "food": p.get("product_name") or food_name,
                "brand": (p.get("brands") or "").split(",")[0] or None,
                "serving_g": serving_g,
                "kcal":      round(n.get("energy-kcal_100g", 0) * scale, 1),
                "protein_g": round(n.get("proteins_100g", 0) * scale, 1),
                "carb_g":    round(n.get("carbohydrates_100g", 0) * scale, 1),
                "fat_g":     round(n.get("fat_100g", 0) * scale, 1),
            }
    except Exception:
        return None


def lookup(food_name: str, serving_grams: float = 100) -> dict:
    """Tool entry point. Tries USDA first, falls back to Open Food Facts."""
    if not food_name or not isinstance(food_name, str):
        return {"error": "food_name required"}
    try:
        serving_grams = float(serving_grams)
    except (TypeError, ValueError):
        serving_grams = 100.0

    result = _try_usda(food_name, serving_grams) or _try_off(food_name, serving_grams)
    if not result:
        return {
            "food": food_name,
            "error": "not found in USDA or Open Food Facts",
            "source": None,
        }
    return result
