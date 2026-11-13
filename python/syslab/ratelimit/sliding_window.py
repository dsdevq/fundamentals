"""Sliding-window-log limiter: at most ``limit`` requests in any ``window`` seconds. Exact.

State is the timestamps of the accepted requests inside the window, so memory is O(limit) per
limiter. Compare with a fixed window counter (O(1), but allows 2x ``limit`` across a boundary)
and with the sliding-window *counter* approximation (O(1), slightly inexact); see README.md.
"""

from __future__ import annotations

import threading
from collections import deque

from syslab.clock import Clock, monotonic


class SlidingWindowLimiter:
    def __init__(self, limit: int, window: float, clock: Clock = monotonic) -> None:
        if limit < 0:
            raise ValueError("limit must be >= 0")
        if window <= 0:
            raise ValueError("window must be > 0")
        self.limit = limit
        self.window = window
        self._clock = clock
        self._stamps: deque[float] = deque()  # accepted request times, oldest first
        self._latest = float("-inf")
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            now = self._now()
            self._expire(now)
            if len(self._stamps) >= self.limit:
                return False
            self._stamps.append(now)
            return True

    def retry_after(self) -> float:
        """Seconds until a request would be accepted (``inf`` if limit is 0)."""
        with self._lock:
            now = self._now()
            self._expire(now)
            if len(self._stamps) < self.limit:
                return 0.0
            if not self._stamps:  # limit == 0
                return float("inf")
            return self._stamps[0] + self.window - now

    def _now(self) -> float:
        # Never let time go backwards for our own bookkeeping: the deque must stay sorted.
        # Consequence: after a backwards jump, time is frozen until the clock catches up, so the
        # limiter gets stricter, never looser.
        self._latest = max(self._latest, self._clock())
        return self._latest

    def _expire(self, now: float) -> None:
        # A request made at t leaves the window at t + window exactly (boundary is "out").
        while self._stamps and now - self._stamps[0] >= self.window:
            self._stamps.popleft()
