import json
import os
import sqlite3
import uuid

DB_PATH = os.environ.get("INTERVIEWPILOT_DB", "interviewpilot.sqlite3")


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
    return c


def create(data: dict) -> str:
    sid = uuid.uuid4().hex[:12]
    with _conn() as c:
        c.execute("INSERT INTO sessions VALUES (?, ?)", (sid, json.dumps(data)))
    return sid


def load(sid: str):
    with _conn() as c:
        row = c.execute("SELECT data FROM sessions WHERE id=?", (sid,)).fetchone()
    return json.loads(row["data"]) if row else None


def save(sid: str, data: dict):
    with _conn() as c:
        c.execute("UPDATE sessions SET data=? WHERE id=?", (json.dumps(data), sid))
