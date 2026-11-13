"""Failure-injection variants of ``LRUCache``. Each one is a single-method bug.

They exist so you can flip a switch and watch a plausible-looking bug hurt (see the tests and
``demos/cache_demo.py``). Do not use them for anything else.
"""

from __future__ import annotations

from syslab.cache.lru import LRUCache


class EvictsMostRecent[K, V](LRUCache[K, V]):
    """Evicts the *newest* entry instead of the oldest.

    Looks fine on a trace with no reuse, then the hot key you just wrote is the first to go and
    the hit rate collapses to roughly zero on any loop slightly bigger than the cache.
    """

    def _pick_victim(self) -> K:
        return next(reversed(self._data))


class ForgetsToTouch[K, V](LRUCache[K, V]):
    """``get`` does not refresh recency, so this is really a FIFO cache.

    The classic "I forgot move_to_end" bug: hot keys get evicted on schedule as if cold.
    """

    def _touch(self, key: K) -> None:
        return None
