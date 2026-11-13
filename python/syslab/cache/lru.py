"""LRU cache with optional per-entry TTL.

Data structure: one ``OrderedDict`` (hash map + doubly linked list). Most recently used entries
live at the right end, the eviction victim is the left end. get/put are O(1).

Expiry is lazy: an expired entry is only noticed (and removed) when someone touches it, or when
it reaches the LRU end and is evicted anyway. There is no background sweeper, so a cache full of
dead entries still *occupies* capacity until they are read or pushed out. See README.md.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import Callable, Hashable
from typing import Any

from syslab.clock import Clock, monotonic

_MISSING: Any = object()


class LRUCache[K: Hashable, V]:
    """Fixed-capacity LRU cache. ``capacity=0`` is legal and stores nothing.

    ``ttl`` is the default lifetime in seconds (``None`` = forever); ``put`` can override it per
    entry. An entry written at time ``t`` with ttl ``d`` is alive for ``now < t + d`` and
    expired at ``now >= t + d`` (the boundary instant is already expired).
    """

    def __init__(
        self,
        capacity: int,
        ttl: float | None = None,
        clock: Clock = monotonic,
    ) -> None:
        if capacity < 0:
            raise ValueError("capacity must be >= 0")
        if ttl is not None and ttl <= 0:
            raise ValueError("ttl must be > 0 or None")
        self.capacity = capacity
        self.ttl = ttl
        self._clock = clock
        # key -> (value, expires_at or None)
        self._data: OrderedDict[K, tuple[V, float | None]] = OrderedDict()
        self._lock = threading.RLock()
        self._inflight: dict[K, _Flight[V]] = {}
        self.hits = self.misses = self.evictions = self.expirations = 0

    # -- public API -------------------------------------------------------------------------

    def get(self, key: K, default: V | None = None) -> V | None:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                self.misses += 1
                return default
            value, expires_at = entry
            if expires_at is not None and self._clock() >= expires_at:
                del self._data[key]
                self.expirations += 1
                self.misses += 1
                return default
            self._touch(key)
            self.hits += 1
            return value

    def put(self, key: K, value: V, ttl: float | None = _MISSING) -> None:
        """Insert or overwrite. Overwriting refreshes both recency and TTL."""
        if ttl is _MISSING:
            ttl = self.ttl
        elif ttl is not None and ttl <= 0:
            raise ValueError("ttl must be > 0 or None")
        if self.capacity == 0:
            return
        with self._lock:
            expires_at = None if ttl is None else self._clock() + ttl
            if key in self._data:
                self._data[key] = (value, expires_at)
                self._touch(key)
                return
            while len(self._data) >= self.capacity:
                self._evict_one()
            self._data[key] = (value, expires_at)

    def delete(self, key: K) -> bool:
        with self._lock:
            return self._data.pop(key, None) is not None

    def __len__(self) -> int:
        """Number of stored entries, *including* expired ones nobody has touched yet."""
        with self._lock:
            return len(self._data)

    def __contains__(self, key: K) -> bool:
        """Liveness check that does not change recency."""
        with self._lock:
            entry = self._data.get(key)
            return entry is not None and not self._is_expired(entry[1])

    def purge_expired(self) -> int:
        """Eager sweep, O(n). Call it from a timer if dead entries hurt you."""
        with self._lock:
            dead = [k for k, (_, exp) in self._data.items() if self._is_expired(exp)]
            for k in dead:
                del self._data[k]
            self.expirations += len(dead)
            return len(dead)

    def get_or_load(
        self,
        key: K,
        loader: Callable[[K], V],
        single_flight: bool = True,
    ) -> V:
        """Read-through. On a miss, call ``loader(key)`` and cache the result.

        With ``single_flight=True`` concurrent misses for one key share a single loader call.
        With ``False`` every concurrent miss calls the loader: the thundering herd.
        """
        value = self.get(key, _MISSING)
        if value is not _MISSING:
            return value
        if not single_flight:
            value = loader(key)
            self.put(key, value)
            return value

        with self._lock:
            flight = self._inflight.get(key)
            leader = flight is None
            if leader:
                flight = self._inflight[key] = _Flight()
        if not leader:
            flight.done.wait()
            if flight.error is not None:
                raise flight.error
            return flight.value
        try:
            flight.value = loader(key)
            self.put(key, flight.value)
            return flight.value
        except BaseException as exc:
            flight.error = exc
            raise
        finally:
            with self._lock:
                del self._inflight[key]
            flight.done.set()

    # -- internals (the fault-injection subclasses override these) ---------------------------

    def _touch(self, key: K) -> None:
        """Mark ``key`` most recently used."""
        self._data.move_to_end(key)

    def _pick_victim(self) -> K:
        """Choose the key to evict. LRU = the oldest entry = the left end."""
        return next(iter(self._data))

    def _evict_one(self) -> None:
        del self._data[self._pick_victim()]
        self.evictions += 1

    def _is_expired(self, expires_at: float | None) -> bool:
        return expires_at is not None and self._clock() >= expires_at


class _Flight[V]:
    def __init__(self) -> None:
        self.done = threading.Event()
        self.value: V = _MISSING
        self.error: BaseException | None = None
