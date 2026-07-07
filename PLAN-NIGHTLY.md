# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-07

---

## Snapshot (current state)

- Branch: `claude/optimistic-edison-dc0hc6` (off `main`, last merged PR #218 "stabilize SC2 bot test suite")
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` runs black + isort + flake8 ✅ (all clean on touched files)
- **Test suite: 673 pass / 0 skip / 0 fail** ✅ (661 pre-existing + 12 new regression tests added this run)
- Queen transfusion logic: 3 bugs fixed (`is_idle` guard removed, target dedup, per-queen cooldown) ✅ (prior session)

## 2026-07-07 run — audit → fix → test cycle

Ran a 4-way parallel subagent audit over combat_manager.py, economy_manager.py,
strategy_manager.py + production_resilience.py, and the smaller managers
(queen_manager, upgrade_manager, opponent_modeling, unit_factory, creep
systems), using flake8 F841 hits as a lead to chase down genuine dead-code
bugs rather than cosmetic unused-variable noise. Confirmed and fixed 6 real
bugs, each verified by reverting the fix and confirming the matching new
test fails (12 new tests total):

| Bug | File | Fix |
|-----|------|-----|
| "LURKER" string doesn't match any real UnitTypeId (ladder Lurkers are `LURKERMP`/`LURKERMPBURROWED`) | `combat_manager.py` (2 sets) | Corrected enum names in both threat/attack-detection sets |
| `_evaluate_army_retreat` inflated enemy supply with non-attacking units (workers/overlords) | `combat_manager.py` | Filter `nearby_enemies` by `can_attack` before computing enemy supply |
| `_redistribute_mineral_workers` removed a list tuple by a locally-mutated value that never matches → `ValueError` swallowed, truncating redistribution to one base pair per call | `economy_manager.py` | Index-based in-place update/pop instead of `list.remove()` by value |
| `_optimize_mineral_assignments` pushed Mineral objects (not Worker units) into `surplus_workers`, so over-assigned drones were never reassigned | `economy_manager.py` | Track actual per-patch worker lists; feed the excess workers into `available` |
| `race_priority_modifiers` keyed by capitalized race name, looked up with lowercase — always missed, so per-race upgrade weighting never applied | `upgrade_manager.py` | Case-correct the lookup + actually apply modifiers via stable sort |
| `OpponentModeling` published counter-strategy predictions to the blackboard, but nothing ever consumed them | `opponent_modeling.py` + `strategy_manager.py` | `StrategyManager.get_unit_ratios()` now reads `recommended_strategy` and biases ratios (1.25x, renormalized) |

Also found but deferred (documented in `REMAINING_ISSUES.md` as #7/#8 for the
next round, since they're missing-feature gaps rather than one-line bug
fixes): no Ravager-specific counter-reaction in `strategy_manager.py`
`_counter_zerg_units`, and a late-game Mutalisk production branch in
`production_resilience.py` that's gated on `has_spire` but never actually
queues a Mutalisk (mitigated by redundant production paths elsewhere).

`REMAINING_ISSUES.md` N1-N4 (F811 duplicate defs) and Issue #3/#4 (smart
transfusion priority, resource-reservation locking) turned out to already be
implemented in code — the doc was simply stale. Updated it to reflect
reality and avoid re-investigating already-solved problems next time.

## Resolved this run (2026-05-03)

| Item | File(s) | Notes |
|------|---------|-------|
| pytest-asyncio missing | sandbox install | Installed pytest-asyncio 1.3.0 — cleared 83 "async def not natively supported" failures. Note: add to `requirements-dev.txt`. |
| QMIX torch stubs | `qmix_marl/sc2_qmix_agent.py` | `NameError: nn is not defined` at module level when torch absent. Added `types.SimpleNamespace` stubs in `except ImportError` block. |
| MAPPO torch stubs | `mappo_marl/sc2_mappo_agent.py` | Same fix as QMIX. |
| MAPPO `__init__` stale exports | `mappo_marl/__init__.py` | Imported non-existent names `ActorNetwork, MAPPOAgent, MAPPOTrainer, SharedCritic`. Replaced with correct names + backward-compat aliases. |
| comm_learning `__init__` stale exports | `comm_learning/__init__.py` | Imported non-existent `CommAgent, CommChannel, CommNet, TarMAC`. Fixed with correct names + aliases + `CommChannel` stub class. |
| Gas overflow test stale | `tests/test_phase10_improvements.py` | Test asserted threshold == 1000 but code was intentionally improved to 800. Updated assertion. |
| Crypto test missing skipif | `tests/test_crypto_trading.py` | `test_import_auto_trader` and `test_import_market_analyzer` were guarded by `pandas` check but both transitively require `pyupbit`. Added `pyupbit` to their `skipif` condition. |

**Net result: 90 failures → 0 failures. Suite: 398 pass / 20 skip.**

## P0 — Critical / blocking

*No P0 items this run.*

## P1 — Important

| #    | Item                                                     | Status | Notes |
|------|----------------------------------------------------------|--------|-------|
| P1.1 | Scouting cadence improvements                            | ✅ Done | `phase_scout_cadence.py` + tests written. Commit pending. |
| P1.2 | Harassment retraction + worker-kill tracking hardening   | ✅ Done | `harassment_coordinator.py` updated. Commit pending. |
| P1.3 | First-expansion timing test harness                      | ✅ Done | `tests/test_expansion_timing.py` 20 tests. Commit pending. |
| P1.4 | Reduce duplicate scout system files                      | ✅ Done | Canonical: `AdvancedScoutingSystemV2`. Deprecation shim + import fix done. |
| P1.5 | Trim top-level doc surface area                          | ✅ Done | 15 historical docs moved to `docs/history/`. Commit pending. |
| P1.6 | Add `pytest-asyncio` to `requirements-dev.txt`           | ✅ Done | `requirements-dev.txt` created with pytest-asyncio>=0.23.0 and all dev deps. |
| P1.7 | Queen transfusion logic bugs                              | ✅ Done | Fixed `is_idle` blocking combat-phase transfusions, added target dedup, added per-queen cooldown (1.5s). 14 new tests in `tests/test_queen_transfusion.py`. |

## P2 — Nice-to-have

| #    | Item                                            | Status | Notes |
|------|-------------------------------------------------|--------|-------|
| P2.1 | Force-accumulation FSM tests                    | ✅ Done | `tests/test_combat_phase_fsm.py` — 23 tests all passing. |
| P2.2 | Benchmark runner                                | ❌ Open | Single command, N replays, APM/supply/win-rate report vs Hard. |
| P2.3 | Build-order config externalisation              | ❌ Open | Move top-20 hardcoded values to `config/build_orders.yaml`. |
| P2.4 | RL agent save-experience guard                  | ❌ Open | Unit test for save under disk-full / interrupted-rename. |
| P2.5 | Type hints + docstring pass on core modules     | ❌ Open | `core/resource_manager.py`, `core/manager_factory.py`. |

## Long-term direction

- **AI Arena submission cadence.** 2-week cadence: benchmark suite (P2.2), submit only if metrics improve.
- **Self-play loop.** `NEXT_LARGE_PLAN.md` P823 — highest-leverage long-term improvement.
- **Macro / micro directory split.** Keep `wicked_zerg_challenger/macro/` vs `wicked_zerg_challenger/micro/`.

---

## Pending Windows actions (user)

Run `E:\GitHub\Swarm-control-in-sc2bot\scripts\commit_nightly_2026-05-03.bat`:
1. `qmix_marl/sc2_qmix_agent.py` (torch stubs)
2. `mappo_marl/sc2_mappo_agent.py` (torch stubs)
3. `mappo_marl/__init__.py` (stale export fix)
4. `comm_learning/__init__.py` (stale export fix)
5. `tests/test_phase10_improvements.py` (gas threshold 800)
6. `tests/test_crypto_trading.py` (pyupbit skipif fix)
7. `tests/test_combat_phase_fsm.py` (P2.1 FSM tests — from prev session)
8. `wicked_zerg_challenger/bot_step_integration.py` (P0 scout import fix — prev)
9. `wicked_zerg_challenger/scouting/advanced_scout_system_v2.py` (compat alias — prev)
10. `wicked_zerg_challenger/scouting/enhanced_scout_system.py` (deprecation shim — prev)
11. `wicked_zerg_challenger/combat/harassment_coordinator.py` (P1.2 — prev)
12. `wicked_zerg_challenger/scouting/phase_scout_cadence.py` + test (P1.1 — prev)
13. `tests/test_expansion_timing.py` (P1.3 — prev)
14. `docs/history/` (P1.5 — prev)
15. Updated `PLAN-NIGHTLY.md`
16. Also add `pytest-asyncio>=0.23` to `requirements-dev.txt` (P1.6)

---

## Run history

- **2026-04-25** — Initial nightly plan.
- **2026-04-26** — P0.2 (empty-logger CI guard) landed.
- **2026-04-27** — black + isort + flake8 all clean.
- **2026-04-28** — Harassment retraction logic hardened (P1.2).
- **2026-05-01** — P1.1 scout cadence, P1.2 harassment, P1.3 expansion timing, P1.5 doc history. Commit blocked by index.lock.
- **2026-05-02** — P0 scout import mismatch fixed. P1.4 deprecation shim. P2.1 FSM tests 23/23 pass.
- **2026-05-03** — **Test suite cleared:** 90 failures → 0. Fixed pytest-asyncio, torch stubs (qmix/mappo), stale __init__ exports (mappo/comm_learning), gas threshold test, crypto skipif guards. Final: 398 pass / 20 skip / 0 fail.
- **2026-06-01/02** — PR #218: stabilized suite further, fixed F821/duplicate-method bugs. 661 pass / 0 skip / 0 fail.
- **2026-07-07** — 4-way parallel audit found and fixed 6 real behavioral bugs (Lurker detection, retreat-ratio inflation, worker-redistribution crash + dead surplus-worker path, race-priority-modifier no-op, opponent-modeling dead-end). 12 new regression tests, each verified against the pre-fix code. `REMAINING_ISSUES.md` stale entries reconciled. Final: 673 pass / 0 skip / 0 fail.
