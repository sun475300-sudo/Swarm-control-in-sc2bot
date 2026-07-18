# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-18

---

## Snapshot (current state)

- Branch: `main`, last commit: queen transfusion + requirements-dev.txt session
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` runs black + isort + flake8 ✅ (all clean)
- **Test suite: 502 pass / 14 skip / 0 fail** ✅ (was 398/20/0 on 2026-05-03; gap between then and now had no nightly runs recorded)
- Queen transfusion logic: 3 bugs fixed (`is_idle` guard removed, target dedup, per-queen cooldown) ✅

## Resolved this run (2026-07-18)

| Item | File(s) | Notes |
|------|---------|-------|
| Order-dependent test failures in combat FSM suite | `tests/test_combat_phase_fsm.py` | 12 tests (`TestIdleToGathering`, `TestGatheringToPositioning`, `TestPositioningToEngagement`, `TestEngagementToActiveCombat`, `TestActiveCombatToRegrouping`) called `asyncio.get_event_loop().run_until_complete(...)` from sync test methods. When run after other test modules that use pytest-asyncio's auto-mode fixtures (which close and unset the thread's event loop on teardown), `get_event_loop()` raised `RuntimeError: There is no current event loop in thread 'MainThread'`. Passed in isolation, failed in the full suite — a real regression risk for CI. Replaced all 5 call sites with `asyncio.run(...)`, which creates and tears down its own loop and does not depend on thread-local loop state. Full suite now green: 502 passed / 14 skipped / 0 failed. |
| Verified `REMAINING_ISSUES.md` open items #3/#4 already fixed | `wicked_zerg_challenger/economy/queen_transfusion_manager.py`, `wicked_zerg_challenger/core/resource_manager.py` | Doc was stale (last touched 2026-04-27). Issue #3 (transfusion priority) already has a `HEAL_PRIORITY` table + sorted target selection. Issue #4 (resource reservation race) already has `asyncio.Lock`-guarded atomic reservation. `REMAINING_ISSUES.md` N1-N4 (duplicate-method F811 bugs) also independently re-verified clean via an AST scan for duplicate method names per class across `wicked_zerg_challenger/` — 0 found. |

## Resolved 2026-05-03 (previous run)

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

## P3 — Newly identified (2026-07-18 sweep)

Priority list built from a fresh `pyflakes` pass over `wicked_zerg_challenger/` plus a manual read of the
FSM controller touched this run. Ordered by likely runtime impact; the CI/tooling items (P3.5+) are
carried over from `MASTER_TODO_SC2.md` §1.6-1.8 since they're still unaddressed.

| #    | Item | Status | Notes |
|------|------|--------|-------|
| P3.1 | Dead `group_center` computation in combat FSM | ❌ Open | `combat_phase_controller.py:164` — `_get_group_center(group_units)` is computed every `_manage_group_phase` tick but never passed to any phase handler or used in transition checks. Either it's leftover from a refactor (safe to delete) or gathering/positioning should be using it for rally-point math and currently isn't (a real gap). Needs a human call on intent before touching — flagged for advisor review rather than blind deletion. |
| P3.2 | ~130 "local variable assigned but never used" (pyflakes) | ❌ Open | Mostly harmless (`except Exception as e` where `e` is unused, a few `game_time`/`style` locals). Bulk of these are cosmetic; worth a dedicated low-risk sweep but not urgent. `bot_step_integration.py` has the largest concentration (~12). |
| P3.3 | ~250 "f-string is missing placeholders" (pyflakes) | ❌ Open | Style-only (an f-string with no `{}`), spread across ~20 files. Safe to bulk-fix with a script but zero functional impact — lowest priority. |
| P3.4 | `ursina` star-import blocks undefined-name checking | ❌ Open | `wicked_zerg_challenger/visuals/swarm_3d_ursina.py` — `from ursina import *` hides ~95 potential undefined-name findings from static analysis in that one file. Only affects an optional 3D visualizer, not the bot core. |
| P3.5 | CI dependency resolution hardening | ❌ Open | `ci.yml` still uses plain `pip install -r requirements.txt` (prone to "resolution-too-deep"). Candidate: `uv pip install` or a `pip-tools` lockfile. See `MASTER_TODO_SC2.md` §1.7. |
| P3.6 | Lint tool consolidation (black+isort+flake8+mypy → ruff) | ❌ Open | `sc2bot-ci.yml`'s lint matrix runs 4 separate tools; `ruff` covers black-compatible formatting + isort-compatible import order + most flake8 rules at ~100x speed. See `MASTER_TODO_SC2.md` §1.8. |
| P3.7 | `REMAINING_ISSUES.md` / `MASTER_TODO_SC2.md` refresh | ❌ Open | Both docs are several months stale and describe issues already fixed (verified this run — see "Resolved this run" above). Next automation pass should do a full re-audit and either update or archive them to `docs/history/` per `STATUS.md`'s own recommendation (P1.5 pattern). |

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
- **2026-07-18** — Fixed order-dependent `asyncio.get_event_loop()` failures in `test_combat_phase_fsm.py` (12 tests). Re-verified `REMAINING_ISSUES.md` #3/#4 and `MASTER_TODO_SC2.md` N1-N4 already resolved (docs were stale). Final: 502 pass / 14 skip / 0 fail. New P3 backlog logged from a fresh pyflakes sweep.
