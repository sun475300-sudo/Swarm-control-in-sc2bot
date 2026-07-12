# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-12

---

## Snapshot (current state)

- Branch: `main`, last commit: queen transfusion + requirements-dev.txt session
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` + `ci.yml` were both **red on every push since ~2026-05-28** (see 2026-07-12 entry) — fixed this run ✅
- **Test suite: 1163 pass / 14 skip / 0 fail** ✅ (`tests/` 492 + `tests/integration` 10 + `wicked_zerg_challenger/tests` 661; run as 3 separate `pytest` invocations — combining them in one process breaks `scripts.*` import resolution, see 2026-07-12 notes)
- Queen transfusion logic: 3 bugs fixed (`is_idle` guard removed, target dedup, per-queen cooldown) ✅

## Resolved this run (2026-07-12)

Ran the standard cycle (test → inspect CI → fix → commit/push) after a ~2-month
gap since the last nightly entry. Headline finding: **CI had been failing on
every push to `main` since 2026-05-28** and nobody had noticed because the
gate silently no-ops when nothing pushes to a watched branch.

| Item | File(s) | Notes |
|------|---------|-------|
| `sc2bot-ci.yml` lint job red since 2026-05-28 | 73 files | `black --check --diff .` was failing (formatting drift accumulated over ~2 months of commits that skipped the pre-commit format pass). Ran `black .` + `isort .` repo-wide; both clean now. Lint job blocks `test`/`build_docker`/`push_to_registry`/`deploy_to_k8s` via `needs:`, so this one regression silently disabled the entire pipeline including deploys. |
| `sc2bot-ci.yml` test job broken even when lint passes | `.github/workflows/sc2bot-ci.yml` | `pytest tests/unit` referenced a directory that doesn't exist (never did, in this history). Fixed to `pytest tests --ignore=tests/integration`, added a separate step for `pytest wicked_zerg_challenger/tests` (661 tests that were never wired into any CI job), kept `tests/integration` as-is. |
| `ci.yml` "Python 린트 & 테스트" job red since 2026-05-28 | `.github/workflows/ci.yml` | `pytest 실행 (전체)` step was missing `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION: python`, so importing `sc2` triggered `TypeError: Descriptors cannot be created directly` (protobuf ≥ 4 generated-code check) and 14 test files failed to collect. The sibling `sc2-bot-test` job already sets this env var correctly — just missing here. |
| `tests/test_combat_phase_fsm.py` — 12 failures under full-suite run (passed in isolation) | `tests/test_combat_phase_fsm.py` | 5 helper methods called `asyncio.get_event_loop().run_until_complete(...)`, a pattern removed/errors in Python 3.11 once any earlier test has closed the default event loop (`RuntimeError: There is no current event loop in thread 'MainThread'`). Replaced with `asyncio.run(...)`, which owns its own loop per call. |
| Sandbox `import crypto_trading` panics (`pyo3_runtime.PanicException` / `ModuleNotFoundError: No module named '_cffi_backend'`) | `requirements-dev.txt` | Debian-packaged `cryptography` 41.x hazmat rust bindings import `_cffi_backend` at load time; pip's own `cryptography>=41.0.0` constraint was already satisfied so it never got a fresh wheel. Added `cffi>=1.15.0` to `requirements-dev.txt` as a safety net. |
| Local sandbox couldn't install `burnysc2`/`mpyq` at all | environment only, no repo change | `mpyq`'s legacy `setup.py bdist_wheel` hits a Debian-distutils `install_layout` bug on this box's system Python. Workaround: `SETUPTOOLS_USE_DISTUTILS=stdlib pip install ...`. Not a repo issue (GitHub Actions runners use upstream CPython builds, unaffected) — noting here so the next session doesn't re-diagnose it from scratch. |

**Net result:** CI unblocked after ~6 weeks red. Full suite (all 3 pytest
invocations) now 1163 passed / 14 skipped / 0 failed.

## Resolved 2026-05-03

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

| #    | Item                                                     | Status | Notes |
|------|----------------------------------------------------------|--------|-------|
| P0.1 | CI red on every push to `main` since 2026-05-28          | ✅ Done | See 2026-07-12 run notes: black/isort drift + bad test paths (`sc2bot-ci.yml`) and missing protobuf env var (`ci.yml`). |

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
| P1.8 | Wire `wicked_zerg_challenger/tests` (661 tests) into CI    | ✅ Done | Was passing locally the whole time but no CI job ever ran it — added a dedicated step in `sc2bot-ci.yml`. |

### Next up (not started, highest-value candidates for the next run)

- Sweep `REMAINING_ISSUES.md` N5 (≈360+ bare `except Exception:`) and N6 (F841 unused locals) — low severity but large volume, worth a scripted pass.
- `REMAINING_ISSUES.md` Issue #3 — priority-based Queen transfusion (heal high-value units first, skip un-healable units).
- P2.2 benchmark runner is still the biggest open gap for judging whether future changes actually improve win rate.

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
- **2026-07-12** — **CI unblocked after ~6 weeks red:** `sc2bot-ci.yml` black/isort drift (73 files) + bogus `tests/unit` path; `ci.yml` missing `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION` env var; `test_combat_phase_fsm.py` deprecated-event-loop bug (12 failures under full-suite ordering). Added `wicked_zerg_challenger/tests` (661 tests) to CI — was never wired in. `cffi` added to `requirements-dev.txt`. Full suite: 1163 pass / 14 skip / 0 fail.
