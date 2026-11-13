# Python systems lab

Small reference implementations of classic interview systems, written to be read, broken and
reasoned about. Standard library only at runtime. Python 3.12+.

| Part | Code | Notes |
|---|---|---|
| LRU cache with per-entry TTL | `syslab/cache/` | [README](syslab/cache/README.md) |
| Token bucket + sliding-window rate limiters | `syslab/ratelimit/` | [README](syslab/ratelimit/README.md) |

Next milestone (not here yet): retry with backoff, idempotent job queue.

## Setup

```sh
cd python
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"      # installs pytest and ruff
pytest                       # tests
ruff check . && ruff format --check .
python benchmarks/bench_cache.py
python benchmarks/bench_ratelimit.py
python demos/cache_demo.py --switch wrong-victim      # failure switches, see part READMEs
python demos/ratelimit_demo.py --switch outage --fail closed
```

## Layout

- `syslab/clock.py` - the injectable clock. Every time-dependent class takes `clock=`.
  `ManualClock` (moves only when told, can go backwards) and `SkewedClock` (offset switch).
- `tests/` - edge cases: capacity 0 and 1, TTL boundary, refill and burst, clock going backwards.
- `benchmarks/` - micro-benchmarks that print results. Absolute numbers depend on the machine;
  compare the rows to each other, not to anyone else's table.
- `demos/` - one command per failure switch.

## How to study this

For each part: read the README, predict what a switch will do, run it, then read the test that
pins the behaviour. The interesting questions are in the "Trade-offs" and "Failure modes"
sections.
