# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-11

---

## Snapshot (current state)

- Branch: `main` (this session worked on `claude/optimistic-edison-6q6jec`, PR-bound).
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` lint gate (black/isort/flake8-critical) was **red on every run since ~2026-06-14** — fixed this run, see below.
- **Test suite: 502 pass / 14 skip / 0 fail** (`tests/`) + **10 pass** (`tests/integration/`) ✅
- REMAINING_ISSUES.md N1-N4 (F811 duplicate defs) reconfirmed resolved.

## Resolved this run (2026-07-11)

| Item | File(s) | Notes |
|------|---------|-------|
| `sc2bot-ci.yml` lint gate red since ~2026-06-14 | 69 files | `black --check .` failing blocked the entire pipeline (test/build/push/deploy all skipped via `needs: lint`). Ran `black .` + `isort .` (formatting only, no logic changes). |
| `sc2bot-ci.yml` "Run unit tests" pointed at nonexistent `tests/unit` | `.github/workflows/sc2bot-ci.yml` | Changed to `pytest tests/ --ignore=tests/integration`; would have failed as soon as the lint gate above was fixed. |
| `tests/test_combat_phase_fsm.py` 12/23 tests failing | same file | `asyncio.get_event_loop()` raises `RuntimeError` on Python 3.11 with no loop on the thread. Switched to `asyncio.run(...)`. This is the FSM regression safety net (P2.1) — it was silently broken. |
| REMAINING_ISSUES.md N1-N4 stale "open" status | `REMAINING_ISSUES.md` | Re-verified via `flake8 --select=F811,F821` (0 hits) and manual grep — all 4 duplicate-definition bugs were already fixed by earlier commits (`fb0d61f`, `e648ae4`, `fcf1004`, `30b1ce2`). Marked resolved. |

## Resolved prior run (2026-05-03)

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

## Run history

- **2026-04-25** — Initial nightly plan.
- **2026-04-26** — P0.2 (empty-logger CI guard) landed.
- **2026-04-27** — black + isort + flake8 all clean.
- **2026-04-28** — Harassment retraction logic hardened (P1.2).
- **2026-05-01** — P1.1 scout cadence, P1.2 harassment, P1.3 expansion timing, P1.5 doc history. Commit blocked by index.lock.
- **2026-05-02** — P0 scout import mismatch fixed. P1.4 deprecation shim. P2.1 FSM tests 23/23 pass.
- **2026-05-03** — Test suite cleared: 90 failures → 0. pytest-asyncio, torch stubs, stale `__init__` exports, gas threshold test, crypto skipif guards.
- **2026-07-11** — **CI pipeline resurrected.** `sc2bot-ci.yml` lint gate (black format check) had been red since ~2026-06-14, silently skipping test/build/push/deploy on every run. Fixed formatting (69 files, no logic changes) + `tests/unit` → real path in the test job. Also fixed 12 broken FSM regression tests (`asyncio.get_event_loop()` → `asyncio.run()`) and reconfirmed REMAINING_ISSUES.md N1-N4 (F811 duplicate defs) are resolved. Full suite: 502 pass / 14 skip + 10 integration pass, 0 fail.
- **2026-05-03** — **Test suite cleared:** 90 failures → 0. Fixed pytest-asyncio, torch stubs (qmix/mappo), stale __init__ exports (mappo/comm_learning), gas threshold test, crypto skipif guards. Final: 398 pass / 20 skip / 0 fail.
