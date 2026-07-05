# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-05

---

## Snapshot (current state)

- Branch: `main`, last commit: queen transfusion + requirements-dev.txt session
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` runs black + isort + flake8 ✅ (all clean)
- **Test suite: 502 pass / 14 skip / 0 fail** ✅ (verified 2026-07-05 on a fresh checkout — this figure had not actually been reproduced on `main` since the FSM asyncio bug was silently regressing P2.1)
- Queen transfusion logic: 3 bugs fixed (`is_idle` guard removed, target dedup, per-queen cooldown) ✅
- **⚠️ Repo hygiene:** ~20 open PRs (#269-288) and ~300 stale `claude/*` branches accumulated from repeated unmerged automation cycles, most re-fixing this same FSM/asyncio bug independently. Recommend consolidating to one PR and closing the rest — see session report.

## Resolved this run (2026-07-05)

| Item | File(s) | Notes |
|------|---------|-------|
| P2.1 regression: FSM tests actually failing on `main` | `tests/test_combat_phase_fsm.py` | Despite the 2026-05-02 entry below claiming "23/23 pass," `main` still called `asyncio.get_event_loop().run_until_complete(...)`, which raises `RuntimeError: There is no current event loop in thread 'MainThread'` on Python 3.11 (no implicit loop creation). All 12 FSM-transition tests were failing. Note: ~20 open PRs on other `claude/optimistic-edison-*` branches independently "fixed" this same bug without merging — none had landed on `main`. Fixed here with `asyncio.run(...)` (5 call sites). Verified: 502 pass / 14 skip / 0 fail. |
| Stale `REMAINING_ISSUES.md` | `REMAINING_ISSUES.md` | N1-N4 (duplicate method definitions), Issue #3 (transfusion priority), Issue #4 (resource-reservation locking), Issue #5/#6 (utils extraction) were all listed "open" but are already implemented in current code. Re-verified with file:line evidence and marked resolved. |
| Sprint 7.2 DistanceCache adoption (partial → less partial) | `economy_manager.py` | 20 more `.distance_to(` call sites migrated to the existing `self._distance_between()` cache wrapper (was 1/25, now 21/25 in this file). `combat_manager.py` still has ~60 raw calls vs 7 cached — not touched this run, flagged below. |

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
| P2.1 | Force-accumulation FSM tests                    | ✅ Done (2026-07-05, verified for real this time) | `tests/test_combat_phase_fsm.py` — 12 tests, all passing after asyncio.run() fix. Prior "23/23" claim was inaccurate — bug was still live on `main`. |
| P2.2 | Benchmark runner                                | ❌ Open | Single command, N replays, APM/supply/win-rate report vs Hard. |
| P2.3 | Build-order config externalisation              | ❌ Open | Move top-20 hardcoded values to `config/build_orders.yaml`. |
| P2.4 | RL agent save-experience guard                  | ❌ Open | Unit test for save under disk-full / interrupted-rename. |
| P2.5 | Type hints + docstring pass on core modules     | ❌ Open | `core/resource_manager.py`, `core/manager_factory.py`. |
| P2.6 | ROADMAP.md Sprint 7.2 — finish DistanceCache migration | 🟡 Partial | `economy_manager.py` now 21/25 call sites cached (was 1/25). `combat_manager.py` still ~60 raw `.distance_to(` vs 7 cached (`_safe_distance` at combat_manager.py:3567 bypasses cache entirely) — next session should migrate combat_manager.py's hot loops. |
| P2.7 | ROADMAP.md Sprint 7.3 — finish GameConstants migration | 🟡 Partial | `utils/game_constants.py` (`GameFrequencies`, `EconomyConstants`) is adopted in `economy_manager.py` (20 hits) but `strategy_manager.py` and `intel_manager.py` have 0 hits, and `combat_manager.py` still has raw `iteration % 22/33/50/66/110/220` (37 occurrences) that should route through `GameFrequencies`. |
| P2.8 | ROADMAP.md Sprint 8 — Medium AI 30-game benchmark | ❌ Open / unverifiable statically | `run_mass_test.py` exists but no in-repo artifact shows a completed 90%+ win-rate run against Medium AI; requires an actual SC2 client + maps, out of scope for a sandboxed code session. |

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
- **2026-07-05** — Re-verified full suite from a fresh checkout: found the P2.1 FSM asyncio bug was still live on `main` (12 failing), fixed for real (502 pass/14 skip/0 fail). Corrected stale `REMAINING_ISSUES.md`. Migrated 20 more `economy_manager.py` distance calls onto `DistanceCache` (Sprint 7.2). Audited ROADMAP.md Sprints 1-8 against actual code — Sprints 1-6 confirmed fully implemented, Sprint 7 confirmed partial (scaffolding built, migration incomplete), Sprint 8 unverifiable without running real games. Flagged severe PR/branch sprawl (20 open duplicate PRs, ~300 stale branches).
