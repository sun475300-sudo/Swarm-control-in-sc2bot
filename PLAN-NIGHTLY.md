# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-14

---

## Snapshot (current state)

- Branch: `main`, last commit: queen transfusion + requirements-dev.txt session
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` runs black + isort + flake8 ✅ (all clean per prior run; **black is
  currently NOT clean repo-wide** — see Known Issues below, found 2026-07-14)
- **Test suite: 1167 pass / 14 skip / 0 fail** ✅ (`tests/` + `wicked_zerg_challenger/tests/`
  combined, 2026-07-14 — up from 468/15/0, suite has grown substantially since last refresh)
- Queen transfusion logic: 3 bugs fixed (`is_idle` guard removed, target dedup, per-queen cooldown) ✅

## Resolved this run (2026-07-14)

| Item | File(s) | Notes |
|------|---------|-------|
| Test-order-dependent failures (12 tests) | `tests/test_combat_phase_fsm.py` | `_run()` helpers used `asyncio.get_event_loop().run_until_complete(...)`. Once any earlier test in the run made pytest-asyncio call `asyncio.set_event_loop(None)` at teardown, `get_event_loop()` stopped auto-creating a loop and raised `RuntimeError: There is no current event loop`. Replaced all 5 call sites with `asyncio.run(...)`, which owns its own loop lifecycle regardless of global state. |
| Cross-file import poisoning | `tests/test_production_resilience.py` | Test inserted `wicked_zerg_challenger/local_training` directly onto `sys.path` (in addition to `wicked_zerg_challenger`, which was the only insert actually needed). That exposed `local_training/scripts/` — a **regular** package (has `__init__.py`) — as the top-level `scripts` module. Once Python resolved `scripts` to that path first, `wicked_zerg_challenger/tests/test_ladder_tracker.py` and `test_meta_adapter.py` (which need the real root-level `scripts/ladder_tracker.py` / `scripts/meta_adapter.py`) failed with `ModuleNotFoundError: No module named 'scripts.ladder_tracker'` for the rest of the run. Removed the unnecessary sys.path insert. |
| Non-atomic experience save (data-loss window) | `wicked_zerg_challenger/local_training/rl_agent.py` (`RLAgent.save_experience_data`) | Old code did `os.remove(path)` then `os.rename(tmp, path)` — if the rename step failed (disk full, interrupted process, permission error) between those two calls, the previously-saved experience file was gone with nothing to replace it: a real data-loss bug, not just non-atomic in theory. Replaced with a single `os.replace(tmp, path)` (atomically overwrites on both POSIX and Windows) and added best-effort temp-file cleanup on failure. Closes PLAN-NIGHTLY P2.4 (guard test now exists). |
| P2.4 guard test (new) | `tests/test_rl_agent_save_experience.py` | 4 new tests: successful save, no leftover temp file on success, existing file survives a forced `os.replace` failure, temp file cleaned up after a forced failure. |
| Broken CI job (`sc2bot-ci.yml`) | `.github/workflows/sc2bot-ci.yml` | The `test` job's "Run unit tests" step ran `pytest tests/unit` — that directory has never existed in this repo (only `tests/integration` does), so this job has been failing on every push/PR. Repointed at `pytest tests/ wicked_zerg_challenger/tests/ --ignore=tests/integration` (also picks up `requirements-dev.txt` so pytest-asyncio/mock/timeout plugins are installed) — this also means the ~650 tests under `wicked_zerg_challenger/tests/` start running in CI for the first time. |

## Known issues (found 2026-07-14, not yet fixed)

- **`black --check --diff .` is not clean repo-wide.** The `lint` job in `sc2bot-ci.yml` runs
  this without `continue-on-error`, so CI's lint job is likely red independent of any code
  change. Needs a repo-wide `black .` pass (large, mechanical diff — do as its own PR, not
  bundled with logic changes) or relaxing the CI gate. Not fixed this run to avoid an
  unreviewable mega-diff riding along with the bug fixes above.
- `REMAINING_ISSUES.md` was stale: Issues #3 (transfusion priority), #4 (resource-reservation
  lock), #5 (position_utils dedup) were all already implemented in code
  (`queen_manager._transfuse_injured_units`, `economy_manager`/`resource_manager.try_reserve`,
  `utils/position_utils.py`) — doc updated to reflect reality instead of re-doing the work.

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
| P2.1 | Force-accumulation FSM tests                    | ✅ Done | `tests/test_combat_phase_fsm.py` — 23 tests all passing (fixed a test-order-dependent failure in this file 2026-07-14). |
| P2.2 | Benchmark runner                                | ❌ Open | Single command, N replays, APM/supply/win-rate report vs Hard. |
| P2.3 | Build-order config externalisation              | ❌ Open | Move top-20 hardcoded values to `config/build_orders.yaml`. |
| P2.4 | RL agent save-experience guard                  | ✅ Done | Fixed a real data-loss window in `save_experience_data` (remove-then-rename → `os.replace`) + 4 new tests in `tests/test_rl_agent_save_experience.py` (2026-07-14). |
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
- **2026-07-14** — Full-suite run (`tests/` + `wicked_zerg_challenger/tests/`, 1173 collected): fixed a test-order-dependent event-loop failure (`test_combat_phase_fsm.py`), a `sys.path` import-poisoning bug (`test_production_resilience.py` breaking `test_ladder_tracker.py`/`test_meta_adapter.py`), a real data-loss window in `RLAgent.save_experience_data` (closes P2.4), and a broken `sc2bot-ci.yml` test job pointing at a nonexistent `tests/unit` directory. Final: 1167 pass / 14 skip / 0 fail. Flagged (not fixed): `black --check` not clean repo-wide.
