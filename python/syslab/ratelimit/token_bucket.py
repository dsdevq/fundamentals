"""Token bucket: allows bursts up to ``capacity``, sustained rate ``refill_rate`` per second.

State is two numbers (tokens, last refill time). Refill is computed lazily on each call from the
elapsed time, so there is no timer thread. O(1) time and memory.
"""

from __future__ import annotations

import threading

from syslab.clock import Clock, monotonic


class TokenBucket:
    def __init__(self, capacity: float, refill_rate: float, clock: Clock = monotonic) -> None:
        if capacity < 0:
            raise ValueError("capacity must be >= 0")
        if refill_rate < 0:
            raise ValueError("refill_rate must be >= 0")
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._clock = clock
        self._tokens = float(capacity)  # starts full: the first burst is allowed
        self._last = clock()
        self._lock = threading.Lock()

    def allow(self, cost: float = 1.0) -> bool:
        """Take ``cost`` tokens if available. Never blocks."""
        with self._lock:
            self._refill()
            if cost > self._tokens:
                return False
            self._tokens -= cost
            return True

    @property
    def tokens(self) -> float:
        with self._lock:
            self._refill()
            return self._tokens

    def retry_after(self, cost: float = 1.0) -> float:
        """Seconds until ``cost`` tokens will be available (``inf`` if they never will be)."""
        with self._lock:
            self._refill()
            missing = cost - self._tokens
            if missing <= 0:
                return 0.0
            if cost > self.capacity or self.refill_rate == 0:
                return float("inf")
            return missing / self.refill_rate

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._last
        if elapsed < 0:
            # Clock went backwards. Grant nothing for this call and re-anchor at the new time,
            # so we neither freeze until the old time is reached nor double-count that span.
            self._last = now
            return
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
        self._last = now
