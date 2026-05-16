"""Thin repository classes around SQLite tables.

Three repos:
  - AthleteRepo  — upsert + get full profile (JSON columns auto-deserialized)
  - LogRepo      — add + recent (last N hours)
  - ChatRepo     — append + last N turns
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from backend.db.connection import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ----- Athletes ------------------------------------------------------------

# Column names that store JSON blobs — auto deserialised on read.
_ATHLETE_JSON_LIST_COLS = ("conditions", "medications", "allergies", "injury_history", "current_injuries")
_ATHLETE_JSON_DICT_COLS = ("sport_profile", "specific_targets")


class AthleteRepo:
    def get(self, athlete_id: str) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM athletes WHERE athlete_id = ?", (athlete_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_dict(dict(row))

    def upsert(self, athlete_id: str, profile: dict) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO athletes (
                    athlete_id, created_at, name, language, city, age, sex,
                    height_cm, weight_kg, sport, sport_profile_json,
                    training_phase, weekly_hours, training_days,
                    conditions_json, medications_json, allergies_json,
                    injury_history_json, current_injuries_json,
                    primary_goal, specific_targets_json, diet_type, religious_fasting
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(athlete_id) DO UPDATE SET
                    name=excluded.name, language=excluded.language, city=excluded.city,
                    age=excluded.age, sex=excluded.sex,
                    height_cm=excluded.height_cm, weight_kg=excluded.weight_kg,
                    sport=excluded.sport, sport_profile_json=excluded.sport_profile_json,
                    training_phase=excluded.training_phase,
                    weekly_hours=excluded.weekly_hours, training_days=excluded.training_days,
                    conditions_json=excluded.conditions_json,
                    medications_json=excluded.medications_json,
                    allergies_json=excluded.allergies_json,
                    injury_history_json=excluded.injury_history_json,
                    current_injuries_json=excluded.current_injuries_json,
                    primary_goal=excluded.primary_goal,
                    specific_targets_json=excluded.specific_targets_json,
                    diet_type=excluded.diet_type,
                    religious_fasting=excluded.religious_fasting
                """,
                (
                    athlete_id, _now(),
                    profile.get("name", "Athlete"),
                    profile.get("language", "tr"),
                    profile.get("city"),
                    profile.get("age"),
                    profile.get("sex"),
                    profile.get("height_cm"),
                    profile.get("weight_kg"),
                    profile.get("sport", "football"),
                    json.dumps(profile.get("sport_profile", {})),
                    profile.get("training_phase"),
                    profile.get("weekly_hours"),
                    profile.get("training_days"),
                    json.dumps(profile.get("conditions", [])),
                    json.dumps(profile.get("medications", [])),
                    json.dumps(profile.get("allergies", [])),
                    json.dumps(profile.get("injury_history", [])),
                    json.dumps(profile.get("current_injuries", [])),
                    profile.get("primary_goal"),
                    json.dumps(profile.get("specific_targets", {})),
                    profile.get("diet_type", "omnivore"),
                    profile.get("religious_fasting"),
                ),
            )
            conn.commit()

    @staticmethod
    def _row_to_dict(row: dict) -> dict:
        out = dict(row)
        for col in _ATHLETE_JSON_LIST_COLS:
            out[col] = json.loads(out.pop(f"{col}_json", "[]") or "[]")
        for col in _ATHLETE_JSON_DICT_COLS:
            out[col] = json.loads(out.pop(f"{col}_json", "{}") or "{}")
        return out


# ----- Logs ----------------------------------------------------------------

class LogRepo:
    def add(self, athlete_id: str, log_type: str, data: dict) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO logs (athlete_id, type, timestamp, data_json) VALUES (?,?,?,?)",
                (athlete_id, log_type, _now(), json.dumps(data)),
            )
            conn.commit()
            return cur.lastrowid

    def recent(self, athlete_id: str, hours: int = 48) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM logs WHERE athlete_id = ? "
                "AND timestamp > datetime('now', ?) "
                "ORDER BY timestamp DESC",
                (athlete_id, f"-{hours} hours"),
            ).fetchall()
            return [
                {**dict(r), "data": json.loads(r["data_json"])}
                for r in rows
            ]


# ----- Chat history --------------------------------------------------------

class ChatRepo:
    def append(self, athlete_id: str, role: str, content: str, metadata: dict | None = None) -> None:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO chat_history (athlete_id, timestamp, role, content, metadata_json) "
                "VALUES (?,?,?,?,?)",
                (athlete_id, _now(), role, content, json.dumps(metadata or {})),
            )
            conn.commit()

    def last(self, athlete_id: str, n: int = 6) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT role, content FROM chat_history "
                "WHERE athlete_id = ? ORDER BY msg_id DESC LIMIT ?",
                (athlete_id, n),
            ).fetchall()
            return [dict(r) for r in reversed(rows)]
