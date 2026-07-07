# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-07

---

## Snapshot (current state)

- Branch: `claude/optimistic-edison-1co6dc` (from `main`)
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` — black/isort **repo-wide check currently fails**
  (67 pre-existing files not black-formatted; not caused by this run — see
  P0 below). flake8 critical (E9,F63,F7,F82) clean.
- **Test suite: 508 pass / 14 skip / 0 fail** ✅ (up from 398/20/0; count
  differences vs. prior "468" snapshot are from environment/dependency
  availability, not new tests alone — see below)
- Queen transfusion logic: 3 bugs fixed (`is_idle` guard removed, target dedup, per-queen cooldown) ✅

## Resolved this run (2026-07-07)

| Item | File(s) | Notes |
|------|---------|-------|
| Missing sc2/cffi deps blocked collection | sandbox install | Installed `burnysc2` (python-sc2) + `cffi` — cleared 1 collection error + 6 `pyo3_runtime.PanicException` failures in `test_security.py`/`test_crypto_trading.py` (cryptography needed `_cffi_backend`). |
| **Real bug**: `asyncio.get_event_loop()` test pollution | `tests/test_combat_phase_fsm.py` | 12 tests failed with `RuntimeError: There is no current event loop` only when run after other suites (pytest-asyncio 1.x tears the loop down between async tests, and `get_event_loop()` no longer auto-creates one). Replaced with `asyncio.run(...)` (5 call sites). |
| **Real bug**: data-loss window in atomic save | `wicked_zerg_challenger/local_training/rl_agent.py` `save_experience_data` | Old code did `os.remove(path)` then `os.rename(tmp, path)` — if `rename` failed after `remove` succeeded, the previous checkpoint was already gone (interrupted-rename data loss). Replaced with `os.replace(tmp, path)`, atomic on both POSIX and Windows. Closes PLAN-NIGHTLY **P2.4**. 6 new tests in `tests/test_rl_agent_save_experience.py`. |
| Dead utility never adopted | `wicked_zerg_challenger/battle_preparation_system.py` | `utils/position_utils.get_center_position()` existed but nothing imported it; one duplicate center-calc remained in `_find_enemy_clusters`. Wired it in. Closes `REMAINING_ISSUES.md` Issue #5. |
| Stale doc audit | `REMAINING_ISSUES.md` | N1–N4 (duplicate-def F811 findings from PR #44) and Issues #3/#4 (queen transfuse priority, resource-reservation lock) were already implemented in code — doc was stale. Re-verified via `flake8 --select=F811,F821` (0 hits) and source read, moved to Resolved. |

## P0 — Critical / blocking

| # | Item | Status | Notes |
|---|------|--------|-------|
| P0.1 | CI `black --check --diff .` fails repo-wide | ❌ Open | 67 files (pre-existing, unrelated to this run's changes — largely `visuals/`, RL/quantum experiment dirs) would be reformatted. All files touched this run are black+isort clean. Needs a dedicated formatting-only PR (large diff, no logic change) rather than folding into feature work. |
| P0.2 | CI `test` job references `tests/unit` | ✅ Done | `sc2bot-ci.yml` ran `pytest tests/unit -v ...` — no `tests/unit/` directory exists (tests live flat under `tests/` + `tests/integration/`), so pytest printed `ERROR: file or directory not found` but **exited 0** ("no tests ran"), silently green in CI for however long this shipped. Fixed to `pytest tests --ignore=tests/integration -v ...`; verified locally (498 collected, was 0). |

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
| P2.4 | RL agent save-experience guard                  | ✅ Done | 2026-07-07: found and fixed a real data-loss window (`os.remove`+`os.rename` → `os.replace`), 6 new tests in `tests/test_rl_agent_save_experience.py`. |
| P2.5 | Type hints + docstring pass on core modules     | ❌ Open | `core/resource_manager.py`, `core/manager_factory.py`. |
| P2.6 | REMAINING_ISSUES.md #6 magic numbers            | ❌ Open | Only remaining item from that doc after 2026-07-07 audit (N1-N4, #1-#5 all verified resolved). Readability only, no behavior change. |

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
- **2026-07-07** — Full re-audit. Installed missing `sc2`/`cffi` deps, fixed a real test-pollution bug (`asyncio.get_event_loop()` → `asyncio.run()` in `test_combat_phase_fsm.py`), fixed a real data-loss bug in RL checkpoint saving (`os.replace`, closes P2.4), adopted the unused `position_utils` helper to close `REMAINING_ISSUES.md` #5, and verified N1-N4/#3/#4 from that doc were already resolved (doc was stale). Found and logged two pre-existing CI issues (P0.1 black repo-wide failures, P0.2 `tests/unit` path mismatch) for a dedicated follow-up. Final: 508 pass / 14 skip / 0 fail.
