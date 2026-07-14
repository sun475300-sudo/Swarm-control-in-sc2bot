# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-14

---

## Snapshot (current state)

- Branch: `claude/optimistic-edison-aiby71` (PR #460 open against `main`).
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: both `ci.yml` and `sc2bot-ci.yml` were red on `main` going into this run —
  see "Resolved this run (2026-07-14)" below. Fixes are in PR #460, not yet merged.
- **Test suite (root `tests/`): 474 pass / 4 skip / 0 fail** (excl. 2 crypto/security
  tests that fail locally on `_cffi_backend`/rust-panic — sandbox-only, see below).
- **Test suite (`wicked_zerg_challenger/tests/`): 661 pass / 0 fail**.
- ROADMAP.md audit (2026-07-14): 25/26 Sprint 1-7 tasks confirmed DONE in code;
  only Task 7.3 (magic-number → `GameConstants` migration) is PARTIAL. The
  roadmap's own "Phase 56, 342/342" header is stale — ignore it.
- REMAINING_ISSUES.md audit (2026-07-14): all previously-open issues (#3 smart
  transfusion priority, #4 resource reservation lock, #5 position-utils
  dedup) are implemented in code. Doc has been updated to reflect this.

## Resolved this run (2026-07-14)

| Item | File(s) | Notes |
|------|---------|-------|
| Test collection crash w/o `sc2` installed | `tests/test_queen_transfusion.py` | Missing the `try/except ImportError` guard every sibling test file has; broke collection for the whole suite in any env without `burnysc2`. |
| Repo-wide black/isort drift | 70 files | `black --check`/`isort --check-only` both failing on `main`, unrelated to any single PR — blocked CI for every open PR. Ran both tools; verified via `py_compile` + manual diff review (formatting only). |
| `ci.yml` "pytest 실행 (전체)" step missing protobuf env var | `.github/workflows/ci.yml` | `pytest tests/ --co -q` crashes 14 files with `TypeError: Descriptors cannot be created directly` without `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python`. Sibling step already sets it; this one didn't. Masked previously by a `\|\| true` that a prior commit removed. |
| `sc2bot-ci.yml` "Test Suite" job pointing at nonexistent dirs | `.github/workflows/sc2bot-ci.yml` | `tests/unit` and `tests/integration` have never existed in this repo — job failed at collection every time it ran, gating `build_docker`/`push_to_registry`/`deploy_to_k8s` behind an unwinnable step. Repointed at `tests/` + `wicked_zerg_challenger/tests/` as two separate invocations (combining them in one pytest process hits a `scripts/` namespace-package collision between repo-root `scripts/` and `wicked_zerg_challenger/scripts/`). |
| `asyncio.get_event_loop()` deprecated pattern | `tests/test_combat_phase_fsm.py` | Raised `RuntimeError: no current event loop` under pytest-asyncio 1.x, failing all 12 FSM-transition tests. Switched to `asyncio.run()`. |

### Known local-sandbox-only failure (not fixed, believed non-reproducible in CI)

`tests/test_crypto_trading.py` / `tests/test_security.py` fail locally with
`pyo3_runtime.PanicException: Python API call failed` / `ModuleNotFoundError:
No module named '_cffi_backend'` when importing `cryptography`. Root cause:
this sandbox has a system apt `cryptography` package (`/usr/lib/python3/dist-packages`)
shadowing the pip-installed one, missing its Rust/cffi backend. CI installs
`cryptography` cleanly via pip per `requirements.txt` with no such conflict —
GitHub Actions job logs from this same run show a clean `cryptography-49.0.0`
+ `cffi-2.1.0` install. Flagged here in case it ever surfaces in real CI; no
code change made since it isn't a real bug in this repo's code.

## Previously resolved (2026-05-03)

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
|------|-----------------------------------------------------------|--------|-------|
| P0.1 | CI red on every PR (sc2 import guard + black/isort drift) | ✅ Done | See "Resolved this run (2026-07-14)" above. PR #460. |
| P0.2 | `ci.yml` missing protobuf env var on full-suite step       | ✅ Done | Same PR. |
| P0.3 | `sc2bot-ci.yml` Test Suite job pointing at dead dirs       | ✅ Done | Same PR — was gating Docker build/push/deploy behind an unwinnable step. |

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
| P2.6 | ROADMAP Task 7.3: magic numbers → `GameConstants`| ❌ Open | `GameFrequencies`/`EconomyConstants` exist and are correct but only adopted in 4 files; raw `iteration % 11/22/33/66/110/220` patterns still appear 146+ times repo-wide (confirmed by 2026-07-14 roadmap audit). |
| P2.7 | Wire up `utils/position_utils.py` (dead code)   | ❌ Open | Helper functions exist and match REMAINING_ISSUES.md Issue #5 exactly, but nothing imports them. 6 inline duplicated center-position calcs remain: `battle_preparation_system.py:166`, `combat_manager.py:1622,3657`, `combat_phase_controller.py:591`, `idle_unit_manager.py:179`, `micro_controller.py:525`. |

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
- **2026-07-14** — Resumed after a ~2.5 month gap. Found and fixed 5 issues that had made CI red on every open PR (sc2 import guard, repo-wide black/isort drift, two separate CI-yaml misconfigurations, a deprecated asyncio pattern). Audited ROADMAP.md (25/26 done) and REMAINING_ISSUES.md (all previously-open issues actually resolved in code already) — both were stale. PR #460 opened, CI re-running.
