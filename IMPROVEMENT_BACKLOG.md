# SC2 Commander Bot — Improvement Backlog

**Created:** 2026-05-03
**Branch:** claude/stoic-shannon-VPj64
**Source:** test results + REMAINING_ISSUES.md + TODO.md + manual code audit

This backlog drives the iterative test → improve → commit → repeat loop.
Each batch must end with passing tests and a commit pushed to remote.

---

## Status Legend
- [ ] pending
- [~] in progress
- [x] done (referenced commit hash)

---

## Batch 0 — Test Infrastructure (DONE)
- [x] Install pytest-asyncio in pytest's uv environment so async tests run
- [x] Fix stale `test_gas_overflow_threshold_lowered` (1000 → 800) to match
      improved threshold in `economy_manager.py:110-112`

Result: 306 passed, 34 skipped, 0 failed (was: 84 failed before plugin fix +
1 stale test failure).

---

## Batch 1 — Code Quality: Centroid Deduplication (IN PROGRESS)

`utils/position_utils.get_center_position` already exists but 5 modules still
hand-roll the same `sum(u.position.x for u in units) / len(units)` pattern.
Replacing them shrinks the surface area for bugs (e.g. empty-list crashes,
single-unit fast-path) and standardises behaviour.

- [ ] `battle_preparation_system.py:167` — cluster center calc
- [ ] `combat_phase_controller.py:585-594` — `_get_group_center`
- [ ] `micro_controller.py:520-527` — `_centroid` static helper
- [ ] `combat_manager.py:3140-3151` — `_get_enemy_center` fallback
- [ ] `idle_unit_manager.py:178-185` — army center calculation

Validation: existing tests (`test_combat_manager.py`,
`test_combat_components.py`) cover the call sites; full suite must stay green.

---

## Batch 2 — Smart Transfusion Priority (PLANNED)

REMAINING_ISSUES.md Issue #3. Current Queen transfusion picks targets
naively. Add HEAL_PRIORITY map + CANNOT_HEAL exclusion set so high-cost units
(Ultralisk, Brood Lord, Ravager) get healed before Zerglings, and one-shot
units (Baneling, Broodling, Locust) are skipped.

- [ ] Audit `queen_manager.py` and `queen_transfusion_manager.py` transfusion
      flow
- [ ] Add HEAL_PRIORITY constants in `utils/game_constants.py` (or extend
      existing `UnitPriority` class)
- [ ] Implement `smart_transfusion()` selecting target by
      `(-priority, health_percentage)`
- [ ] Add unit tests covering: priority ordering, CANNOT_HEAL exclusion,
      empty-target safety, range guard (≤7)

---

## Batch 3 — Combat Frame-Skip Performance (PLANNED)

TODO.md item #4. Combat micro runs every step which costs FPS in late-game
fights with hundreds of units. Run heavy logic every 3-5 frames except when
in panic state (under attack with HP loss spike).

- [ ] Identify hot loops in `combat_manager.py` and `combat/micro_combat.py`
- [ ] Add `combat_step_interval` (default 3) and panic override
- [ ] Verify with profiler on a simulated 200-unit battle if available

---

## Batch 4 — Scouting Cadence (PLANNED)

TODO.md item #1. Tighten scout intervals and ensure overlord/zergling scout
modes coexist without duplicating intel work.

- [ ] Audit `scouting_system.py`, `early_scout_system.py`,
      `advanced_scout_system_v2.py`
- [ ] Surface `INITIAL_SCOUT_TIME` / `SCOUT_INTERVAL` from
      `StrategyConstants` instead of hard-coded values
- [ ] Add regression test that scout dispatcher fires at expected cadence

---

## Batch 5 — Resource Reservation Race (PLANNED)

REMAINING_ISSUES.md Issue #4. `resource_manager.py` already exists; goal is
to ensure all spend sites (training, building, upgrade) actually go through
the reservation API rather than checking minerals/gas directly.

- [ ] Grep for direct `self.minerals >=` / `self.vespene >=` checks
- [ ] Route the high-traffic ones through ResourceManager
- [ ] Extend existing `tests/test_resource_manager.py` with integration cases

---

## Batch 6 — Magic Number Sweep (PLANNED)

REMAINING_ISSUES.md Issue #6. Replace inline `iteration % 22`, `< 0.4`,
`< 15` etc. with named constants from `utils/game_constants.py`.

- [ ] grep for `iteration %` occurrences and route through `GameFrequencies`
- [ ] grep for `health_percentage <` and route through `CombatConstants`
- [ ] grep for hard-coded distance thresholds and route through
      `CombatConstants` / `UpgradeConstants`

---

## Tracking
After each batch is committed, update the matching `[ ]` to `[x] <hash>` and
add the commit hash. The next session resumes from the first incomplete `[ ]`.
