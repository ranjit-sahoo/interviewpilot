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
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown")


def rate_limit(request: Request):
    if not limiter.check(client_key(request)):
        raise HTTPException(429, "Too many requests. Please wait a minute and try again.")
