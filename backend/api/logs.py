"""Log endpoints: /log (POST) and /log/{athlete_id} (GET recent)."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from backend.db.repos import LogRepo

router = APIRouter(prefix="/log")


class LogIn(BaseModel):
    athlete_id: str
    type: str  # training | meal | weight | sleep
    data: dict


@router.post("")
def add_log(log: LogIn):
    if log.type not in ("training", "meal", "weight", "sleep"):
        return {"ok": False, "error": f"invalid type: {log.type}"}
    log_id = LogRepo().add(log.athlete_id, log.type, log.data)
    return {"ok": True, "log_id": log_id}


@router.get("/{athlete_id}")
def recent_logs(athlete_id: str, hours: int = 48):
    return LogRepo().recent(athlete_id, hours)
