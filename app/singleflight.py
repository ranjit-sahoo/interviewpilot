"""Per-key lock: identical lookups wait for the first one instead of repeating the same AI call."""
import threading
from contextlib import contextmanager

_guard = threading.Lock()
_locks: dict = {}


@contextmanager
def lock(key):
    with _guard:
        entry = _locks.setdefault(key, [threading.Lock(), 0])
        entry[1] += 1
    try:
        with entry[0]:
            yield
    finally:
        with _guard:
            entry[1] -= 1
            if entry[1] <= 0:
                _locks.pop(key, None)
