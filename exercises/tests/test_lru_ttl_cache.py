"""Skeleton tests for the hand-written LRU/TTL cache. No solution code here."""

import pytest

# Interface the exercise needs (describe only; implement it yourself):
#
#   get(key, now) -> value or a miss marker
#     - a hit makes the key most recently used
#     - an expired entry counts as a miss
#   set(key, value, now, ttl=None)
#     - inserts or overwrites; ttl is in seconds, None means no expiry
#   ttl(key, now) -> remaining seconds, or a marker for missing / no expiry
#   eviction
#     - when over capacity, evict the least recently used entry
#     - expired entries should go before live ones
#
# Time is passed in as `now` so tests are deterministic.

SKIP = pytest.mark.skip(reason="exercise: write this test yourself")


@SKIP
def test_get_miss_then_hit():
    pass


@SKIP
def test_overwrite_updates_value():
    pass


@SKIP
def test_ttl_expiry():
    pass


@SKIP
def test_ttl_reports_remaining():
    pass


@SKIP
def test_evicts_least_recently_used():
    pass


@SKIP
def test_get_refreshes_recency():
    pass
