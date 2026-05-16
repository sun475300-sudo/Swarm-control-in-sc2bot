# SC2 Commander Bot - Improvement List (2026-05-16)

Discovered from test sweep + static analysis (pyflakes) on `wicked_zerg_challenger/`.

Tests: **604 passing**, **2 modules failing to import** (cascading from bug #1).

After iteration 1: **661 passing**, no collection errors.

## Priority 1 - Critical Bugs (broken behavior, test collection failures)

- [x] **P1.1** `blackboard.py` missing `Blackboard` alias → 2 test modules fail to collect, `wicked_zerg_bot_pro_impl` import broken
- [x] **P1.2** `opponent_modeling.py` duplicate `on_step` (lines 341 & 765) — second definition shadows the rich one. Critical: bot loses tech tracking, timing-attack detection, strategy prediction, blackboard updates
- [x] **P1.3** `opponent_modeling.py` state attribute drift — `current_opponent_id` (init) vs `current_opponent` (on_game_start). Different attributes break consistency
- [x] **P1.4** `combat_manager.py` duplicate `_find_harass_target` (lines 2809 & 5005) — first def is dead code
- [x] **P1.5** `economy_manager.py` duplicate `_prevent_resource_banking` (lines 1681 & 3258) — first def is dead code
- [x] **P1.6** `economy_manager.py` duplicate `_reduce_gas_workers` (lines 3391 & 4082) — first def is dead code
- [x] **P1.7** `blackboard.py` `should_expand` referenced non-existent `is_supply_block` (typo of `is_supply_blocked`) → would throw AttributeError every time called
- [x] **P1.8** `blackboard.py` `should_expand` missing mineral threshold (always True if no threat, even at 0 minerals)

## Priority 2 - Code Quality (silent failures, lint smells)

- [x] **P2.1** 141 f-string-with-no-placeholders fixed (mechanical f"" → "")
- [x] **P2.2** 46 caught-but-ignored exception vars `e` cleaned up (`except E as e:` → `except E:`)
- [x] **P2.3** `game_analytics_system.py` had a **syntax error** (duplicated paste artifact at line 419) that made the entire module unimportable — this was hidden behind pyflakes order, now fixed
- [x] **P2.4** Triaged ~15 unused-local warnings: dropped genuinely-dead assignments in `combat_manager`, `economy_manager`, `strategy_manager`, `production_controller`, `meta_game_analyzer`, `aggressive_strategies`, `adaptive_trainer`, `air_threat_response_trainer`. Several encoded silent algorithm gaps (e.g., `ravager_count` computed in ZvZ counter logic but never branched on). Remaining ~19 are very small files / one-off scripts and lower-risk
- [x] **P2.5** Applied `black` + `isort` to all touched files (CI was failing on format check)

## Priority 3 - Test Coverage / Robustness

- [x] **P3.1** Added `test_no_shadowed_methods.py` — parametrized regression guard that AST-walks every bot module and fails if any class redefines a method (would have caught P1.2 / P1.4 / P1.5 / P1.6 instantly). Currently scans 138 modules
- [x] **P3.2** Added `test_iteration1_regressions.py` — pins the iteration-1 fixes (Blackboard alias, opponent_modeling on_step richness + state attribute, should_expand typo + mineral gate)
- [ ] **P3.3** Add `pyflakes` step to CI to prevent regression of unused-local / duplicate-method patterns
- [ ] **P3.4** Add a CI check that all bot modules import cleanly (would have caught the `game_analytics_system.py` syntax error from iteration 2)

## Methodology

Fix priority 1 first, commit/push per logical group, then iterate to P2/P3.
