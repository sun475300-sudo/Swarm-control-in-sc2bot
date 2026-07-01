# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-01

---

## Snapshot (current state)

- Branch: `main` (this session on `claude/optimistic-edison-fmx0a4`)
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` runs black + isort + flake8 ✅
- **`tests/` suite: 502 pass / 14 skip / 0 fail** ✅ (verified 2026-07-01, was showing 12 failures before this session's FSM fix)
- **`wicked_zerg_challenger/tests/` suite: 661 pass / 0 fail** ✅ (verified 2026-07-01; run as a separate `pytest` invocation per CI config — do not combine with root `tests/` in one invocation, see note below)
- Queen transfusion logic: 3 bugs fixed (`is_idle` guard removed, target dedup, per-queen cooldown) ✅
- No real SC2 game client available in this sandboxed session — game-level testing (`run_single_game.py`, `run_mass_test.py`) could not be executed here; only static analysis + pytest were run.

### Note: don't run `tests/` and `wicked_zerg_challenger/tests/` in one pytest invocation
Both directories contain an unrelated `scripts/` subpackage (root `scripts/` vs `wicked_zerg_challenger/scripts/`, the latter has no Python modules). Combining both test roots in a single `pytest` command can trigger a Python namespace-package resolution collision (`ModuleNotFoundError: No module named 'scripts.ladder_tracker'`) depending on sys.path insertion order. Each suite passes cleanly when run standalone (matches how CI actually invokes them, in separate steps). Not a functional bug — just a footgun for local ad-hoc runs.

## Resolved this run (2026-07-01)

| Item | File(s) | Notes |
|------|---------|-------|
| FSM combat-phase tests failing on Py3.11 | `tests/test_combat_phase_fsm.py` | 12 tests used `asyncio.get_event_loop().run_until_complete(...)`, which raises `RuntimeError: There is no current event loop in thread 'MainThread'` once pytest-asyncio's per-test loop teardown runs first. Replaced all 5 occurrences with `asyncio.run(...)`. 23/23 tests in the file now pass. |
| `REMAINING_ISSUES.md` N1–N4 stale | docs | Re-verified via `grep -n "def <name>"`: all four previously-flagged duplicate-definition issues (`OpponentModeling.on_step`, `EconomyManager._prevent_resource_banking`/`_reduce_gas_workers`, `combat_manager._find_harass_target`, `production_resilience.build_terran_counters`) have exactly one definition each. Confirmed via `flake8 --select=F811` returning zero hits across `wicked_zerg_challenger/`. Marked Resolved with verification method. |

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
| P2.1 | Force-accumulation FSM tests                    | ✅ Done | `tests/test_combat_phase_fsm.py` — 23 tests all passing. Regressed to 12/23 failing at some point after this was marked done (Py3.11 `get_event_loop()` incompatibility) — re-fixed 2026-07-01, see Resolved section above. |
| P2.2 | Benchmark runner                                | ❌ Open | Single command, N replays, APM/supply/win-rate report vs Hard. Blocked in cloud sessions: no local SC2 client — needs a machine with the game installed. |
| P2.3 | Build-order config externalisation              | ❌ Open | Move top-20 hardcoded values to `config/build_orders.yaml`. |
| P2.4 | RL agent save-experience guard                  | ❌ Open | Unit test for save under disk-full / interrupted-rename. |
| P2.5 | Type hints + docstring pass on core modules     | ❌ Open | `core/resource_manager.py`, `core/manager_factory.py`. |
| P2.6 | Clean up 130 F841 unused-variable warnings       | ❌ Open | `flake8 wicked_zerg_challenger --select=F841`. Mostly `except ... as e` with unused `e` (should at least be logged) and a few dead pre-computed values. Low risk, high volume — good next-session task. |

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
- **2026-07-01** — Full clean-room environment rebuild (venv + deps) and both test suites re-run from scratch. Found and fixed a real regression: 12/23 `test_combat_phase_fsm.py` tests were failing (`asyncio.get_event_loop()` incompatible with current pytest-asyncio + Py3.11 loop teardown) — fixed with `asyncio.run()`. Re-verified `REMAINING_ISSUES.md` N1–N4 (duplicate-definition F811 issues) are already resolved in the codebase; updated that doc so it stops flagging closed issues. Final: `tests/` 502 pass/14 skip/0 fail, `wicked_zerg_challenger/tests/` 661 pass/0 fail. No SC2 game client available in this sandbox, so game-level/benchmark testing (P2.2) remains blocked here. Next priorities queued: P2.6 (F841 cleanup), P2.3, P2.4, P2.5.
