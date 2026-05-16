-- TulparAI database schema. SQLite single-file store.
-- Initialised by backend/db/connection.py:init_db().

CREATE TABLE IF NOT EXISTS athletes (
    athlete_id              TEXT PRIMARY KEY,
    created_at              TEXT NOT NULL,
    name                    TEXT NOT NULL,
    language                TEXT NOT NULL DEFAULT 'tr',
    city                    TEXT,
    age                     INTEGER,
    sex                     TEXT,
    height_cm               REAL,
    weight_kg               REAL,
    sport                   TEXT NOT NULL,                  -- football | wrestling | weightlifting | volleyball
    sport_profile_json      TEXT NOT NULL DEFAULT '{}',     -- polymorphic per-sport fields
    training_phase          TEXT,                            -- preseason | competition | offseason | recovery
    weekly_hours            INTEGER,
    training_days           INTEGER,
    conditions_json         TEXT NOT NULL DEFAULT '[]',
    medications_json        TEXT NOT NULL DEFAULT '[]',
    allergies_json          TEXT NOT NULL DEFAULT '[]',
    injury_history_json     TEXT NOT NULL DEFAULT '[]',
    current_injuries_json   TEXT NOT NULL DEFAULT '[]',
    primary_goal            TEXT,                            -- performance | bulk | cut | maintain | injury_recovery | weight_class
    specific_targets_json   TEXT NOT NULL DEFAULT '{}',
    diet_type               TEXT DEFAULT 'omnivore',
    religious_fasting       TEXT
);

CREATE TABLE IF NOT EXISTS logs (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    athlete_id  TEXT NOT NULL REFERENCES athletes(athlete_id) ON DELETE CASCADE,
    type        TEXT NOT NULL,                               -- training | meal | weight | sleep
    timestamp   TEXT NOT NULL,
    data_json   TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_logs_athlete_ts ON logs(athlete_id, timestamp DESC);

CREATE TABLE IF NOT EXISTS chat_history (
    msg_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    athlete_id      TEXT NOT NULL REFERENCES athletes(athlete_id) ON DELETE CASCADE,
    timestamp       TEXT NOT NULL,
    role            TEXT NOT NULL,                          -- user | assistant
    content         TEXT NOT NULL,
    metadata_json   TEXT NOT NULL DEFAULT '{}'              -- tool_trace, verification_score, removed_claims
);
CREATE INDEX IF NOT EXISTS idx_chat_athlete_ts ON chat_history(athlete_id, timestamp DESC);
