import threading

import pytest

from syslab.cache import LRUCache
from syslab.cache.faults import EvictsMostRecent, ForgetsToTouch
from syslab.clock import ManualClock


def test_basic_get_put_and_miss_default():
    c = LRUCache[str, int](2)
    c.put("a", 1)
    assert c.get("a") == 1
    assert c.get("zzz") is None
    assert c.get("zzz", -1) == -1


def test_evicts_least_recently_used():
    c = LRUCache[str, int](2)
    c.put("a", 1)
    c.put("b", 2)
    c.get("a")  # a is now newer than b
    c.put("c", 3)
    assert "b" not in c
    assert c.get("a") == 1 and c.get("c") == 3
    assert c.evictions == 1


def test_overwrite_refreshes_recency_and_does_not_evict():
    c = LRUCache[str, int](2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("a", 10)
    assert c.evictions == 0
    c.put("c", 3)  # evicts b, not a
    assert c.get("a") == 10 and "b" not in c


def test_capacity_zero_stores_nothing():
    c = LRUCache[str, int](0)
    c.put("a", 1)
    assert len(c) == 0 and c.get("a") is None and c.evictions == 0


def test_capacity_one_keeps_only_latest():
    c = LRUCache[str, int](1)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") is None and c.get("b") == 2
    c.put("b", 3)
    assert c.get("b") == 3 and c.evictions == 1


def test_negative_capacity_and_bad_ttl_rejected():
    with pytest.raises(ValueError):
        LRUCache(-1)
    with pytest.raises(ValueError):
        LRUCache(1, ttl=0)
    with pytest.raises(ValueError):
        LRUCache(1).put("a", 1, ttl=-1)


def test_ttl_boundary_alive_just_before_expired_exactly_at():
    clock = ManualClock()
    c = LRUCache[str, int](2, ttl=10, clock=clock)
    c.put("a", 1)
    clock.set(9.999)
    assert c.get("a") == 1
    clock.set(10)  # t + ttl exactly: already expired
    assert c.get("a") is None
    assert c.expirations == 1 and len(c) == 0


def test_per_entry_ttl_overrides_default_and_none_means_forever():
    clock = ManualClock()
    c = LRUCache[str, int](3, ttl=10, clock=clock)
    c.put("short", 1, ttl=1)
    c.put("default", 2)
    c.put("forever", 3, ttl=None)
    clock.set(5)
    assert c.get("short") is None
    assert c.get("default") == 2
    clock.set(1_000_000)
    assert c.get("default") is None
    assert c.get("forever") == 3


def test_get_does_not_extend_ttl_but_put_does():
    clock = ManualClock()
    c = LRUCache[str, int](2, ttl=10, clock=clock)
    c.put("a", 1)
    clock.set(8)
    assert c.get("a") == 1  # reading is not renewal
    clock.set(10)
    assert c.get("a") is None
    c.put("a", 1)
    clock.set(18)
    c.put("a", 2)  # overwrite renews
    clock.set(27)
    assert c.get("a") == 2


def test_expired_entries_occupy_capacity_until_touched_or_purged():
    clock = ManualClock()
    c = LRUCache[str, int](2, ttl=1, clock=clock)
    c.put("a", 1)
    c.put("b", 2)
    clock.set(5)
    assert len(c) == 2  # lazy expiry: dead but still stored
    assert c.purge_expired() == 2
    assert len(c) == 0


def test_contains_respects_ttl_and_does_not_change_recency():
    clock = ManualClock()
    c = LRUCache[str, int](2, ttl=10, clock=clock)
    c.put("a", 1)
    c.put("b", 2)
    assert "a" in c  # must not refresh a
    c.put("c", 3)
    assert "a" not in c  # a was still the LRU victim
    clock.set(10)
    assert "b" not in c


def test_clock_going_backwards_extends_lifetime_documented_behaviour():
    clock = ManualClock(100)
    c = LRUCache[str, int](1, ttl=10, clock=clock)
    c.put("a", 1)  # expires at 110
    clock.set(50)  # clock stepped back 50s
    clock.set(109)
    assert c.get("a") == 1  # it has really lived 59s, with a 10s ttl
    clock.set(110)
    assert c.get("a") is None


def test_delete():
    c = LRUCache[str, int](2)
    c.put("a", 1)
    assert c.delete("a") is True
    assert c.delete("a") is False


# -- fault-injection variants ---------------------------------------------------------------


def test_evicts_most_recent_variant_loses_the_hot_key():
    good, bad = LRUCache[str, int](2), EvictsMostRecent[str, int](2)
    for c in (good, bad):
        c.put("old", 1)
        c.put("hot", 2)
        c.get("hot")
        c.put("new", 3)
    assert good.get("hot") == 2 and good.get("old") is None
    assert bad.get("hot") is None and bad.get("old") == 1  # the hot key was the victim


def test_forgets_to_touch_variant_is_fifo():
    c = ForgetsToTouch[str, int](2)
    c.put("a", 1)
    c.put("b", 2)
    c.get("a")  # should protect a, does not
    c.put("c", 3)
    assert c.get("a") is None


# -- get_or_load / thundering herd ----------------------------------------------------------


def _herd(single_flight: bool, n: int = 8) -> int:
    cache = LRUCache[str, int](4)
    calls = 0
    count_lock = threading.Lock()
    release = threading.Event()
    barrier = threading.Barrier(n)

    def loader(key: str) -> int:
        nonlocal calls
        with count_lock:
            calls += 1
        release.wait(timeout=2)
        return 42

    results: list[int] = []

    def worker() -> None:
        barrier.wait()
        results.append(cache.get_or_load("k", loader, single_flight=single_flight))

    threads = [threading.Thread(target=worker) for _ in range(n)]
    for t in threads:
        t.start()
    # Let every thread reach its miss before the "slow backend" answers.
    threading.Event().wait(0.3)
    release.set()
    for t in threads:
        t.join()
    assert results == [42] * n
    return calls


def test_single_flight_collapses_concurrent_misses_to_one_load():
    assert _herd(single_flight=True) == 1


def test_without_single_flight_every_concurrent_miss_hits_the_backend():
    assert _herd(single_flight=False) > 1


def test_loader_error_propagates_to_waiters_and_is_not_cached():
    cache = LRUCache[str, int](2)

    def boom(key: str) -> int:
        raise RuntimeError("backend down")

    with pytest.raises(RuntimeError):
        cache.get_or_load("k", boom)
    assert cache.get_or_load("k", lambda k: 7) == 7  # next caller retries
