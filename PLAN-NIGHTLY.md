# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-14

---

## Snapshot (current state)

- Branch: `claude/optimistic-edison-pvmdcu` (from `main`)
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` runs black + isort + flake8 ✅ (all clean)
- **`tests/` suite: 502 pass / 14 skip / 0 fail** ✅
- **`wicked_zerg_challenger/tests/` suite: 661 pass / 0 fail** ✅
- Run the two suites as separate `pytest` invocations (see "Known limitation" below) — matches CI.
- Queen transfusion logic: 3 bugs fixed (`is_idle` guard removed, target dedup, per-queen cooldown) ✅

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
| P2.6 | Clean up F841 unused-variable warnings           | ❌ Open | 130 occurrences across `wicked_zerg_challenger/` (`flake8 --select=F841`), non-blocking in CI. |
| P2.7 | Fix `scripts` package name collision             | ❌ Open | Top-level `scripts/` vs `wicked_zerg_challenger/scripts/` collide when both test suites run in one pytest session. Only matters if the two CI steps get merged. |
| P2.8 | Whole-repo `black` formatting debt               | ❌ Open | `.github/workflows/ci.yml` "Lint & Type Check" job runs `black --check --diff .` (repo-wide, not diff-scoped) and fails: 65 files need reformatting (confirmed pre-existing on `main`, e.g. `wicked_zerg_challenger/strategy_manager.py`, `wicked_zerg_challenger/visuals/generate_presentation_visuals.py`). Mechanical fix (`black .`), but large blast radius — do as its own dedicated PR, not bundled into an unrelated bugfix. |
| P2.9 | ✅ Done — top-level `tests/` protobuf collection failure | ✅ Done | CI's "Python 린트 & 테스트" job failed all `tests/` collection with `TypeError: Descriptors cannot be created directly` — `s2clientprotocol`'s pre-generated `_pb2.py` files conflict with newer `protobuf` package's C++/upb backend. `wicked_zerg_challenger/tests/conftest.py` already worked around this with `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python`; applied the same fix to the top-level `tests/conftest.py` (2026-07-14). |

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
- **2026-07-14** — Fresh venv (`burnysc2`, `requirements-dev.txt`) built from scratch to run the suites. Fixed 12 failures in `tests/test_combat_phase_fsm.py` (Python 3.11 `asyncio.get_event_loop()` incompatibility → `asyncio.run()`). Removed dead no-op `try/except ImportError` stub in `combat_manager._zergling_early_harass`. Fixed mojibake-corrupted Korean comments in `wicked_zerg_challenger/tools/check_missing_logic.py`. Re-verified `REMAINING_ISSUES.md` N1-N4 and Issues #3-#5 against current code — all already resolved, doc was stale; updated it. Ran `check_missing_logic.py` project-wide scan (241 flagged "missing" methods, mostly false positives from a naive `self.x(...)` regex against RL module attributes — reviewed the 9 real `pass`-stub hits, only 1 was a genuine dead-code stub, now removed). Final: `tests/` 502 pass / 0 fail / 14 skip; `wicked_zerg_challenger/tests/` 661 pass / 0 fail. See `REMAINING_ISSUES.md` "다음 작업 우선순위" for the next-session priority list (P2.6/P2.7 added below).
