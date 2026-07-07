# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-07

---

## Snapshot (current state)

- Branch: `claude/optimistic-edison-nit2vx`.
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` runs black + isort + flake8 ✅ (all clean)
- flake8 `E9,F63,F7,F82` (CI hard gate): 0 findings ✅. pyflakes full sweep of `wicked_zerg_challenger/`: 0 `F811` (redefinition), 0 `F821` (undefined name) ✅.
- **Test suite: 490 pass / 12 skip / 0 fail** ✅ (was 468/15/0 in the prior refresh; 12 previously-hidden failures in `test_combat_phase_fsm.py` surfaced and were fixed this run — see below)
- Queen transfusion logic: 3 bugs fixed (`is_idle` guard removed, target dedup, per-queen cooldown) ✅

## Resolved this run (2026-07-07)

| Item | File(s) | Notes |
|------|---------|-------|
| `test_combat_phase_fsm.py` collection-time pass, 12 hidden failures | `tests/test_combat_phase_fsm.py` | Tests called `asyncio.get_event_loop().run_until_complete(...)`, deprecated/removed pattern that raises `RuntimeError: There is no current event loop` under pytest-asyncio's loop-per-test teardown on Python 3.11. Replaced all 5 call sites with `asyncio.run(...)`. All 23 tests in the file now pass; this had been silently masking real FSM coverage. |
| `RLAgent.save_experience_data` data-loss window | `wicked_zerg_challenger/local_training/rl_agent.py` | Old code did `os.remove(path)` then `os.rename(tmp, path)` — if the rename step failed (disk full, interrupted write) the original experience file was already deleted with nothing to replace it, silent data loss. Replaced with `os.replace(tmp, path)`, which is atomic and never leaves that gap. This directly resolves P2.4 below. |
| P2.4 test coverage | `tests/test_rl_agent_save_experience.py` (new) | 4 tests: successful round trip, save failure during compression preserves the existing file, interrupted replace preserves the existing file (this test would have failed against the pre-fix code), parent-dir auto-creation. |
| Stale doc audit | `REMAINING_ISSUES.md`, `ROADMAP.md` | Verified against actual code: Issue #3 (transfusion priority) and Issue #4 (resource reservation locking) were already implemented in a prior session but never marked resolved in the docs; `ROADMAP.md` Sprints 1–7 tasks (worker harassment response, harass-unit tag/return logic, scout cadence constants, 25-pattern build-order detection, `LURKERMP` positioning, mutalisk micro, distance cache, `GameConstants`) are all already present in code. Docs updated so future runs don't re-investigate closed items. |

**Net result: 468 pass → 490 pass (22 new/fixed), 0 fail maintained, 1 real data-loss bug fixed.**

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
| P2.2 | Benchmark runner                                | 🟡 Partial | `benchmarks/bot_benchmark.py` + `scripts/performance_benchmark_suite.py` exist but only cover inference-latency/throughput/memory micro-benchmarks. The originally-scoped "N replays, APM/supply/win-rate vs Hard" match benchmark still needs an actual SC2 game client, which this sandbox doesn't have — cannot close from here. |
| P2.3 | Build-order config externalisation              | ❌ Open | No `config/build_orders.yaml` exists yet. Top hardcoded build values still live in `build_order_executor.py` / `economy_manager.py`. |
| P2.4 | RL agent save-experience guard                  | ✅ Done | Fixed real data-loss bug (remove-then-rename → atomic `os.replace`) in `rl_agent.py::save_experience_data` + 4 new tests in `tests/test_rl_agent_save_experience.py`. |
| P2.5 | Type hints + docstring pass on core modules     | 🟡 Partial | `core/resource_manager.py` already has good coverage; `core/manager_factory.py::__init__(self, bot)` still untyped. Full pass not done this run. |

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
- **2026-07-07** — Sandbox environment set up from scratch (venv + `burnysc2`/`protobuf<4` pin — `s2clientprotocol`'s generated `_pb2.py` files need protobuf 3.x). Found and fixed 12 hidden test failures in `test_combat_phase_fsm.py` (deprecated `asyncio.get_event_loop()` pattern). Closed P2.4 with a real bug fix (atomic `os.replace`) + 4 new tests. Audited `ROADMAP.md`/`REMAINING_ISSUES.md` against actual code — most of Sprints 1–7 and Issues #3/#4 were already implemented but undocumented; docs updated to stop future runs from re-investigating closed items. flake8 CI gate (`E9,F63,F7,F82`) and full pyflakes sweep both clean. Final: 490 pass / 12 skip / 0 fail.
