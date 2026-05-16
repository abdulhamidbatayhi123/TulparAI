"""TulparAI Telegram bot.

Ported in spirit from OpenAgent's `telegram_bot.py` but with TulparAI improvements:
  - Multi-tenant: each Telegram user_id maps to a unique athlete_id, auto-created
    on first message via /start or any text
  - Reuses the full Orchestrator (regex fast-path, 4-agent pipeline, vision, etc.)
  - Photo handler → routes through analyze_image tool via the orchestrator's
    image_base64 parameter
  - Commands: /start  /profile  /sport  /clear

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
    "Komutlar:\n"
    "/sport futbol|gures|halter|voleybol — spor dalını ayarla\n"
    "/profile ad:Ahmet yas:24 kilo:78 boy:178 — profilini güncelle\n"
    "/clear — sohbeti temizle\n\n"
    "Yemek fotoğrafı veya sakatlık fotoğrafı gönderebilirsin — doğrulanmış vision modeli analiz eder."
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
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    log.info("🐎 TulparAI Telegram bot starting — polling Telegram for updates...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
