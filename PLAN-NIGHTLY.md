# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-10

---

## Snapshot (current state)

- Branch: `claude/optimistic-edison-9i8tj7` (from `main`)
- Bot core: `wicked_zerg_challenger/` — 417+ Python files across 10+ subdirs (py_compile: 0 errors).
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` runs black + isort + flake8 ✅; flake8 critical (E9/F63/F7/F82) clean across whole repo.
- **Test suite (root `tests/`): 502 pass / 14 skip / 0 fail** ✅
- **Test suite (`wicked_zerg_challenger/tests/`): 661 pass / 0 fail** ✅ (was silently passing 18 dead async tests before this session — see 2026-07-10 entry)
- Note: previous "398/468 pass" snapshots above measured a different, smaller subset — this session installed the real dependency set (numpy/burnysc2/scipy/etc, skipping the `mpyq` sdist which fails to build here) and ran the full suite for the first time in a while; counts above are not directly comparable to older entries.
- Queen transfusion logic: 3 bugs fixed (`is_idle` guard removed, target dedup, per-queen cooldown) ✅ (still holds, re-verified)

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

*No P0 items this run.* (2026-07-10: found and fixed two test-infrastructure correctness bugs — see Run history below — neither blocked this run since they were fixed same-session.)

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
| P2.1 | Force-accumulation FSM tests                    | ✅ Done | `tests/test_combat_phase_fsm.py` — 23 tests all passing in isolation, but were order-dependent (failed when run after `test_combat_manager.py` in the full suite) due to bare `asyncio.get_event_loop()` — fixed 2026-07-10 (`asyncio.run()`). |
| P2.2 | Benchmark runner                                | ❌ Open | `wicked_zerg_challenger/run_mass_test.py` already covers N-games + win-rate; still missing APM/supply reporting vs Hard specifically — needs a closer look before calling this fully open or done. |
| P2.3 | Build-order config externalisation              | ❌ Open | Move top-20 hardcoded values to `config/build_orders.yaml`. |
| P2.4 | RL agent save-experience guard                  | ✅ Done | `local_training/rl_agent.py:637 save_experience_data` already did atomic temp-file+rename with try/except; added `tests/test_rl_agent_save_experience.py` (5 tests: success, nested-dir creation, overwrite, disk-full-preserves-existing-file, disk-full-no-existing-file). |
| P2.5 | Type hints + docstring pass on core modules     | ❌ Open | `core/resource_manager.py`, `core/manager_factory.py`. |
| P2.6 | Wire Sprint-4.5 combat frame-skip into live path | ❌ Open (new) | `combat_manager.manage_combat`/`_should_skip_combat_frame` is tested (`tests/test_sprint4_combat_micro.py`) but never called from the real on_step path — `bot_step_integration.py` calls `combat.on_step()` directly via `_safe_manager_step`, bypassing it. `logic_optimizer.py` separately hardcodes Combat to `interval=1` (every frame). Needs a live-game (or replay) check before changing cadence — can't safely validate combat responsiveness in this sandbox (no SC2 client). See `REMAINING_ISSUES.md` N7. |

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
- **2026-07-10** — Full re-verification from a clean environment (installed numpy/burnysc2/scipy/etc; `mpyq` sdist fails to build here but `sc2` imports fine without it). Findings:
  - Renamed root `pytest/` dir → `python_pytest_example/` (collided with the real `pytest` package under `python -m pytest`, breaking `run_combat_tests.bat`/`PUSH_FIX_TO_MAIN.bat`).
  - Added `cffi>=1.15.0` to `requirements.txt` (silent hard dependency of `cryptography` in this environment; without it 8 crypto/security tests fail with `pyo3_runtime.PanicException`).
  - Fixed `tests/test_combat_phase_fsm.py`: 5 helpers used bare `asyncio.get_event_loop().run_until_complete(...)`, which raised `RuntimeError: There is no current event loop` when run after other async tests in the full suite (order-dependent flake, invisible when the file is run alone). Switched to `asyncio.run(...)`.
  - Found and fixed 18 test methods across `wicked_zerg_challenger/tests/test_production_resilience.py` and `test_opponent_modeling.py` that were `async def test_...` on a plain `unittest.TestCase` — the coroutines were never awaited, so the tests always "passed" without running their bodies. Switched both classes to `unittest.IsolatedAsyncioTestCase`; 3 of the newly-live `_get_counter_unit` tests then failed for real (stale call signature) and were rewritten against the current `(enemy_units, has_roach_warren, has_hydra_den, has_spire)` signature.
  - Cross-checked `REMAINING_ISSUES.md` Issues #3–#6 and N1–N4 against code: all already implemented in prior sessions: doc was stale, not the code. Updated `REMAINING_ISSUES.md` accordingly.
  - New finding not yet fixed: P2.6 / N7 above (Sprint 4.5 combat frame-skip is dead code).
  - **Final: root `tests/` 502 pass / 14 skip / 0 fail. `wicked_zerg_challenger/tests/` 661 pass / 0 fail (0 silently-skipped-coroutine tests remaining).**
