# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-08

---

## Snapshot (current state)

- Branch: `claude/optimistic-edison-04u5bc`
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` runs black + isort + flake8 (blocking: E9/F63/F7/F82 only)
- **Test suite: 507 pass / 14 skip / 0 fail** ✅ (was 468/15/0)
- Queen transfusion logic: 3 bugs fixed (`is_idle` guard removed, target dedup, per-queen cooldown) ✅
- ⚠️ `black --check .` currently fails on 66 pre-existing files repo-wide (not caused by this session — CI's blocking lint step doesn't include black, so it hasn't been caught). Worth a dedicated formatting pass.

## Resolved this run (2026-07-08)

| Item | File(s) | Notes |
|------|---------|-------|
| Test-order event-loop pollution | `tests/test_combat_phase_fsm.py` | 11 tests used `asyncio.get_event_loop().run_until_complete()`; `asyncio.run()` in `test_matchup_strategies.py` (which runs earlier alphabetically) resets the global event-loop policy to "no loop", so these 11 tests failed only when run as part of the full suite, never in isolation. Replaced with `asyncio.run()`. |
| **RL model checkpointing was silently broken** | `wicked_zerg_challenger/local_training/rl_agent.py` | `save_model()` built `tmp_path` via `.with_suffix(".tmp")`, but `np.savez()` auto-appends `.npz` to any name lacking it, so the file actually written was `*.tmp.npz` while the code checked `tmp_path` (`*.tmp`) — that check was always False, so the move-into-place step never ran. The function still returned `True` and logged success. Fixed by giving the tmp path an explicit `.npz` ending. |
| Non-atomic "atomic" save | `rl_agent.py` (`save_model`, `save_experience_data`) | Both deleted/moved the destination file in two separate syscalls (`remove()`+`rename()`, or `unlink()`+`move()` with a `copy+delete` fallback) — a crash between the two steps loses the previous good file with nothing complete to replace it. Switched both to a single `os.replace()`, which is atomic on POSIX and Windows. |
| No regression coverage for the above | `tests/test_rl_agent_atomic_save.py` (new, 5 tests) | Covers no-leftover-tmp-file and correct-data-after-overwrite for both save paths. This is PLAN-NIGHTLY P2.4. |
| `REMAINING_ISSUES.md` stale for months | doc | Re-verified N1-N4 (F811 dupes) and Issue #3/#4/#5 (transfusion priority, resource-reservation lock, position utils) against current code via `flake8 --select=F811` and direct grep — all were already implemented in prior sessions but the doc still listed them "open". Trimmed and corrected. |

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
| P2.4 | RL agent save-experience guard                  | ✅ Done | Fixed the underlying non-atomic-save + broken-tmp-path bugs (see above) and added 5 regression tests in `tests/test_rl_agent_atomic_save.py`. |
| P2.5 | Type hints + docstring pass on core modules     | ❌ Open | `core/resource_manager.py`, `core/manager_factory.py`. |
| P2.6 | Repo-wide `black --check .` failure (66 files)  | ❌ Open | Not blocking CI today since the blocking lint step only checks E9/F63/F7/F82, but the non-blocking `black --check --diff .` step in the other workflow will show red. Needs a dedicated formatting-only PR. |
| P2.7 | Bare `except Exception:` cleanup (460 occurrences) | ❌ Open | `REMAINING_ISSUES.md` N5. Large, do incrementally per-file. |

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
- **2026-07-08** — Fixed test-order event-loop pollution (P2.1 FSM tests), discovered + fixed silently-broken RL model checkpointing (P2.4), switched RL save paths to true atomic `os.replace()`, added 5 regression tests, re-verified and corrected stale `REMAINING_ISSUES.md`. Final: 507 pass / 14 skip / 0 fail.
