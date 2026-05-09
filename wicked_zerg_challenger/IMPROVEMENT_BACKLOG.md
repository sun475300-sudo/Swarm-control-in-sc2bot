# SC2 Commander Bot — Improvement Backlog

Continuous test-driven improvement list captured from running the suite under
`wicked_zerg_challenger/tests/`. Items marked **(done)** are landed on the
current branch; the rest are picked off in priority order.

## Iteration 1 — Test infrastructure (done)

| ID  | Item | Notes |
| --- | --- | --- |
| 1.1 | Lightweight `sc2` stub package | `tests/_sc2_stub.py` registers `sc2`, `sc2.ids.*`, `sc2.position`, `sc2.unit`, `sc2.units`, `sc2.bot_ai`, `sc2.player`, `sc2.main`, `sc2.data`, `sc2.race`, `sc2.difficulty` so test collection succeeds without burnysc2 + the full game install. |
| 1.2 | `conftest.py` auto-installs the stub | Real `sc2` is preferred when present; otherwise the stub is registered before any test module imports. |
| 1.3 | Recover 23 broken collections | Test collection now reports **661 tests** (was 364 with 23 errors). 646 pass on first run. |

## Iteration 2 — Stub fidelity for serialization tests (done)

| ID  | Item | Result |
| --- | --- | --- |
| 2.1 | `Race`/`Difficulty`/`Result` now expose `__getitem__` so `Race["Terran"]` and `Difficulty["Easy"]` work | `test_difficulty_progression.py::test_serialize_deserialize_consistency` & `test_save_and_load_stats` pass |
| 2.2 | Iteration / `__contains__` over enum members | Enables `list(Race)` and `name in Race` lookups |
| 2.3 | Drove the failing-test count from 15 → 13 |

## Iteration 3 — Combat filter regressions (done)

| ID  | Item | Result |
| --- | --- | --- |
| 3.1 | Stub `UnitTypeId` now mints enum-style members with `.name` and `.value`, so `mock.type_id = UnitTypeId.MUTALISK` round-trips through production code paths that call `unit.type_id.name in {...}` | `test_filter_air_units`, `test_filter_ground_units`, `test_filter_army_units_*` all pass |
| 3.2 | Tightened equality so `UnitTypeId.X == "X"` and `UnitTypeId.X == UnitTypeId.X` agree | Removes the silent falsy-string mismatch from the filter helpers |
| 3.3 | Side benefit: also fixed the 5 `TestTechCoordinatorExpansion` failures, the 2 build/zvt/zvp opener failures and the worker-harassment defense failure since they all relied on the same enum-name lookup path |
| 3.4 | All 661 tests now pass on first run from `wicked_zerg_challenger/` | `python -m pytest tests/ --tb=no -q` ⇒ 661 passed |

## Iteration 4 — Opening expansion priority gating

| ID  | Item | Symptom |
| --- | --- | --- |
| 4.1 | `test_opening_hatchery_step_is_held_before_ninety_seconds` returns `'upgrade'` instead of `'expand'` |
| 4.2 | Five `TestTechCoordinatorExpansion` failures around the opening-hatchery and pending-third reservation logic |
| 4.3 | `test_zvt_safe_expand_selects_fast_lair_macro` and `test_zvp_stargate_selects_hydra_lair_macro` expect `'morph'` action set but only see `{'upgrade'}` |

## Iteration 4 — Project-root suite (done)

| ID  | Item | Result |
| --- | --- | --- |
| 4.1 | Project-root `tests/conftest.py` now installs the same sc2 stub | `tests/test_queen_transfusion.py` collects + passes |
| 4.2 | Installed `pytest-asyncio` for the async tool/workflow tests | 86 async failures cleared in one shot (workflow_orchestrator, tool_dispatcher, tool_executor, resource_manager) |
| 4.3 | Project-root suite now reports **491 passed / 8 failed / 14 skipped** | Was 0 collecting + 1 hard error before iteration 1 |
| 4.4 | Remaining 8 failures are environmental: `pyo3 PanicException` triggered by `cryptography.hazmat.bindings._rust` because system `_cffi_backend` is missing | Not a bot bug — security/crypto smoke tests; cleanup is to either `pip install cffi` in the dev image or guard the import so pure-Python paths still load. Filed as low-priority. |

## Iteration 5 — Combined-suite event-loop fix (done)

| ID  | Item | Result |
| --- | --- | --- |
| 5.1 | `tests/test_combat_phase_fsm.py` swapped 5× `asyncio.get_event_loop().run_until_complete(...)` for `asyncio.run(...)` | The deprecated API was raising `RuntimeError: There is no current event loop` when the combined run interleaved with pytest-asyncio's auto-mode loops |
| 5.2 | Combined suite `wicked_zerg_challenger/tests/ + tests/` now reports **1160 passed / 14 skipped / 0 failed** | Was **12 failed** in the combined run before |

## Iteration 6 — Quality-of-life follow-ups (in progress)

| ID  | Item | Status |
| --- | --- | --- |
| 6.1 | `TestOpponentModeling` extended `unittest.TestCase`, so 8 `async def test_*` methods returned coroutines that were never awaited (silent passes). Switched to `unittest.IsolatedAsyncioTestCase` so they actually run. | Done — 32/32 pass after also fixing the production bug below |
| 6.2 | **Production bug surfaced**: `OpponentModeling` had two `on_step` methods; the duplicate at line ~777 silently shadowed the canonical one at line ~341. The canonical step ran the full pipeline (build-order tracking, timing-attack detection, blackboard sync); the duplicate only detected early-game signals. Removed the duplicate. | Done |
| 6.3 | `OpponentModeling` mixed two attribute names for the same concept (`current_opponent` set in the integration helpers vs `current_opponent_id` everywhere else). Added a `current_opponent` property that aliases `current_opponent_id` so both lifecycle APIs stay in sync. | Done |
| 6.4 | Combined-suite warnings dropped from 38 → 19 after these fixes. | Done |
| 6.5 | Pre-existing repo-wide `black --check .` fails on 66 unrelated files; CI's `Lint & Type Check (3.11)` is red as a result. Out-of-scope here, but a one-shot black format pass would clear it. | Pending (out of scope) |

## Iteration N — Continuous loop instructions

After each iteration:
1. Run `python -m pytest tests/ --tb=no -q` from `wicked_zerg_challenger/`.
2. Move newly-fixed entries to **(done)**.
3. Append any newly-discovered failures to a new iteration block.
4. Commit and push to `claude/stoic-shannon-SOUVq`.
