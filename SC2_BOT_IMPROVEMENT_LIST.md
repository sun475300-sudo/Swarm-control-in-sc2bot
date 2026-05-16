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
- [ ] **P2.4** ~35 remaining "unused local" warnings — these are genuine algorithm bugs (computed value never used). Manual review per-case

## Priority 3 - Test Coverage / Robustness

- [ ] **P3.1** No test exists for the shadowed `on_step` behavior — would have caught P1.2
- [ ] **P3.2** Add lint gate (pyflakes) to CI to prevent regressions

## Methodology

Fix priority 1 first, commit/push per logical group, then iterate to P2/P3.
