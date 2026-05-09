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

## Iteration 3 — Combat filter regressions

| ID  | Item | Symptom |
| --- | --- | --- |
| 3.1 | `CombatManager.filter_air_units` returning empty | `test_filter_air_units` expects 1, gets 0 |
| 3.2 | `CombatManager.filter_ground_units` returning empty | `test_filter_ground_units` expects 1, gets 0 |
| 3.3 | `CombatManager.filter_army_units` (ling-only and mixed) returning empty | Tests `test_filter_army_units_zerglings` / `test_filter_army_units_mixed` |

These tests construct mock units with `is_flying`/`type_id` directly. The filter
likely calls a lookup that no longer matches the production data path.

## Iteration 4 — Opening expansion priority gating

| ID  | Item | Symptom |
| --- | --- | --- |
| 4.1 | `test_opening_hatchery_step_is_held_before_ninety_seconds` returns `'upgrade'` instead of `'expand'` |
| 4.2 | Five `TestTechCoordinatorExpansion` failures around the opening-hatchery and pending-third reservation logic |
| 4.3 | `test_zvt_safe_expand_selects_fast_lair_macro` and `test_zvp_stargate_selects_hydra_lair_macro` expect `'morph'` action set but only see `{'upgrade'}` |

## Iteration 5 — Worker harassment response timing

| ID  | Item | Symptom |
| --- | --- | --- |
| 5.1 | Harass workers should retreat after three kills to a fixed rally; the test expects coordinates `(40, 300)` but observes `(40, 100.0…)` |

## Iteration 6 — Quality-of-life follow-ups (queued)

| ID  | Item | Notes |
| --- | --- | --- |
| 6.1 | Fold the stub into a permanent `sc2_dev_stub` package | Allows non-test scripts (smoke runners) to import without burnysc2 |
| 6.2 | Add `pytest --strict-markers` cleanup as warnings drop — currently 39 warnings |
| 6.3 | Wire a smoke target to `wicked_zerg_challenger/tests/run_scouting_tests.py` for the scouting subset |

## Iteration N — Continuous loop instructions

After each iteration:
1. Run `python -m pytest tests/ --tb=no -q` from `wicked_zerg_challenger/`.
2. Move newly-fixed entries to **(done)**.
3. Append any newly-discovered failures to a new iteration block.
4. Commit and push to `claude/stoic-shannon-SOUVq`.
