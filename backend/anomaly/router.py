"""
FastAPI APIRouter for TulparAI Anomaly Detection.

This is mounted on the main TulparAI FastAPI app so that anomaly
endpoints share the same server, port, and middleware.

Endpoints:
  POST  /anomaly/check         — Check if a daily log is anomalous
  POST  /anomaly/check-batch   — Check multiple logs
  GET   /anomaly/demo          — Run demo with all profiles
  GET   /profiles/anomaly      — List athlete profiles
  GET   /anomaly-dashboard     — Serve dashboard UI
"""

from __future__ import annotations

import os
import json
import logging
from datetime import date

from fastapi import APIRouter, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

import backend.anomaly.config as config
from backend.anomaly.data.schemas import AthleteProfile, DailyLog, AnomalyResult
from backend.anomaly.data.synthetic import generate_profiles, _anomalous_log, _normal_log
from backend.anomaly.model.detector import AnomalyDetector

log = logging.getLogger("tulparai.anomaly")

router = APIRouter(tags=["anomaly"])

# ── Global state (loaded at startup via lifespan event) ──
detector: AnomalyDetector | None = None
profiles_map: dict[str, AthleteProfile] = {}


def load_anomaly_model():
    """Called from main.py lifespan — loads the trained model + profiles."""
    global detector, profiles_map

    try:
        detector = AnomalyDetector.load(config.MODEL_DIR)
        log.info(f"[anomaly] Loaded model from {config.MODEL_DIR}")
    except Exception as e:
        log.warning(f"[anomaly] Could not load model: {e}")
        log.warning("[anomaly] Run `python -m backend.anomaly.train` first!")

    profiles_path = os.path.join(config.DATA_DIR, "sample_profiles.json")
    if os.path.exists(profiles_path):
        with open(profiles_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
            profiles_list = [AthleteProfile(**p) for p in raw]
            profiles_map.update({p.athlete_id: p for p in profiles_list})
        log.info(f"[anomaly] Loaded {len(profiles_map)} athlete profiles")


# ──────────────────────────────────────────────────────────────
# Request / Response Models
# ──────────────────────────────────────────────────────────────

class CheckRequest(BaseModel):
    profile: AthleteProfile
    log: DailyLog


class CheckBatchRequest(BaseModel):
    profile: AthleteProfile
    logs: list[DailyLog]


# ──────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────

@router.post("/anomaly/check", response_model=AnomalyResult)
async def check_anomaly(req: CheckRequest):
    """Check if a single daily log is anomalous."""
    if detector is None:
        raise HTTPException(500, "Model not loaded. Run `python -m backend.anomaly.train` first.")
    result = detector.check(req.profile, req.log)

    # Trigger Telegram alert if anomaly detected
    if result.is_anomaly:
        _send_telegram_alert(req.profile, result)

    return result


@router.post("/anomaly/check-batch", response_model=list[AnomalyResult])
async def check_anomaly_batch(req: CheckBatchRequest):
    """Check multiple daily logs for the same athlete."""
    if detector is None:
        raise HTTPException(500, "Model not loaded. Run `python -m backend.anomaly.train` first.")
    results = detector.check_batch(req.profile, req.logs)

    # Trigger Telegram alerts for anomalies
    for result in results:
        if result.is_anomaly:
            _send_telegram_alert(req.profile, result)

    return results


@router.get("/anomaly/demo")
async def demo():
    """Run a demo: generate normal + anomalous logs for all profiles."""
    if detector is None:
        raise HTTPException(500, "Model not loaded. Run `python -m backend.anomaly.train` first.")

    results = []
    profiles = list(profiles_map.values())
    if not profiles:
        profiles = generate_profiles()

    today = date.today()

    for profile in profiles:
        # Normal log
        normal_log = _normal_log(profile, today)
        normal_result = detector.check(profile, normal_log)
        results.append({
            "type": "normal",
            "profile": profile.model_dump(mode="json"),
            "log": normal_log.model_dump(mode="json"),
            "result": normal_result.model_dump(mode="json"),
        })

        # Anomalous log
        anomalous_log, anomaly_type = _anomalous_log(profile, today)
        anomaly_result = detector.check(profile, anomalous_log)
        results.append({
            "type": f"anomaly ({anomaly_type})",
            "profile": profile.model_dump(mode="json"),
            "log": anomalous_log.model_dump(mode="json"),
            "result": anomaly_result.model_dump(mode="json"),
        })

    return JSONResponse(content=results)


@router.get("/profiles/anomaly")
async def get_profiles():
    """Return all loaded athlete profiles."""
    return [p.model_dump(mode="json") for p in profiles_map.values()]


# ── Serve Dashboard ──
dashboard_dir = os.path.join(config.BASE_DIR, "dashboard")


@router.get("/anomaly-dashboard")
async def anomaly_dashboard():
    """Serve the anomaly detection dashboard."""
    index_path = os.path.join(dashboard_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"message": "Dashboard not found", "hint": "Check backend/anomaly/dashboard/"}


# ──────────────────────────────────────────────────────────────
# Telegram Anomaly Alert
# ──────────────────────────────────────────────────────────────

def _send_telegram_alert(profile: AthleteProfile, result: AnomalyResult):
    """
    Send a Telegram notification when an anomaly is detected.
    Non-blocking fire-and-forget — failures are logged but don't crash the API.
    """
    import threading

    def _do_send():
        try:
            import httpx
            token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
            chat_id = os.getenv("TELEGRAM_ALERT_CHAT_ID", "").strip()

            if not token or not chat_id:
                return  # Telegram not configured — silently skip

            emoji_map = {
                "calorie_excess": "🍔",
                "calorie_deficit": "🥗",
                "macro_imbalance": "⚖️",
                "overtraining": "🏋️",
                "wrong_training": "❌",
                "under_recovery": "😴",
                "dehydration": "💧",
                "bad_meal_timing": "⏰",
            }
            emoji = emoji_map.get(result.anomaly_type, "⚠️")

            msg = (
                f"{emoji} *ANOMALY DETECTED*\n\n"
                f"👤 *Athlete:* {profile.name}\n"
                f"🏅 *Sport:* {profile.sport.title()}\n"
                f"📊 *Score:* {result.anomaly_score}/100\n"
                f"🔍 *Type:* {(result.anomaly_type or 'unknown').replace('_', ' ').title()}\n\n"
                f"💡 *Recommendation:*\n{result.recommendation}\n\n"
                f"📅 Date: {result.log_date}"
            )

            httpx.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": msg,
                    "parse_mode": "Markdown",
                },
                timeout=10,
            )
            log.info(f"[anomaly] Telegram alert sent for {profile.name} — {result.anomaly_type}")
        except Exception as e:
            log.warning(f"[anomaly] Telegram alert failed: {e}")

    threading.Thread(target=_do_send, daemon=True).start()
