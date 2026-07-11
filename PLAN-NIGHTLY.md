# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-11

---

## Snapshot (current state)

- Branch: `claude/optimistic-edison-8huonz` (from `main` @ `8a80b73`, PR #218 merged 2026-06-25)
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` lint job (black + isort + flake8) — **was broken** (66 files failed black, 19 failed isort) → fixed this run, now 100% clean.
- CI: `sc2bot-ci.yml` test job — **was broken** (`pytest tests/unit` pointed at a directory that doesn't exist, exit code 4, blocking `build_docker`/deploy jobs downstream) → fixed this run to run the real suites (`tests/` + `wicked_zerg_challenger/tests/`, run as two separate invocations — running them in one pytest call errors on a `scripts.*` module-name collision between root `scripts/` and `wicked_zerg_challenger/scripts/`).
- **Test suite: 502 pass / 14 skip (`tests/`) + 661 pass (`wicked_zerg_challenger/tests/`) = 1163 pass / 14 skip / 0 fail** ✅
- Fixed a real order-dependent test bug: `tests/test_combat_phase_fsm.py` used `asyncio.get_event_loop().run_until_complete(...)`, which raises `RuntimeError: There is no current event loop in thread 'MainThread'` under pytest-asyncio 1.x when an earlier async test in the same run leaves no current loop set. Replaced with `asyncio.run(...)` (5 call sites) — now passes regardless of run order/composition.
- Queen transfusion logic: 3 bugs fixed (`is_idle` guard removed, target dedup, per-queen cooldown) ✅ (carried over from prior session)

## Resolved this run (2026-07-11)

| Item | File(s) | Notes |
|------|---------|-------|
| CI test job pointed at nonexistent dir | `.github/workflows/sc2bot-ci.yml` | `pytest tests/unit` — no such directory exists (`ls tests/` has no `unit/` subdir). Exit code 4 (usage error), so the `test` job (and downstream `build_docker`/`push_to_registry`/`deploy_to_k8s`) never actually ran successfully. Changed to run `tests/` and `wicked_zerg_challenger/tests/` as two separate `pytest` invocations (combining them in one invocation errors on a `scripts.*` module-name collision — root `scripts/` vs `wicked_zerg_challenger/scripts/`). |
| CI lint job black/isort broken | 66 files (black), 19 files (isort) | `black --check --diff .` and `isort --check-only --diff .` were both failing across all 3 lint matrix legs (py3.10/3.11/3.12). Ran `black .` + `isort .` repo-wide; verified purely mechanical (no logic changes) and reran both test suites after — still 100% pass. |
| Order-dependent test failure | `tests/test_combat_phase_fsm.py` | `asyncio.get_event_loop().run_until_complete(...)` (5 call sites) raised `RuntimeError: There is no current event loop in thread 'MainThread'` when run after other async tests in the same pytest session (reproduced with `pytest tests/test_combat_manager.py tests/test_combat_phase_fsm.py` — 12/12 failed; passed in isolation). Replaced with `asyncio.run(...)`. |
| Environment-only gap (not a repo bug) | sandbox | `tests/test_crypto_trading.py` / `tests/test_security.py` failed with `pyo3_runtime.PanicException: ModuleNotFoundError: No module named '_cffi_backend'` — caused by this sandbox's system-level `cryptography` package (`/usr/lib/python3/dist-packages`) missing `cffi`. Fixed locally with `pip install cffi`; no repo change needed. |

**Net result: two real bugs fixed (CI test-job path, FSM event-loop test), CI lint job restored to green. Suite: 502 pass / 14 skip (`tests/`) + 661 pass (`wicked_zerg_challenger/tests/`), 0 fail.**

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
| P2.1 | Force-accumulation FSM tests                    | ✅ Done | `tests/test_combat_phase_fsm.py` — 23 tests all passing (order-dependency bug fixed 2026-07-11). |
| P2.2 | Benchmark runner                                | ❌ Open | Single command, N replays, APM/supply/win-rate report vs Hard. |
| P2.3 | Build-order config externalisation              | ❌ Open | Move top-20 hardcoded values to `config/build_orders.yaml`. |
| P2.4 | RL agent save-experience guard                  | ❌ Open | Unit test for save under disk-full / interrupted-rename. |
| P2.5 | Type hints + docstring pass on core modules     | ❌ Open | `core/resource_manager.py`, `core/manager_factory.py`. |
| P2.6 | `requirements.txt` pip resolver is very slow    | ⚠️ Needs investigation | A plain `pip install -r requirements.txt` took 6+ minutes without finishing resolution in this session's sandbox (likely backtracking across many loose `>=` constraints spanning unrelated subsystems — crypto trading, Discord bot, GenAI, MCP, AWS, TTS — all in one file). Also `mpyq` (a `burnysc2`/`sc2reader` transitive dep) fails to build against `setuptools>=72` (`AttributeError: install_layout`) unless pinned older. Unverified whether this also affects GitHub-hosted runners in `sc2bot-ci.yml`/`ci.yml` — worth checking actual CI run logs, and possibly splitting `requirements.txt` by subsystem or constraining `setuptools<72` as a build dep. |

## Long-term direction

- **AI Arena submission cadence.** 2-week cadence: benchmark suite (P2.2), submit only if metrics improve.
- **Self-play loop.** `NEXT_LARGE_PLAN.md` P823 — highest-leverage long-term improvement.
- **Macro / micro directory split.** Keep `wicked_zerg_challenger/macro/` vs `wicked_zerg_challenger/micro/`.

---

## Pending Windows actions (user)

*None — the 2026-05-03 batch (torch stubs, stale exports, FSM/expansion/scout tests, doc history move) landed via PR #218 (merged 2026-06-25).*

---

## Run history

- **2026-04-25** — Initial nightly plan.
- **2026-04-26** — P0.2 (empty-logger CI guard) landed.
- **2026-04-27** — black + isort + flake8 all clean.
- **2026-04-28** — Harassment retraction logic hardened (P1.2).
- **2026-05-01** — P1.1 scout cadence, P1.2 harassment, P1.3 expansion timing, P1.5 doc history. Commit blocked by index.lock.
- **2026-05-02** — P0 scout import mismatch fixed. P1.4 deprecation shim. P2.1 FSM tests 23/23 pass.
- **2026-05-03** — **Test suite cleared:** 90 failures → 0. Fixed pytest-asyncio, torch stubs (qmix/mappo), stale __init__ exports (mappo/comm_learning), gas threshold test, crypto skipif guards. Final: 398 pass / 20 skip / 0 fail.
- **2026-06-25** — PR #218 merged (queen transfusion hardening, dead-code cleanup, F821 NameError fixes, CI `ci.yml` update).
- **2026-07-11** — Resumed nightly cycle after a 2.5-week gap. Fixed CI `sc2bot-ci.yml` test job pointing at a nonexistent `tests/unit` dir (was blocking `build_docker`+ deploy jobs). Fixed black/isort — both were failing across the whole repo (66 + 19 files); reformatted, verified no logic changes, reran both suites. Fixed a real order-dependent test bug in `tests/test_combat_phase_fsm.py` (stale `asyncio.get_event_loop()` pattern). Flagged P2.6 (slow/fragile `requirements.txt` resolution) for follow-up. Final: 1163 pass / 14 skip / 0 fail across both suites.
