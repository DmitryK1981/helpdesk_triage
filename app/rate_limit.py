import time
import threading
from collections import defaultdict, deque


class RateLimiter:
    """In-memory sliding-window limiter, keyed by client_id.

    Single-process only: fine for a local MVP demo, won't hold across
    multiple workers/instances.
    """

    def __init__(self, limit_per_minute: int, window_seconds: float = 60.0):
        self.limit = limit_per_minute
        self.window = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, client_id: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[client_id]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True
