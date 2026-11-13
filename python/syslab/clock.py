"""Injectable clocks.

Everything time-dependent takes a ``clock``: a zero-argument callable returning seconds as a
float. Production uses ``time.monotonic``; tests and demos use ``ManualClock`` so time only moves
when we say so, including backwards.
"""

from __future__ import annotations

import time
from collections.abc import Callable

Clock = Callable[[], float]

monotonic: Clock = time.monotonic


class ManualClock:
    """A clock that only moves when told to. ``set`` may go backwards (that is the point)."""

    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds

    def set(self, value: float) -> None:
        self._now = value


class SkewedClock:
    """Wraps a clock and adds an offset: the "NTP stepped the wall clock" switch.

    ``skew(+3600)`` jumps forward an hour, ``skew(-5)`` jumps back five seconds. Offsets add up.
    """

    def __init__(self, inner: Clock = monotonic) -> None:
        self._inner = inner
        self.offset = 0.0

    def __call__(self) -> float:
        return self._inner() + self.offset

    def skew(self, seconds: float) -> None:
        self.offset += seconds
