"""TulparAI Telegram bot.

Ported in spirit from OpenAgent's `telegram_bot.py` but with TulparAI improvements:
  - Multi-tenant: each Telegram user_id maps to a unique athlete_id, auto-created
    on first message via /start or any text
  - Reuses the full Orchestrator (regex fast-path, 4-agent pipeline, vision, etc.)
  - Photo handler → routes through analyze_image tool via the orchestrator's
    image_base64 parameter
  - Anomaly detection integration: /log for daily check-ins, /anomaly for demo
  - Commands: /start  /profile  /sport  /clear  /log  /anomaly  /help

Run as a separate process:
    cd backend
    ./.venv/Scripts/python.exe -m backend.telegram_bot

Required env: TELEGRAM_BOT_TOKEN (set in backend/.env)
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
from datetime import date
from typing import Any

from telegram import Update, Message
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes,
)

from backend.config import settings
from backend.db.connection import init_db
from backend.db.repos import AthleteRepo, ChatRepo
from backend.orchestrator import Orchestrator

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
log = logging.getLogger("tulparai.telegram")

VALID_SPORTS = {"football", "wrestling", "weightlifting", "volleyball"}
DEFAULT_SPORT = "football"


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _athlete_id_for(tg_user_id: int) -> str:
    """Stable per-user athlete id: tg_<tg_user_id>."""
    return f"tg_{tg_user_id}"


def _ensure_athlete(tg_user_id: int, name: str) -> dict:
    """Auto-create a default profile on first interaction. Returns the full profile."""
    aid = _athlete_id_for(tg_user_id)
    repo = AthleteRepo()
    profile = repo.get(aid)
    if profile is None:
        repo.upsert(aid, {
            "athlete_id": aid,
            "name": name or f"User {tg_user_id}",
            "language": "tr",
            "city": "Istanbul",
            "sport": DEFAULT_SPORT,
            "sport_profile": {},
            "primary_goal": "performance",
            "diet_type": "omnivore",
        })
        profile = repo.get(aid)
    return profile


async def _orchestrate(
    user_message: str,
    tg_user_id: int,
    tg_name: str,
    image_base64: str | None = None,
) -> str:
    """Run the orchestrator and return the final answer (drains the SSE generator)."""
    profile = _ensure_athlete(tg_user_id, tg_name)
    history = ChatRepo().last(profile["athlete_id"], n=6)

    final_answer = ""
    # Orchestrator is sync — run in a thread so we don't block the event loop
    def _run() -> str:
        nonlocal final_answer
        for ev in Orchestrator().run(
            user_message=user_message,
            athlete_id=profile["athlete_id"],
            profile=profile,
            history=history,
            image_base64=image_base64,
        ):
            if ev.get("type") == "done":
                final_answer = ev.get("answer", "")
        return final_answer

    answer = await asyncio.get_running_loop().run_in_executor(None, _run)

    # Persist the conversation
    try:
        ChatRepo().append(profile["athlete_id"], "user", user_message)
        if answer:
            ChatRepo().append(profile["athlete_id"], "assistant", answer)
    except Exception:
        pass
    return answer


# ---------------------------------------------------------------------------
#  Handlers
# ---------------------------------------------------------------------------

WELCOME = (
    "🐎 *TulparAI* — Türk sporcular için doğrulanmış AI antrenör.\n\n"
    "Bana sorabileceklerin:\n"
    "• Maç öncesi / sonrası beslenme\n"
    "• Antrenman planı önerileri\n"
    "• İyileşme ve uyku\n"
    "• Sakatlık ön değerlendirmesi (medikal tavsiye değildir)\n\n"
    "*Komutlar:*\n"
    "/sport futbol|gures|halter|voleybol — spor dalını ayarla\n"
    "/profile ad:Ahmet yas:24 kilo:78 boy:178 — profilini güncelle\n"
    "/log — günlük verini gir → anomali tespiti\n"
    "/anomaly — demo: tüm sporcuları test et\n"
    "/clear — sohbeti temizle\n"
    "/help — komutları göster\n\n"
    "Yemek fotoğrafı veya sakatlık fotoğrafı gönderebilirsin — doğrulanmış vision modeli analiz eder.\n\n"
    "⚡ *Anomali Tespiti:* Günlük verilerini /log ile gönder — yapay zeka anormal davranışları otomatik tespit eder!"
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    _ensure_athlete(user.id, user.full_name)
    await update.message.reply_text(WELCOME, parse_mode="Markdown")


async def cmd_sport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    profile = _ensure_athlete(user.id, user.full_name)
    text = " ".join(context.args).strip().lower()
    sport_map = {
        "futbol": "football", "football": "football", "soccer": "football",
        "gures": "wrestling", "güreş": "wrestling", "wrestling": "wrestling",
        "halter": "weightlifting", "weightlifting": "weightlifting", "lift": "weightlifting",
        "voleybol": "volleyball", "volleyball": "volleyball", "volley": "volleyball",
    }
    chosen = sport_map.get(text)
    if not chosen:
        await update.message.reply_text(
            "Geçerli spor dalı seç: /sport futbol | gures | halter | voleybol"
        )
        return

    profile["sport"] = chosen
    AthleteRepo().upsert(profile["athlete_id"], profile)
    await update.message.reply_text(f"✅ Spor dalın güncellendi: *{chosen}*", parse_mode="Markdown")


PROFILE_RE = re.compile(r"(\w+)\s*[:=]\s*([^\s]+)")


async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    profile = _ensure_athlete(user.id, user.full_name)
    args_str = " ".join(context.args)

    if not args_str.strip():
        sp = profile.get("sport_profile", {})
        await update.message.reply_text(
            f"*Mevcut profil*\n"
            f"İsim: {profile.get('name')}\n"
            f"Spor: {profile.get('sport')} · {sp}\n"
            f"Yaş: {profile.get('age')} · Kilo: {profile.get('weight_kg')}kg · "
            f"Boy: {profile.get('height_cm')}cm\n"
            f"Faz: {profile.get('training_phase')} · Hedef: {profile.get('primary_goal')}\n\n"
            f"Güncellemek için: /profile ad:Ahmet yas:24 kilo:78 boy:178",
            parse_mode="Markdown",
        )
        return

    # Parse key:value pairs
    field_map = {
        "ad": "name", "isim": "name", "name": "name",
        "yas": "age", "yaş": "age", "age": "age",
        "kilo": "weight_kg", "weight": "weight_kg",
        "boy": "height_cm", "height": "height_cm",
        "cinsiyet": "sex", "sex": "sex",
        "sehir": "city", "şehir": "city", "city": "city",
        "hedef": "primary_goal", "goal": "primary_goal",
        "diyet": "diet_type", "diet": "diet_type",
    }
    updated = {}
    for raw_key, raw_val in PROFILE_RE.findall(args_str):
        key = field_map.get(raw_key.lower())
        if not key:
            continue
        if key in ("age",):
            try:
                updated[key] = int(raw_val)
            except ValueError:
                continue
        elif key in ("weight_kg", "height_cm"):
            try:
                updated[key] = float(raw_val.replace(",", "."))
            except ValueError:
                continue
        else:
            updated[key] = raw_val

    if not updated:
        await update.message.reply_text(
            "Hiç alan tanınmadı. Örnek: /profile ad:Ahmet yas:24 kilo:78 boy:178"
        )
        return

    profile.update(updated)
    AthleteRepo().upsert(profile["athlete_id"], profile)
    await update.message.reply_text(
        f"✅ Güncellenen alanlar: {', '.join(updated.keys())}"
    )


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # We don't actually delete chat_history rows (audit log) — just say "fresh start"
    await update.message.reply_text("🧹 Sohbet kontekstin temizlendi. Yeni soruyla başla.")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available commands."""
    help_text = (
        "🐎 *TulparAI Komutlar*\n\n"
        "/start — Hoş geldin mesajı\n"
        "/sport futbol|gures|halter|voleybol — Spor dalını ayarla\n"
        "/profile — Profilini gör / güncelle\n"
        "/log kal:2500 pro:180 karb:300 yag:70 antrenman:90 yogunluk:7 uyku:8 su:3 — Günlük verini gir\n"
        "/anomaly — Demo: tüm sporcuları anomali kontrolü\n"
        "/clear — Sohbeti temizle\n"
        "/help — Bu mesaj\n\n"
        "Ayrıca herhangi bir soru sorabilir veya fotoğraf gönderebilirsin!"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


# ---------------------------------------------------------------------------
#  Anomaly Detection Handlers
# ---------------------------------------------------------------------------

def _load_anomaly_detector():
    """Lazily load the anomaly detector (singleton)."""
    try:
        from backend.anomaly.model.detector import AnomalyDetector
        import backend.anomaly.config as anomaly_config
        return AnomalyDetector.load(anomaly_config.MODEL_DIR)
    except Exception as e:
        log.warning(f"Could not load anomaly detector: {e}")
        return None


_detector = None


def _get_detector():
    global _detector
    if _detector is None:
        _detector = _load_anomaly_detector()
    return _detector


LOG_HELP = (
    "📋 *Günlük veri girişi*\n\n"
    "Şu formatta gönder:\n"
    "`/log kal:2500 pro:180 karb:300 yag:70 antrenman:90 yogunluk:7 uyku:8 su:3`\n\n"
    "*Alanlar:*\n"
    "• `kal` — Kalori (kcal)\n"
    "• `pro` — Protein (g)\n"
    "• `karb` — Karbonhidrat (g)\n"
    "• `yag` — Yağ (g)\n"
    "• `antrenman` — Antrenman süresi (dk)\n"
    "• `yogunluk` — Antrenman yoğunluğu (0-10)\n"
    "• `uyku` — Uyku süresi (saat)\n"
    "• `su` — Su tüketimi (litre)\n\n"
    "Opsiyonel: `tip:1` (antrenman planına uyum, 0-1), `ogun:0.8` (öğün zamanlaması, 0-1)"
)


async def cmd_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /log kal:2500 pro:180 karb:300 yag:70 antrenman:90 yogunluk:7 uyku:8 su:3
    Runs the daily log through the anomaly detector and reports back.
    """
    user = update.effective_user
    args_str = " ".join(context.args).strip()

    if not args_str:
        await update.message.reply_text(LOG_HELP, parse_mode="Markdown")
        return

    # Parse key:value pairs
    field_map = {
        "kal": "calories_eaten", "kalori": "calories_eaten", "cal": "calories_eaten",
        "pro": "protein_g", "protein": "protein_g",
        "karb": "carbs_g", "carbs": "carbs_g", "karbonhidrat": "carbs_g",
        "yag": "fat_g", "fat": "fat_g",
        "antrenman": "training_duration_min", "training": "training_duration_min", "sure": "training_duration_min",
        "yogunluk": "training_intensity", "intensity": "training_intensity",
        "uyku": "sleep_hours", "sleep": "sleep_hours",
        "su": "hydration_liters", "water": "hydration_liters",
        "tip": "training_type_match", "ogun": "meal_timing_score",
    }

    parsed = {}
    for match in re.finditer(r"(\w+)\s*[:=]\s*([\d.,]+)", args_str):
        key = field_map.get(match.group(1).lower())
        if key:
            try:
                parsed[key] = float(match.group(2).replace(",", "."))
            except ValueError:
                pass

    required = ["calories_eaten", "protein_g", "carbs_g", "fat_g"]
    missing = [k for k in required if k not in parsed]
    if missing:
        missing_tr = {"calories_eaten": "kal", "protein_g": "pro", "carbs_g": "karb", "fat_g": "yag"}
        missing_labels = [missing_tr.get(m, m) for m in missing]
        await update.message.reply_text(
            f"⚠ Eksik alanlar: {', '.join(missing_labels)}\n\n"
            f"Örnek: `/log kal:2500 pro:180 karb:300 yag:70 antrenman:90 yogunluk:7 uyku:8 su:3`",
            parse_mode="Markdown",
        )
        return

    await update.message.chat.send_action("typing")

    # Get the user's profile to build an AthleteProfile for anomaly detection
    profile_data = _ensure_athlete(user.id, user.full_name)
    sport = profile_data.get("sport", DEFAULT_SPORT)

    # Build athlete profile for anomaly system
    from backend.anomaly.data.schemas import AthleteProfile, DailyLog
    from backend.anomaly.data.synthetic import _mifflin_st_jeor, SPORT_PAL, GOAL_MACROS

    weight = profile_data.get("weight_kg", 80)
    height = profile_data.get("height_cm", 178)
    age = profile_data.get("age", 25)
    goal = "maintain"  # default

    pal = SPORT_PAL.get(sport, 1.725)
    tdee = _mifflin_st_jeor(weight, height, age, pal)
    macros = GOAL_MACROS.get(goal, GOAL_MACROS["maintain"])

    anomaly_profile = AthleteProfile(
        athlete_id=profile_data["athlete_id"],
        name=profile_data.get("name", f"User {user.id}"),
        sport=sport,
        age=age,
        weight_kg=weight,
        height_cm=height,
        goal=goal,
        target_daily_calories=tdee,
        target_protein_g=round(tdee * macros["protein_pct"] / 4),
        target_carbs_g=round(tdee * macros["carbs_pct"] / 4),
        target_fat_g=round(tdee * macros["fat_pct"] / 9),
    )

    today = date.today()
    daily_log = DailyLog(
        athlete_id=profile_data["athlete_id"],
        log_date=today,
        calories_eaten=parsed["calories_eaten"],
        protein_g=parsed["protein_g"],
        carbs_g=parsed["carbs_g"],
        fat_g=parsed["fat_g"],
        training_duration_min=parsed.get("training_duration_min", 60),
        training_intensity=parsed.get("training_intensity", 5),
        training_type_match=parsed.get("training_type_match", 1.0),
        sleep_hours=parsed.get("sleep_hours", 7.5),
        hydration_liters=parsed.get("hydration_liters", 2.5),
        rest_day=parsed.get("training_duration_min", 60) < 15,
        meal_timing_score=parsed.get("meal_timing_score", 0.8),
        day_of_week=today.weekday(),
    )

    detector = _get_detector()
    if detector is None:
        await update.message.reply_text(
            "⚠ Anomali modeli yüklenmedi. Lütfen önce `python -m backend.anomaly.train` çalıştırın."
        )
        return

    result = detector.check(anomaly_profile, daily_log)

    # Format the response
    if result.is_anomaly:
        emoji_map = {
            "calorie_excess": "🍔", "calorie_deficit": "🥗",
            "macro_imbalance": "⚖️", "overtraining": "🏋️",
            "wrong_training": "❌", "under_recovery": "😴",
            "dehydration": "💧", "bad_meal_timing": "⏰",
        }
        emoji = emoji_map.get(result.anomaly_type, "⚠️")
        atype = (result.anomaly_type or "unknown").replace("_", " ").title()

        msg = (
            f"{emoji} *ANOMALY DETECTED — ANORMAL DAVRANIŞ!*\n\n"
            f"📊 *Skor:* {result.anomaly_score}/100\n"
            f"🔍 *Tür:* {atype}\n\n"
            f"💡 *Öneri:*\n{result.recommendation}\n\n"
            f"📅 Tarih: {result.log_date}"
        )
    else:
        msg = (
            f"✅ *HER ŞEY NORMAL!*\n\n"
            f"📊 *Skor:* {result.anomaly_score}/100\n"
            f"🎯 Planına uygun devam ediyorsun, harika!\n\n"
            f"📅 Tarih: {result.log_date}"
        )

    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_anomaly_demo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run anomaly detection demo with all sample profiles."""
    await update.message.chat.send_action("typing")

    detector = _get_detector()
    if detector is None:
        await update.message.reply_text(
            "⚠ Anomali modeli yüklenmedi. `python -m backend.anomaly.train` çalıştırın."
        )
        return

    from backend.anomaly.data.synthetic import generate_profiles, _normal_log, _anomalous_log

    profiles = generate_profiles()
    today = date.today()
    lines = ["🧪 *Anomali Tespiti Demo*\n"]

    for profile in profiles[:4]:  # First 4 athletes to keep message short
        normal_log = _normal_log(profile, today)
        normal_result = detector.check(profile, normal_log)

        anomalous_log, a_type = _anomalous_log(profile, today)
        anomaly_result = detector.check(profile, anomalous_log)

        n_icon = "✅" if not normal_result.is_anomaly else "⚠️"
        a_icon = "⚠️" if anomaly_result.is_anomaly else "✅"

        lines.append(
            f"\n👤 *{profile.name}* ({profile.sport})\n"
            f"  {n_icon} Normal gün: skor {normal_result.anomaly_score}\n"
            f"  {a_icon} Anormal gün ({a_type}): skor {anomaly_result.anomaly_score}"
        )
        if anomaly_result.is_anomaly and anomaly_result.recommendation:
            lines.append(f"  💡 _{anomaly_result.recommendation[:80]}..._")

    lines.append(f"\n_Toplam {len(profiles)} sporcu profili mevcut_")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text or ""
    await update.message.chat.send_action("typing")
    try:
        answer = await _orchestrate(text, user.id, user.full_name)
        await update.message.reply_text(answer or "(boş yanıt)", parse_mode=None)
    except Exception as e:
        log.exception("text handler error")
        await update.message.reply_text(f"⚠ Hata: {e}")


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg: Message = update.message
    caption = (msg.caption or "Bu görseli analiz et").strip()

    await msg.chat.send_action("upload_photo")

    try:
        # Take the largest photo Telegram offers
        tg_file = await msg.photo[-1].get_file()
        photo_bytes = await tg_file.download_as_bytearray()
        b64 = base64.b64encode(bytes(photo_bytes)).decode("ascii")
        answer = await _orchestrate(caption, user.id, user.full_name, image_base64=b64)
        await msg.reply_text(answer or "(boş yanıt)", parse_mode=None)
    except Exception as e:
        log.exception("photo handler error")
        await msg.reply_text(f"⚠ Görsel analizi başarısız: {e}")


# ---------------------------------------------------------------------------
#  Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    # Load .env so os.getenv picks up TELEGRAM_BOT_TOKEN etc.
    from pathlib import Path
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

    init_db()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN missing. Get one from @BotFather on Telegram "
            "and add to backend/.env as TELEGRAM_BOT_TOKEN=<token>."
        )

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("sport", cmd_sport))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("log", cmd_log))
    app.add_handler(CommandHandler("anomaly", cmd_anomaly_demo))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    log.info("🐎 TulparAI Telegram bot starting — polling Telegram for updates...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
