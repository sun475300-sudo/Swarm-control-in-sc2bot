# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-04

---

## Snapshot (current state)

- Branch: `claude/optimistic-edison-7hd5q9` (base: `main`), last logic commit before this
  session: `6947f1a` (2026-06-01) — roughly a month of inactivity on bot logic, only
  a CI yml tweak (2026-06-25) landed since.
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` runs black + isort + flake8 ✅
- **Test suite (2026-07-04): `tests/` 494 pass / 8 fail / 14 skip; `wicked_zerg_challenger/tests/` 661 pass / 0 fail.**
  The 8 `tests/` failures are `crypto_trading`/`test_security.py` — an unrelated
  module hitting a missing `_cffi_backend` native dep in this sandbox, not an SC2
  bot regression.
- Queen transfusion logic: confirmed still correct, priority system (`TRANSFUSE_PRIORITY`) verified against REMAINING_ISSUES.md Issue #3 — already resolved, doc was stale.

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

## Resolved this run (2026-07-04)

| Item | File(s) | Notes |
|------|---------|-------|
| 12 failing FSM tests | `tests/test_combat_phase_fsm.py` | Replaced deprecated `asyncio.get_event_loop().run_until_complete()` with `asyncio.run()` in 5 helper methods. |
| protobuf collection error when running `tests/` alone | `tests/conftest.py` | Added `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` env default (the sc2/s2clientprotocol fix `wicked_zerg_challenger/tests/conftest.py` already had, but too late to help plain `tests/` runs). |
| REMAINING_ISSUES.md N1-N4 (F811 dupes) marked open | `REMAINING_ISSUES.md` | Verified already fixed by commit `e648ae4` (2026-06-01); `pyflakes` confirms 0 F811 repo-wide. Doc updated to Resolved. |
| REMAINING_ISSUES.md Issue #3 (transfusion priority) marked open | `REMAINING_ISSUES.md` | Verified already implemented in `queen_manager.py:711` (`TRANSFUSE_PRIORITY`/`UNHEALABLE_UNITS`), with existing regression tests. Doc updated to Resolved. |
| REMAINING_ISSUES.md Issue #5 marked fully resolved | `REMAINING_ISSUES.md` | `utils/position_utils.py` exists but isn't used anywhere — reclassified PARTIAL, 9 call sites still need the swap. |
| ROADMAP.md stale "Phase 56 / 45-50%" header | `ROADMAP.md` | Added a verified Sprint-by-sprint status table; Sprints 1-7 are essentially done in code, Sprint 8 (30-game QA, arena package validation) has never actually been run. |
| TODO.md stale open items | `TODO.md` | Added a notice — items 1-5 (scouting, harass, expansion timing, frame-skip, StrategyManager split) are all implemented; doc kept as historical record. |

**Net result this run: `tests/test_combat_phase_fsm.py` 12 failing → 0 failing. `tests/` overall 20 failing → 8 failing (remainder is unrelated crypto_trading sandbox dependency, tracked separately, not an SC2 bot bug).**

## Long-term direction

- **AI Arena submission cadence.** 2-week cadence: benchmark suite (P2.2), submit only if metrics improve.
- **Self-play loop.** `NEXT_LARGE_PLAN.md` P823 — highest-leverage long-term improvement.
- **Macro / micro directory split.** Keep `wicked_zerg_challenger/macro/` vs `wicked_zerg_challenger/micro/`.
- **Reality check (2026-07-04):** `NEXT_LARGE_PLAN.md`/`NEXT_PHASE_PLAN.md` P7xx-P9xx items (Kubernetes/Grafana/ONNX/TensorRT-scale infra) have no corresponding code or commits referencing their phase IDs anywhere in history — treat as aspirational/parking-lot, not active backlog, until someone explicitly picks one up.

---

## Run history

- **2026-04-25** — Initial nightly plan.
- **2026-04-26** — P0.2 (empty-logger CI guard) landed.
- **2026-04-27** — black + isort + flake8 all clean.
- **2026-04-28** — Harassment retraction logic hardened (P1.2).
- **2026-05-01** — P1.1 scout cadence, P1.2 harassment, P1.3 expansion timing, P1.5 doc history. Commit blocked by index.lock.
- **2026-05-02** — P0 scout import mismatch fixed. P1.4 deprecation shim. P2.1 FSM tests 23/23 pass.
- **2026-05-03** — **Test suite cleared:** 90 failures → 0. Fixed pytest-asyncio, torch stubs (qmix/mappo), stale __init__ exports (mappo/comm_learning), gas threshold test, crypto skipif guards. Final: 398 pass / 20 skip / 0 fail.
- **2026-06-01** — (PR #218) F811 duplicate-definition cleanup (N1-N4), F821 NameError fixes, dead-code removal, 7 test failures + 1 collection error resolved.
- **2026-06-25** — CI yml tweak only; no bot-logic commits.
- **2026-07-04** — First session after ~1 month of inactivity. FSM asyncio fix (12 failures → 0), protobuf env fix in `tests/conftest.py`, re-verified and closed stale REMAINING_ISSUES entries (N1-N4, #3), reclassified #5 as partial, refreshed ROADMAP.md/TODO.md stale status text. `tests/` 20 failing → 8 failing (remainder unrelated to the bot).
