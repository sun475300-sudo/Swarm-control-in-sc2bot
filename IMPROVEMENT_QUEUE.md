# SC2 Commander Bot — Improvement Queue

Ongoing test-driven iteration log. Each cycle: run tests → list issues → fix highest-priority items → commit/push → repeat.

---

## Cycle 1 (current)

### Critical (production blockers)
- [x] **`blackboard.py` missing `Blackboard` alias** — `wicked_zerg_bot_pro_impl.py:31` and other modules import `from blackboard import Blackboard`, but the module only exports `GameStateBlackboard`. The bot fails to start. Fix: add `Blackboard = GameStateBlackboard` alias and proper `__all__`.
- [x] **`should_expand()` references nonexistent `is_supply_block`** — actual attribute is `is_supply_blocked` (typo). Causes `AttributeError` whenever expand-gate logic runs.
- [x] **`should_expand()` does not consider mineral cost** — returns True even when minerals < hatchery cost (300). Test `test_should_not_expand_low_minerals` confirms expected behavior.

### Tooling
- [x] **`pytest-asyncio` missing** in pytest tool env — 83 async tests in `tests/` were silently failing.

### Pending (next cycles)
- [ ] `tests/test_queen_transfusion.py` collection requires `sc2` lib import at module load — should soft-skip when unavailable.
- [ ] Cross-suite collection conflict: `scripts.ladder_tracker` / `scripts.meta_adapter` import resolves to `wicked_zerg_challenger/scripts` when both `tests/` and `wicked_zerg_challenger/tests/` collected together.
- [ ] Audit remaining `is_supply_block` / `is_supply_blocked` mismatches in dependent managers (already verified: no other call sites).
- [ ] Investigate other `from <X> import` aliases that could regress.

## Cycle 2

### Real bugs (silent — caught by pyflakes)
- [x] **`economy_manager.py`: `_prevent_resource_banking` defined twice** at lines 1681 and 3258 — the first ~108-line implementation was dead code, fully shadowed by the second definition. The first version had unique spore/spine-build logic that was never reachable. Removed the dead duplicate; the live (and more sophisticated) version stays.
- [x] **`economy_manager.py`: `_reduce_gas_workers` defined twice** at lines 3391 and 4082 — the early simple version was shadowed by a more sophisticated banking-severity-aware version. Removed the dead version.

### Tests
- 1156 tests pass (14 skipped) after dedup. No behavior change because Python class semantics already let the second def win — the cleanup just makes the code match what was actually running.

## Cycle 3

### Dead code after `return`
- [x] **`economy_manager._force_expansion_if_stuck`**: ~37 lines of an old fallback path (`bot.expand_now` + gold-priority manual build) were left after a `return`, totally unreachable. Removed; the live path now correctly delegates to `_perform_smart_expansion`.
- [x] **`economy_manager._check_proactive_expansion`**: similar ~40 lines of pre-refactor expansion fallback after the `return`. Removed. Same reasoning — `_perform_smart_expansion` is the modern path.
- [x] Cleaned a few `f""` strings with no placeholders into plain strings while I was in there.

### Tests
- 1156 passed, 14 skipped — unchanged.

## Cycle 4

### Functional bugs (silent loss of behavior)
- [x] **`opponent_modeling.py`: `OpponentModeling.on_step` defined twice** (lines 341 and 765). The second simpler version shadowed the comprehensive one. As a result the live per-frame opponent modeling only did `_detect_early_signals(<= 180s)`, silently skipping: strategy prediction at mid-game transition, build-order tracking, timing-attack detection, tech-progression tracking, and blackboard updates with `predicted_strategy` / `prediction_confidence` / `observed_signals`. Removed the shadowing version; added a `if not self.bot: return` safety guard to the comprehensive one.
- [x] **`combat_manager.py`: `_find_harass_target` defined twice** (lines 2809 and 5005). The second (more sophisticated: worker-first → tech-buildings → main base) was the live one; the first (main-base-only) was dead. Removed the dead one.

### Notes
- `opponent_modeling.py` also has two parallel naming conventions inside the same class (`current_opponent_id` vs `current_opponent`). The remaining duplicate-naming hazard is documented but not refactored here to keep this cycle's change surgical — flag for cycle 5/6.

## Cycle 5 (planned)
- Audit `except Exception as e: ...` where `e` is unused — silent error swallowing.
- Reconcile `current_opponent_id` vs `current_opponent` naming in `opponent_modeling.py`.
- Hunt remaining pyflakes duplicate-def warnings.
- Make test collection robust to combined runs (`scripts.*` resolution).
