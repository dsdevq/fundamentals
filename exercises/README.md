# Exercises: hand-written rate limiter and LRU/TTL cache

Owner decision D4a (2026-11-13): a rate limiter and an LRU/TTL cache, written from scratch by the owner. Due 2026-11-30. Python only.

## The rule

- **AI reviews, never writes it.** No AI-generated solution code goes in this folder. Review comments, questions and test ideas are fine.
- The agent-built lab under `../python/` is for studying and breaking, not copying.
- This folder starts empty on purpose. The only content is this README, the pytest setup and test skeletons that describe the interface in comments.

## Layout

- `pyproject.toml`: pytest config.
- `tests/test_rate_limiter.py`: skeleton for the rate limiter.
- `tests/test_lru_ttl_cache.py`: skeleton for the LRU/TTL cache.

Put your implementation modules next to `tests/` (for example `rate_limiter.py`, `cache.py`). `pythonpath` is set to this folder, so tests can import them directly.

## Running

```
cd exercises
pip install pytest
pytest
```

The skeleton tests are skipped until you remove the `skip` marks and write them.
