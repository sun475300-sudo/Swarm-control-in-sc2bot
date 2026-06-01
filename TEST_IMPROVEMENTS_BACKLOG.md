# SC2 Commander Bot — Test Improvements Backlog

> Generated: 2026-06-01 · Branch: `claude/cool-edison-GeBOL`
> Source: Live test runs identifying breakage on Python 3.11

## Cycle 1 Findings (Live Test Run)

Initial test run yielded:
- **376 passed**, **33 skipped**, **19 failed**
- Wicked-zerg-challenger directory: **23 collection errors** (missing `sc2` stub)
- Root tests: **1 collection error** (`test_queen_transfusion.py`)

## Priority Improvement List

### P0 — Test Breakage (blocks CI)

- [x] **#1** `tests/test_combat_phase_fsm.py` — replace 5 occurrences of `asyncio.get_event_loop().run_until_complete(...)` with `asyncio.run(...)`. Python 3.10+ deprecated implicit loop creation; raises `RuntimeError: There is no current event loop in thread 'MainThread'`. 12 tests recovered.
- [x] **#2** `tests/test_queen_transfusion.py` — guarded top-level `from sc2.ids.unit_typeid import UnitTypeId`. Wrap in try/except + `pytest.skip(allow_module_level=True)` so missing sc2 env doesn't break collection. 14 tests recovered.
- [x] **#3** `wicked_zerg_challenger/tests/test_production_resilience.py:388` — same deprecated `asyncio.get_event_loop()` pattern.
- [x] **#4** `wicked_zerg_challenger/tests/` — 23 modules unconditionally import sc2; built shared offline stub package at `tests/_sc2_stub/sc2/` (unit_typeid, upgrade_id, ability_id, position, unit, units, data, player, main, maps, game_info, bot_ai). Wired into both root and wicked conftest via sys.path fallback.

### P0.5 — Real Bot Bugs Surfaced By Tests

- [x] **#A** `wicked_zerg_challenger/unit_factory.py:91` — mojibake comment swallowed the `strategy = getattr(self.bot, "strategy_manager", None)` assignment (no newline between comment and code), so the function `_update_gas_ratio_target` raised `NameError: name 'strategy' is not defined` whenever it was called. 5 tests recovered.
- [x] **#B** `wicked_zerg_challenger/blackboard.py:540` — `should_expand()` ignored mineral availability. Added explicit 300-mineral hatchery cost check. 1 test recovered + improves bot behavior (no more spurious expansion attempts at low minerals).
- [x] **#C** `wicked_zerg_challenger/local_training/production_resilience.py` — `_get_counter_unit` did not validate that `enemy_units` was iterable, crashing on partial-state callers; added explicit `iter()` guard. Plus `_produce_army_unit` did not honor `_should_reserve_third_base_minerals()`, so larvae were spent on army units even when the 3rd base reserve was active. 1 test recovered + meaningful gameplay improvement.

### P1 — Environment Hygiene

- [ ] **#5** `tests/test_security.py` and `tests/test_crypto_trading.py` — fail with `pyo3_runtime.PanicException` due to missing `_cffi_backend`. Either install cffi in the test profile or `pytest.importorskip("cryptography")` at module top.
- [ ] **#6** Missing `pytest-asyncio` was implicit; add to `requirements-test.txt` or `pyproject.toml` extras.
- [ ] **#7** Pytest deprecation warning: bare `asyncio` mode in `pytest.ini`. Audit configuration for explicit `asyncio_mode = auto` block once asyncio fixes land.

### P2 — Bot Code Quality (post-test)

- [ ] **#8** Audit `wicked_zerg_challenger/` for remaining `asyncio.get_event_loop()` outside tests.
- [ ] **#9** Audit other mojibake-broken comment+code joined lines (3 known visual cases that don't break behavior: `dynamic_resource_balancer.py:175`, `unit_factory.py:167`, `unit_factory.py:216`).
- [ ] **#10** Verify `tests/conftest.py` doesn't shadow `wicked_zerg_challenger/tests` fixtures.

## Cycle 2 Findings (Silent-no-op Async Tests)

Running with warnings exposed: pytest reported **38 warnings** including `coroutine '...' was never awaited` for **18 test methods** that appeared to pass but were actually skipped silently (unittest.TestCase doesn't await async test methods). Two classes were affected.

### P0.6 — Silent-no-op Tests & Real Bug Surfaced

- [x] **#D** `wicked_zerg_challenger/tests/test_production_resilience.py` — `TestProductionResilience` inherited from `unittest.TestCase`; 9 `async def test_*` methods were never awaited. Converted to `unittest.IsolatedAsyncioTestCase`. 3 broken `test_get_counter_unit_*` tests called a sync method with `await` and the wrong signature (`"Terran"` as positional arg for `enemy_units` instead of a list + 3 tech bool flags); rewrote them to construct realistic enemy unit mocks and call the real signature.
- [x] **#E** `wicked_zerg_challenger/tests/test_opponent_modeling.py` — `TestOpponentModeling` same problem; 9 `async def test_*` methods silently no-op'd. Converted to `IsolatedAsyncioTestCase`. Surfaced **#F**.
- [x] **#F** `wicked_zerg_challenger/opponent_modeling.py` — duplicate `async def on_step` defined twice in the same class. The second (lines 765–774) silently overrode the first and referenced `self.current_opponent`, an attribute that was never initialized in `__init__` (only `self.current_opponent_id` was). Any call to `on_step()` before `on_game_start()` (i.e. when `on_start()` was used instead) crashed with `AttributeError: 'OpponentModeling' object has no attribute 'current_opponent'`. Deleted the duplicate `on_step` so the proper async implementation wins. Unified `on_game_start`/`on_game_end`/`get_predicted_strategy` to use `current_opponent_id` for consistency.

### P0.7 — Environment Polish

- [x] **#G** Installed `pytest-timeout` (the pytest.ini `timeout = 60` was warning `Unknown config option`).

## Status

| Cycle | Date       | Improvements applied                            | Tests passed | Warnings |
|-------|------------|-------------------------------------------------|--------------|----------|
| 1     | 2026-06-01 | #1, #2, #3, #4, #A, #B, #C                      | **1155** (was 376) | 38 |
| 2     | 2026-06-01 | #D, #E, #F, #G — 18 silent no-op tests recovered | **1155** (same count, but 18 are now real) | 1 |
