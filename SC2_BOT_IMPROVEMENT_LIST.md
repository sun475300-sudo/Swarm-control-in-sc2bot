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

- [ ] **P2.1** 136 f-string-with-no-placeholders across managers — likely missed interpolations
- [ ] **P2.2** 81 unused locals — many caught-but-ignored exception vars `e` that should be logged or renamed `_`
- [ ] **P2.3** Unused imports in core modules

## Priority 3 - Test Coverage / Robustness

- [ ] **P3.1** No test exists for the shadowed `on_step` behavior — would have caught P1.2
- [ ] **P3.2** Add lint gate (pyflakes) to CI to prevent regressions

## Methodology

Fix priority 1 first, commit/push per logical group, then iterate to P2/P3.
