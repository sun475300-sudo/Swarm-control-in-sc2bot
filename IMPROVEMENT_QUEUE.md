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

## Cycle 2 (next)
- Examine `economy_manager`, `production_controller`, `tech_coordinator` for similar broken imports / typos.
- Look for managers that call methods on the blackboard that don't exist.
- Investigate logger / error-handling consistency.
