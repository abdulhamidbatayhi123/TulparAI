"""OpenWeather current-conditions lookup.

Used by the Reasoner to adjust outdoor-training recommendations
(hydration, intensity, clothing) based on the athlete's city.
"""
from __future__ import annotations

import httpx
from backend.config import settings

URL = "https://api.openweathermap.org/data/2.5/weather"


def get(city: str, date: str | None = None) -> dict:
    """Returns current weather for `city`. `date` is accepted but ignored (free tier = current only).

    Output dict keys: city, temp_c, feels_like_c, humidity_pct, wind_ms, condition, summary.
    On error returns {"city": city, "error": "..."}.
    """
    if not settings.openweather_api_key:
        return {"city": city, "error": "OPENWEATHER_API_KEY not configured"}
    if not city:
        return {"error": "city required"}

    try:
        with httpx.Client(timeout=10) as c:
            r = c.get(URL, params={
                "q": city,
                "appid": settings.openweather_api_key,
                "units": "metric",
                "lang": "tr",
            })
            r.raise_for_status()
            d = r.json()

        return {
            "city":          d.get("name", city),
            "country":       d.get("sys", {}).get("country"),
            "temp_c":        d["main"]["temp"],
            "feels_like_c":  d["main"].get("feels_like"),
            "humidity_pct":  d["main"]["humidity"],
            "wind_ms":       d["wind"]["speed"],
            "condition":     d["weather"][0]["description"],
            "summary": (
                f"{d.get('name', city)}: {d['main']['temp']}°C, "
                f"{d['weather'][0]['description']}, "
                f"%{d['main']['humidity']} nem, rüzgar {d['wind']['speed']} m/s"
            ),
        }
    except httpx.HTTPStatusError as e:
        return {"city": city, "error": f"HTTP {e.response.status_code}: {e.response.text[:120]}"}
    except Exception as e:
        return {"city": city, "error": f"{type(e).__name__}: {e}"}
