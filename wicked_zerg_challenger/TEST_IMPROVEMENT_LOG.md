# SC2 Commander Bot - Test & Improvement Iteration Log

Continuous test-and-fix loop. Issues found via test suite and code inspection.

## Iteration 1 - Test Suite Bring-up

### Environment fixes
- Installed missing runtime deps (`loguru`, `scipy`) and `burnysc2 --no-deps`.
- `conftest.py` already sets `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` for tests.

### Bugs fixed
1. **blackboard.py — `should_expand()` ignored mineral cost** (failing test `test_should_not_expand_low_minerals`)
   - Added `min_minerals` threshold (default 300, Hatchery cost) so we don't claim we can expand on <100 minerals.

2. **unit_factory.py — corrupted Korean comment swallowed `strategy = …` assignment** (5 failing tests in `TestGasRatioTarget`)
   - Mojibake bytes on line 91 produced no newline before the assignment, so the entire `strategy = getattr(...)` line was part of the comment and `strategy` was never defined.
   - Rewrote the comment in clean ASCII and restored the assignment on its own line.

3. **local_training/production_resilience.py — `_get_counter_unit` crashes on non-iterable `enemy_units`** (Mock-based test)
   - Added `try: iter(enemy_units)` guard before the loop.

4. **local_training/production_resilience.py — third-base reserve did not gate larva spending in `_produce_army_unit`** (failing test)
   - After the min-defense check passes, return False if `_should_reserve_third_base_minerals()` is active so larvae are held for the next Hatchery instead of being burned on extra zerglings.

### Results
- Before: 7 failing tests + 3 collection errors (642 collected, 1 file completely uncollectable).
- After: **659 passing, 0 failing.** `test_sprint8_qa.py` still uncollectable due to missing `mpyq` (native build deps required — environment limitation, not bot bug).
