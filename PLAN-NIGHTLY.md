# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-03

---

## Snapshot (current state)

- Branch: `main` (working from `claude/optimistic-edison-h7igj2`), after PR #218 stabilization work.
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` runs black + isort + flake8 ✅ (all clean)
- **Test suite: 1166 pass / 14 skip / 0 fail** ✅ (`wicked_zerg_challenger/tests` 664 pass + root `tests/` 502 pass)
- **`MASSIVE_FIX_PLAN.md` P0-1 through P0-8 verified in code** (see 2026-07-03 entry) — that doc is stale and its "not yet fixed" framing no longer applies; do not re-do this work, only re-verify if a regression is suspected.

## Resolved this run (2026-07-03)

| Item | File(s) | Notes |
|------|---------|-------|
| 12 failing tests: `RuntimeError: There is no current event loop` | `tests/test_combat_phase_fsm.py` | Sync test helpers called `asyncio.get_event_loop().run_until_complete(...)`; under pytest-asyncio's auto mode there is no set loop left for the main thread between async tests, so this crashed on Python 3.11. Replaced all 5 call sites with `asyncio.run(...)`. Regression vs. the 2026-05-02 entry below, which had these at 23/23 passing — re-verify FSM tests after any pytest-asyncio upgrade. |
| P2.4 RL agent save-experience guard | `tests/test_rl_agent_experience_save.py` (new) | Verified `RLAgent.save_experience_data()` already does atomic temp-file+rename saves; added 3 tests confirming (a) successful save leaves no `.tmp.npz`, (b) overwrite is atomic, (c) a simulated `np.savez_compressed` failure (disk full) leaves the original file untouched and no stray temp file. Marking P2.4 done below. |
| Verified `MASSIVE_FIX_PLAN.md` P0-1..P0-8 | `blackboard.py`, `production_resilience.py`, `strategy_manager_v2.py`, `economy_manager.py`, `resource_manager.py` | Grepped for `FIX P0-N` markers and read the surrounding code for all 8 items (gas overflow, EMERGENCY timeout, min-drone floor during EMERGENCY, REMAX rebuild, 3rd-base forcing, supply-block threshold, gas-worker rebalancing, 1-base mineral overflow). All 8 are implemented — most already carry `# FIX P0-N` comments from a prior session. `MASSIVE_FIX_PLAN.md` predates that work and should be treated as historical, not a live backlog. |

## Resolved 2026-05-03 (previous run, kept for history)

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
| P2.2 | Benchmark runner                                | ❌ Open | Single command, N replays, APM/supply/win-rate report vs Hard. `scripts/performance_benchmark.py` and `benchmarks/bot_benchmark.py` exist but don't match this spec — needs consolidation. |
| P2.3 | Build-order config externalisation              | ❌ Open | Move top-20 hardcoded values to `config/build_orders.yaml` (file does not exist yet). |
| P2.4 | RL agent save-experience guard                  | ✅ Done | `tests/test_rl_agent_experience_save.py` — 3 tests confirming atomic save/overwrite/failure-safety. |
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
- **2026-07-03** — Fresh full-suite run (`wicked_zerg_challenger/tests` + root `tests/`) found a real regression: 12 `test_combat_phase_fsm.py` tests crashing with `RuntimeError: no current event loop` (deprecated `asyncio.get_event_loop()` pattern). Fixed. Verified `MASSIVE_FIX_PLAN.md` P0-1..P0-8 are all already implemented in code (that doc is stale). Closed P2.4 with new atomic-save tests. Final: 1166 pass / 14 skip / 0 fail. Next open items: P2.2 (benchmark runner), P2.3 (`config/build_orders.yaml`), P2.5 (type hints on core/).
