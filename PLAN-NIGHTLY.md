# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-09

---

## Snapshot (current state)

- Branch: `claude/optimistic-edison-3jsqye` (PR to `main`), last commit: CI pipeline + formatting repair session
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` lint job (black + isort + flake8) — was RED (66 files unformatted, 16 import-order errors), now ✅ clean
- CI: `sc2bot-ci.yml` test job was misconfigured (`pytest tests/unit` — directory never existed, exit code 4, job always failed) — fixed to run the real suites
- **Test suite (root `tests/`): 502 pass / 14 skip / 0 fail** ✅
- **Test suite (`wicked_zerg_challenger/tests/`): 661 pass / 0 fail** ✅ (not previously wired into `sc2bot-ci.yml` at all)
- **Test suite (`tests/integration/`): 10 pass / 0 fail** ✅

## Resolved this run (2026-07-09)

| Item | File(s) | Notes |
|------|---------|-------|
| CI test job pointed at nonexistent `tests/unit` | `.github/workflows/sc2bot-ci.yml` | Every run of this workflow's `test` job failed at the first step (exit 4), blocking `build_docker`/`push_to_registry`/`deploy_to_k8s` downstream. Repointed at `tests` (minus `tests/integration`), kept the existing integration step, and added a new step running `wicked_zerg_challenger/tests` (661 tests) which this workflow never executed. |
| CI missing `pytest-timeout` dependency | `.github/workflows/sc2bot-ci.yml` | Integration step already used `--timeout=120` but the install step never installed the plugin providing that flag. |
| Combat-phase FSM tests order-dependent | `tests/test_combat_phase_fsm.py` | 12/23 tests failed only when the full suite ran (passed in isolation): `asyncio.get_event_loop()` raises `RuntimeError` once any earlier pytest-asyncio test calls `set_event_loop(None)` at teardown. Replaced the 5 `asyncio.get_event_loop().run_until_complete(...)` call sites with `asyncio.run(...)`. |
| `cryptography`/`_cffi_backend` import panic | sandbox install only | `pip install cffi` — not a code change, just a missing transitive dep in this session's environment. |
| black/isort formatting drift | 71 files (66 black, 16 isort, overlapping) | `black .` + `isort .` — repo had drifted out of CI compliance (likely from files added without running formatters). Purely mechanical, no logic changes; full suite re-verified green after. |

## Resolved previous run (2026-05-03)

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
- **2026-06-01/02** — PR #218: 7 failing tests + 1 collection error resolved, 6 F821 NameError bugs fixed, shadowed duplicate methods deleted (`OpponentModeling.on_step`, `EconomyManager._prevent_resource_banking`/`_reduce_gas_workers`, `combat_manager._find_harass_target`, `production_resilience.build_terran_counters` — closes `REMAINING_ISSUES.md` N1–N4), unimplemented-but-called methods implemented.
- **2026-07-09** — **CI pipeline repair:** `sc2bot-ci.yml` test job fixed (was pointed at nonexistent `tests/unit`, always failing at exit 4 — blocked `build_docker`/`push_to_registry`/`deploy_to_k8s` on every run since the job was written); now also runs `wicked_zerg_challenger/tests` (661 tests), which had never been wired into this workflow. `test_combat_phase_fsm.py` order-dependent failures fixed (`asyncio.get_event_loop()` → `asyncio.run()`, 5 call sites). black/isort drift repaired across 71 files (lint job was red, blocking the whole pipeline via `needs: lint`). Combined suite: 502 + 661 + 10 = 1173 tests, 0 fail, 14 skip (all env-gated: `pyupbit`/`config.yaml` absent in sandbox).
