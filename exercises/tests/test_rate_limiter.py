"""Skeleton tests for the hand-written rate limiter. No solution code here."""

import pytest

# Interface the exercise needs (describe only; implement it yourself):
#
#   allow(key, now) -> bool
#     - key: identifies the caller being limited
#     - now: current time passed in by the caller (no hidden clock, so tests are deterministic)
#     - returns True if the request is admitted, False if it is rejected
#
# Decide and document: algorithm (token bucket, sliding window, ...), limit, window/refill
# rate, what happens with time going backwards, and how idle keys are cleaned up.

SKIP = pytest.mark.skip(reason="exercise: write this test yourself")


@SKIP
def test_allows_up_to_limit():
    pass


@SKIP
def test_rejects_over_limit():
    pass


@SKIP
def test_keys_are_independent():
    pass


@SKIP
def test_recovers_after_window():
    pass
