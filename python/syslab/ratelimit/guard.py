"""Fail-open vs fail-closed: what the caller sees when the limiter itself breaks.

A real limiter often depends on a shared store (Redis, a DB). When that store is down the limiter
raises, and *something* has to decide. ``GuardedLimiter`` makes that decision explicit.
"""

from __future__ import annotations

import enum
from typing import Protocol


class FailPolicy(enum.Enum):
    OPEN = "open"  # limiter broken -> let traffic through (availability over protection)
    CLOSED = "closed"  # limiter broken -> reject traffic (protection over availability)


class _Limiter(Protocol):
    def allow(self) -> bool: ...


class GuardedLimiter:
    def __init__(self, inner: _Limiter, policy: FailPolicy) -> None:
        self.inner = inner
        self.policy = policy
        self.errors = 0

    def allow(self) -> bool:
        try:
            return self.inner.allow()
        except Exception:
            self.errors += 1
            return self.policy is FailPolicy.OPEN


class FlakyLimiter:
    """Test double with an outage switch: set ``down = True`` and ``allow`` raises."""

    def __init__(self, inner: _Limiter) -> None:
        self.inner = inner
        self.down = False

    def allow(self) -> bool:
        if self.down:
            raise ConnectionError("limiter backend unavailable")
        return self.inner.allow()
