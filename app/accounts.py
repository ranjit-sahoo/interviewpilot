"""Optional accounts and saved history.

Guests keep every feature. An account only adds "save to my history". Storage is Postgres when DATABASE_URL
is set (free managed tier in production) and SQLite otherwise (local runs and tests).
Passwords use scrypt; sessions are random tokens stored hashed and sent in an HttpOnly cookie.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time
import uuid

DATABASE_URL = os.environ.get("DATABASE_URL", "")
SQLITE_PATH = os.environ.get("ACCOUNTS_DB", os.environ.get("INTERVIEWPILOT_DB", "interviewpilot.sqlite3"))
SESSION_DAYS = 30
MAX_HISTORY_PER_USER = 200
MAX_ITEM_BYTES = 120_000
KINDS = {"star", "brief", "prep", "code_review", "resume", "interview", "negotiation", "match", "review"}
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{2,}$")

_pool = None
_pool_lock = threading.Lock()


def using_postgres() -> bool:
    return bool(DATABASE_URL)


class Conn:
    """Tiny adapter so the same SQL (written with ?) runs on SQLite and Postgres."""

    def __init__(self):
        if using_postgres():
            global _pool
            with _pool_lock:
                if _pool is None:
                    from psycopg_pool import ConnectionPool

                    _pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=5, open=True, kwargs={"autocommit": False})
                    with _pool.connection() as c:
                        for stmt in _schema():
                            c.execute(stmt)
            self._ctx = _pool.connection()
            self.c = self._ctx.__enter__()
            self.pg = True
        else:
            self.c = sqlite3.connect(SQLITE_PATH, timeout=15)
            self.c.row_factory = sqlite3.Row
            for stmt in _schema():
                self.c.execute(stmt)
            self.pg = False

    def run(self, sql, params=()):
        if self.pg:
            cur = self.c.execute(sql.replace("?", "%s"), params)
            cols = [d.name for d in cur.description] if cur.description else []
            return [dict(zip(cols, r)) for r in cur.fetchall()] if cols else []
        cur = self.c.execute(sql, params)
        return [dict(r) for r in cur.fetchall()] if cur.description else []

    def __enter__(self):
        return self

    def __exit__(self, et, ev, tb):
        if self.pg:
            return self._ctx.__exit__(et, ev, tb)
        try:
            self.c.commit() if et is None else self.c.rollback()
        finally:
            self.c.close()


def _schema():
    return [
        "CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, pw_hash TEXT NOT NULL, created DOUBLE PRECISION NOT NULL)"
        if using_postgres() else
        "CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, pw_hash TEXT NOT NULL, created REAL NOT NULL)",
        "CREATE TABLE IF NOT EXISTS auth_sessions (token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires DOUBLE PRECISION NOT NULL)"
        if using_postgres() else
        "CREATE TABLE IF NOT EXISTS auth_sessions (token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires REAL NOT NULL)",
        "CREATE TABLE IF NOT EXISTS history (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, kind TEXT NOT NULL, title TEXT NOT NULL, data TEXT NOT NULL, created DOUBLE PRECISION NOT NULL)"
        if using_postgres() else
        "CREATE TABLE IF NOT EXISTS history (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, kind TEXT NOT NULL, title TEXT NOT NULL, data TEXT NOT NULL, created REAL NOT NULL)",
        "CREATE INDEX IF NOT EXISTS history_user ON history (user_id, created)",
    ]


# ---------- passwords ----------
# OWASP-recommended scrypt setting (N=2^15, r=8, p=3). Hashes are stored with their parameters so they can be
# upgraded later; the older N=2^14, p=1 format is still verified and silently re-hashed on the next login.
_SCRYPT_SLOTS = threading.BoundedSemaphore(2)  # cap memory (about 32 MB per hash) on the small free instance


def _scrypt(pw: str, salt: bytes, n: int, p: int) -> bytes:
    with _SCRYPT_SLOTS:
        return hashlib.scrypt(pw.encode(), salt=salt, n=n, r=8, p=p, dklen=32, maxmem=96 * 1024 * 1024)


def hash_password(pw: str) -> str:
    salt = secrets.token_bytes(16)
    return f"scrypt2${2**15}${3}${salt.hex()}${_scrypt(pw, salt, 2**15, 3).hex()}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        parts = stored.split("$")
        if parts[0] == "scrypt2":
            _, n, p, salt, h = parts
            calc = _scrypt(pw, bytes.fromhex(salt), int(n), int(p))
        else:
            _, salt, h = parts
            calc = _scrypt(pw, bytes.fromhex(salt), 2**14, 1)
        return hmac.compare_digest(calc.hex(), h)
    except Exception:
        return False


def needs_rehash(stored: str) -> bool:
    return not stored.startswith("scrypt2$")


_DUMMY = hash_password("not-a-real-password")  # equalizes timing for unknown emails


def _clean_email(email: str) -> str:
    e = (email or "").strip().lower()
    if not EMAIL_RE.match(e):
        raise ValueError("Enter a valid email address.")
    return e


def _hash_token(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


# ---------- users and sessions ----------
def _new_session(c: Conn, user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    now = time.time()
    c.run("DELETE FROM auth_sessions WHERE expires < ?", (now,))
    c.run("INSERT INTO auth_sessions (token_hash, user_id, expires) VALUES (?, ?, ?)", (_hash_token(token), user_id, now + SESSION_DAYS * 86400))
    return token


def register(email: str, password: str):
    email = _clean_email(email)
    if len(password or "") < 8 or len(password) > 200:
        raise ValueError("Password must be 8 to 200 characters.")
    uid = uuid.uuid4().hex
    pw = hash_password(password)
    with Conn() as c:
        if c.run("SELECT id FROM users WHERE email=?", (email,)):
            raise ValueError("An account with this email already exists. Try logging in.")
        try:
            c.run("INSERT INTO users (id, email, pw_hash, created) VALUES (?, ?, ?, ?)", (uid, email, pw, time.time()))
        except Exception:  # unique race
            raise ValueError("An account with this email already exists. Try logging in.")
        return {"id": uid, "email": email}, _new_session(c, uid)


def login(email: str, password: str):
    email = (email or "").strip().lower()
    with Conn() as c:
        rows = c.run("SELECT id, pw_hash FROM users WHERE email=?", (email,))
        ok = verify_password(password or "", rows[0]["pw_hash"] if rows else _DUMMY)
        if not rows or not ok:
            raise PermissionError("Wrong email or password.")
        if needs_rehash(rows[0]["pw_hash"]):
            c.run("UPDATE users SET pw_hash=? WHERE id=?", (hash_password(password), rows[0]["id"]))
        return {"id": rows[0]["id"], "email": email}, _new_session(c, rows[0]["id"])


def user_for(token: str | None):
    if not token:
        return None
    with Conn() as c:
        rows = c.run(
            "SELECT u.id, u.email FROM auth_sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires>?",
            (_hash_token(token), time.time()),
        )
    return rows[0] if rows else None


def logout(token: str | None):
    if token:
        with Conn() as c:
            c.run("DELETE FROM auth_sessions WHERE token_hash=?", (_hash_token(token),))


def delete_account(user_id: str):
    with Conn() as c:
        c.run("DELETE FROM history WHERE user_id=?", (user_id,))
        c.run("DELETE FROM auth_sessions WHERE user_id=?", (user_id,))
        c.run("DELETE FROM users WHERE id=?", (user_id,))


# ---------- history ----------
def save_item(user_id: str, kind: str, title: str, data) -> dict:
    if kind not in KINDS:
        raise ValueError("Unknown item type.")
    blob = json.dumps(data, ensure_ascii=False)
    if len(blob.encode()) > MAX_ITEM_BYTES:
        raise ValueError("This item is too large to save.")
    title = " ".join((title or "").split())[:120] or kind
    iid, now = uuid.uuid4().hex[:16], time.time()
    with Conn() as c:
        c.run("INSERT INTO history (id, user_id, kind, title, data, created) VALUES (?, ?, ?, ?, ?, ?)", (iid, user_id, kind, title, blob, now))
        extra = c.run("SELECT id FROM history WHERE user_id=? ORDER BY created DESC", (user_id,))[MAX_HISTORY_PER_USER:]
        for r in extra:
            c.run("DELETE FROM history WHERE id=?", (r["id"],))
    return {"id": iid, "kind": kind, "title": title, "created": now}


def list_items(user_id: str) -> list[dict]:
    with Conn() as c:
        return c.run("SELECT id, kind, title, created FROM history WHERE user_id=? ORDER BY created DESC LIMIT ?", (user_id, MAX_HISTORY_PER_USER))


def get_item(user_id: str, iid: str):
    with Conn() as c:
        rows = c.run("SELECT id, kind, title, data, created FROM history WHERE id=? AND user_id=?", (iid, user_id))
    if not rows:
        return None
    r = rows[0]
    r["data"] = json.loads(r["data"])
    return r


def delete_item(user_id: str, iid: str) -> bool:
    with Conn() as c:
        had = bool(c.run("SELECT id FROM history WHERE id=? AND user_id=?", (iid, user_id)))
        c.run("DELETE FROM history WHERE id=? AND user_id=?", (iid, user_id))
    return had
