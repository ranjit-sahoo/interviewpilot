"""Hard spend guard for the paid model API.

The model account is prepaid credit, but a card is on file, so overspending could bill the owner. Every model call
adds an estimated cost (token usage x deliberately generous prices) to a persistent counter. When the
daily or total budget is reached, AI calls stop with a friendly message; non-AI features keep working.
Counters live in the accounts database (Postgres in production) so restarts cannot reset them.
"""
import os
import threading
import time

TOTAL_CAP = float(os.environ.get("SPEND_TOTAL_CAP_USD", "20"))  # credit is $29.50; stay well inside it
DAILY_CAP = float(os.environ.get("SPEND_DAILY_CAP_USD", "3"))
# USD per 1M tokens, rounded UP from the price list and including tax, so the estimate over-counts.
PRICES = {"ultra": (1.8, 4.5), "nano": (0.25, 0.8)}
_lock = threading.Lock()
_cache = {"t": 0.0, "total": 0.0, "day": 0.0, "d": None}
_ready = False


class BudgetExceeded(RuntimeError):
    pass


def _conn():
    from app import accounts

    return accounts.Conn()


def _init(c):
    global _ready
    if not _ready:
        c.run("CREATE TABLE IF NOT EXISTS spend (day TEXT PRIMARY KEY, micro BIGINT NOT NULL)")
        _ready = True


def _today() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def _refresh(force=False):
    now = time.time()
    if not force and now - _cache["t"] < 20 and _cache["d"] == _today():
        return
    with _conn() as c:
        _init(c)
        tot = c.run("SELECT COALESCE(SUM(micro),0) AS s FROM spend")[0]["s"]
        day = c.run("SELECT micro FROM spend WHERE day=?", (_today(),))
    _cache.update(t=now, total=float(tot) / 1e6, day=(float(day[0]["micro"]) / 1e6 if day else 0.0), d=_today())


def check():
    """Raise BudgetExceeded when no budget is left."""
    with _lock:
        try:
            _refresh()
        except Exception:
            return  # never block users because the counter store hiccuped; the in-process cache still counts
        if _cache["total"] >= TOTAL_CAP or _cache["day"] >= DAILY_CAP:
            raise BudgetExceeded("AI budget reached")


def cost(model_is_strong: bool, tin: int, tout: int) -> float:
    pi, po = PRICES["ultra" if model_is_strong else "nano"]
    return (tin * pi + tout * po) / 1e6


def record(usd: float):
    micro = max(1, int(usd * 1e6))
    with _lock:
        _cache["total"] += usd
        _cache["day"] += usd
    try:
        with _conn() as c:
            _init(c)
            c.run(
                "INSERT INTO spend (day, micro) VALUES (?, ?) ON CONFLICT (day) DO UPDATE SET micro = spend.micro + EXCLUDED.micro",
                (_today(), micro),
            )
    except Exception:
        pass


def status() -> dict:
    try:
        _refresh(force=True)
    except Exception:
        pass
    return {"total_usd": round(_cache["total"], 4), "today_usd": round(_cache["day"], 4), "total_cap": TOTAL_CAP, "daily_cap": DAILY_CAP}
