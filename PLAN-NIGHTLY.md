# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-14

---

## Snapshot (current state)

- Branch: `claude/optimistic-edison-ybru6n` (PR #468 vs `main`), base last commit: `8a80b73` "Update ci.yml".
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` lint job still fails repo-wide (65 files need `black`; pre-existing, unrelated to this run — see S3.2/S1.8 in `MASTER_TODO_SC2.md`). Not addressed this run beyond the files this run's fixes touched.
- **Test suite (local, full deps installed): 1166 pass / 14 skip / 0 fail** ✅ — up from 762 pass / 55 fail / 11 error / 65 skip measured at the start of this run once the sandbox's SC2 dependency install was fixed (see below); the 66 "failures" beyond the 3 real bugs below were all missing-dependency artifacts (stubbed `UnitTypeId`, missing `cffi`), not code bugs.
- Queen transfusion logic (previous run): 3 bugs fixed (`is_idle` guard removed, target dedup, per-queen cooldown) ✅

## Resolved this run (2026-07-14)

| Item | File(s) | Notes |
|------|---------|-------|
| P2.4 RL agent save-experience guard | `wicked_zerg_challenger/local_training/rl_agent.py`, new `wicked_zerg_challenger/tests/test_rl_agent_save_guard.py` | `save_experience_data()` did `os.remove(dest)` then `os.rename(tmp, dest)` — if the rename step failed or the process died in that window (disk-full, interrupted syscall), the previous good save was gone with nothing to replace it. Switched to `os.replace()` (atomic swap on POSIX + Windows, no unlinked-but-not-replaced window). Added 3 guard tests: successful save, disk-full mid-write, interrupted replace (asserts the prior file survives untouched). Closes the P2.4 item below. |
| CI: `python-lint-test` pytest collection failing | `.github/workflows/ci.yml` | The job's `pytest tests/ --co -q` step didn't set `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python`, so collection order determined which protobuf backend won the process; whichever test file imported `google.protobuf` first (without having set the env var itself) locked in the C++ backend and broke 14 other files' collection with `TypeError: Descriptors cannot be created directly`. The sibling `sc2-bot-test` job already sets this env var — brought `python-lint-test`'s pytest step in line with it. |
| Flaky FSM tests: `asyncio.get_event_loop()` | `tests/test_combat_phase_fsm.py` | 5 call sites used `asyncio.get_event_loop().run_until_complete(...)`, which depends on a "current" event loop existing for the thread. Once any other test in the same pytest run exercises `pytest-asyncio` and its loop gets closed, `get_event_loop()` stops auto-creating a replacement and raises `RuntimeError: There is no current event loop in thread 'MainThread'` — 12/23 tests in this file failed whenever it ran after other suites (all 23 passed in isolation, which is why this had gone unnoticed). Switched to `asyncio.run(...)`, which owns its own loop per call. |
| Stray committed test artifact | `local_training/models/test_rl_agent.tmp.npz` | Untracked from git — matched an existing `.gitignore` rule (`**/local_training/models/*.tmp*`) but had been added to the index before that rule existed. |

**Sandbox-only, no code change**: this run's container needed `cffi` and burnysc2's non-`mpyq` runtime deps (`aiohttp`, `loguru`, `portpicker`, `scipy`, `pys2clientprotocol`) installed by hand — `mpyq`'s sdist fails to build against this container's patched `setuptools` (`AttributeError: install_layout`) and has no prebuilt wheel. This looks like a container-specific `setuptools`/`distutils` quirk, not a repo bug: GitHub Actions' `sc2-bot-test` job installs `burnysc2` (which pulls `mpyq`) successfully today. Flagged here in case it recurs elsewhere, not filed as a repo TODO.

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
| P2.1 | Force-accumulation FSM tests                    | ✅ Done | `tests/test_combat_phase_fsm.py` — 23 tests all passing (fixed a real event-loop flake this run, see above). |
| P2.2 | Benchmark runner                                | ❌ Open | Single command, N replays, APM/supply/win-rate report vs Hard. Needs an actual SC2 client + display — not runnable in this sandboxed container; existing `benchmarks/bot_benchmark.py` / `scripts/performance_benchmark_suite.py` only cover microbenchmarks (latency/throughput), not real games. |
| P2.3 | Build-order config externalisation              | ❌ Open | Move top-20 hardcoded values to `config/build_orders.yaml`. Not started this run — no `config/build_orders.yaml` exists yet. |
| P2.4 | RL agent save-experience guard                  | ✅ Done | Fixed a real atomic-save bug (remove-then-rename data-loss window) and added 3 guard tests this run — see above. |
| P2.5 | Type hints + docstring pass on core modules     | 🟡 Partial | `core/resource_manager.py` already has full type hints + docstrings (implements the Issue #4 resource-reservation lock from `REMAINING_ISSUES.md`, confirmed done). `core/manager_factory.py` not audited this run. |

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
- **2026-07-14** — Fresh sandbox baseline (fixed local SC2 dep install, see Sandbox-only note above). Fixed 3 real bugs: RL agent atomic-save data-loss window (P2.4, closed), CI `python-lint-test` missing protobuf-backend env var (14 collection errors), flaky FSM tests from deprecated `asyncio.get_event_loop()` (12/23 intermittent failures). Untracked a stray committed `.tmp.npz` test artifact. Final: 1166 pass / 14 skip / 0 fail locally. PR #468 opened, draft, CI in progress (repo-wide black-format debt — 65 files, pre-existing — still fails the `sc2bot-ci.yml` lint job; out of scope for this run beyond files actually touched).
