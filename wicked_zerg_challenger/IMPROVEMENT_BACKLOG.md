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

## Iteration 6 — Silent-async-test cleanup (done)

| ID  | Item | Status |
| --- | --- | --- |
| 6.1 | `TestOpponentModeling` extended `unittest.TestCase`, so 8 `async def test_*` methods returned coroutines that were never awaited (silent passes). Switched to `unittest.IsolatedAsyncioTestCase` so they actually run. | Done — 32/32 pass after also fixing the production bug below |
| 6.2 | **Production bug surfaced**: `OpponentModeling` had two `on_step` methods; the duplicate at line ~777 silently shadowed the canonical one at line ~341. The canonical step ran the full pipeline (build-order tracking, timing-attack detection, blackboard sync); the duplicate only detected early-game signals. Removed the duplicate. | Done |
| 6.3 | `OpponentModeling` mixed two attribute names for the same concept (`current_opponent` set in the integration helpers vs `current_opponent_id` everywhere else). Added a `current_opponent` property that aliases `current_opponent_id` so both lifecycle APIs stay in sync. | Done |
| 6.4 | `TestProductionResilience` had the same silent-async issue. Switched the base class. The newly-running tests then exposed three counter-unit tests calling an obsolete `_get_counter_unit("Terran")` signature. The real method now takes `(enemy_units, has_roach_warren, has_hydra_den, has_spire)`. Rewrote those three tests against the current API, covering armored-ground, air, and empty-enemies branches. | Done |
| 6.5 | Combined-suite warnings dropped 38 → **1**, and the suite now exercises 22 test cases that used to be silently skipped. | Done |
| 6.6 | Pre-existing repo-wide `black --check .` fails on 66 unrelated files; CI's `Lint & Type Check (3.11)` is red as a result. Out-of-scope here, but a one-shot black format pass would clear it. | Pending (out of scope) |

## Iteration 7 — Shadowed-method scan (in progress)

A small AST scan (`ast.walk` over `ClassDef.body`) found four classes with two
`def` for the same name. Python keeps the *last* definition, so the first is
unreachable dead code. Each case below was inspected:

| ID  | File:line | Disposition |
| --- | --- | --- |
| 7.1 | `combat_manager.py:2809 _find_harass_target` (first) vs `:5005` (second) | Deleted the first; the second is strictly more capable (workers > isolated tech > base fallback). 1160/1160 still pass. |
| 7.2 | `economy_manager.py:1681 _prevent_resource_banking` vs `:3258` | **Architectural — needs human review.** First focuses on extra Queens + spore/spine static defense after the 3rd base. Second focuses on macro hatcheries + tech upgrades + gas-worker reduction. Both meaningful; merging requires a product decision (e.g. compose them, or choose). Leaving in place for now. |
| 7.3 | `economy_manager.py:3391 _reduce_gas_workers` vs `:4082` | Same kind of split – two different approaches to reducing gas. Needs human review. |
| 7.4 | `local_training/production_resilience.py:105 build_terran_counters` x2 | Needs human review. |
| 7.5 | `opponent_modeling.py current_opponent` x2 | False positive — getter + setter for the property added in iteration 6. Intentional. |

## Iteration 8 — Smoke runners work without burnysc2 (done)

| ID  | Item | Result |
| --- | --- | --- |
| 8.1 | `wicked_zerg_challenger/test_bot_initialization.py` (a CLI smoke runner) couldn't run without burnysc2 because it imported the bot directly. Bootstraps the same `_sc2_stub` registration the pytest conftest does, so the script now exits 0 and verifies real importability of `WickedZergBotProImpl`. |
| 8.2 | `scouting/advanced_scout_system_v2.py` had an empty `class UnitTypeId: pass` ImportError fallback. Any default-argument access (`unit_type=UnitTypeId.OVERLORD`) at class-definition time blew up the entire module. Added a tiny `__getattr__` metaclass so the fallback returns the attribute name as a sentinel, mirroring the test stub. |
| 8.3 | Combined pytest suite still 1160/1160 green; main bot module imports cleanly via stub. |

## Iteration N — Continuous loop instructions

After each iteration:
1. Run `python -m pytest tests/ --tb=no -q` from `wicked_zerg_challenger/`.
2. Move newly-fixed entries to **(done)**.
3. Append any newly-discovered failures to a new iteration block.
4. Commit and push to `claude/stoic-shannon-SOUVq`.
