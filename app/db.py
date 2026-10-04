import json
import os
import sqlite3
import time
import uuid

DB_PATH = os.environ.get("INTERVIEWPILOT_DB", "interviewpilot.sqlite3")
TTL_SECONDS = 7 * 24 * 3600


def _conn():
    c = sqlite3.connect(DB_PATH, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
    cols = [r["name"] for r in c.execute("PRAGMA table_info(sessions)")]
    if "created" not in cols:
        c.execute("ALTER TABLE sessions ADD COLUMN created REAL DEFAULT 0")
    return c


def create(data: dict) -> str:
    sid = uuid.uuid4().hex[:12]
    now = time.time()
    with _conn() as c:
        c.execute("INSERT INTO sessions (id, data, created) VALUES (?, ?, ?)", (sid, json.dumps(data), now))
        c.execute("DELETE FROM sessions WHERE created > 0 AND created < ?", (now - TTL_SECONDS,))
    return sid


def load(sid: str):
    with _conn() as c:
        row = c.execute("SELECT data FROM sessions WHERE id=?", (sid,)).fetchone()
    return json.loads(row["data"]) if row else None


def save(sid: str, data: dict):
    with _conn() as c:
        c.execute("UPDATE sessions SET data=? WHERE id=?", (json.dumps(data), sid))
