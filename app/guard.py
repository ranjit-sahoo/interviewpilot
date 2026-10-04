"""Small in-memory per-client rate limiter (sliding window)."""
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, limit: int, window: float):
        self.limit, self.window = limit, window
        self.hits = defaultdict(deque)
        self.lock = threading.Lock()

    def check(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        with self.lock:
            q = self.hits[key]
            while q and q[0] <= now - self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            if len(self.hits) > 5000:  # bound memory
                for k in [k for k, v in self.hits.items() if not v or v[-1] <= now - self.window]:
                    del self.hits[k]
            return True


import os

limiter = RateLimiter(limit=int(os.environ.get("RATE_LIMIT_PER_MIN", "60")), window=60.0)


def client_key(request: Request) -> str:
    """Real client IP. The first X-Forwarded-For entry is client-supplied (spoofable), so prefer the
    CDN-set header and otherwise take the entry the platform proxy appended."""
    cf = request.headers.get("cf-connecting-ip", "").strip()
    if cf:
        return cf
    parts = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    if len(parts) >= 3:
        return parts[-3]
    if parts:
        return parts[-1]
    return request.client.host if request.client else "unknown"


# Anonymous abuse cap: each POST can trigger a paid model call, so cap them per client per day.
daily = RateLimiter(limit=int(os.environ.get("AI_DAILY_PER_IP", "250")), window=86400.0)


def rate_limit(request: Request):
    key = client_key(request)
    if not limiter.check(key):
        raise HTTPException(429, "Too many requests. Please wait a minute and try again.")
    if request.method == "POST" and not daily.check(key):
        raise HTTPException(429, "Daily free usage limit reached for this network. Please come back tomorrow.")


class FailLimiter:
    """Counts failures per key (e.g. an account) and blocks after `limit` within `window` seconds."""

    def __init__(self, limit: int, window: float):
        self.limit, self.window = limit, window
        self.hits = defaultdict(deque)
        self.lock = threading.Lock()

    def _prune(self, q, now):
        while q and q[0] <= now - self.window:
            q.popleft()

    def blocked(self, key: str) -> bool:
        now = time.monotonic()
        with self.lock:
            q = self.hits.get(key)
            if q is None:
                return False
            self._prune(q, now)
            return len(q) >= self.limit

    def fail(self, key: str):
        now = time.monotonic()
        with self.lock:
            q = self.hits[key]
            self._prune(q, now)
            q.append(now)
            if len(self.hits) > 5000:
                for k in [k for k, v in self.hits.items() if not v or v[-1] <= now - self.window]:
                    del self.hits[k]
