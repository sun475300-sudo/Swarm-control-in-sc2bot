# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-14

---

## ⚠️ CRITICAL: PR pileup — nothing has merged since PR #218

- `main` is still exactly at PR #218 (`Merge PR #218: stabilize SC2 bot test suite and iterate on improvements`).
- There are **30 open draft PRs** (`#439`–`#468`, all on `claude/optimistic-edison-*` branches) stacked on top of that,
  almost every one titled some variant of "fix: combat FSM event-loop bug / CI test path / sc2 import guard".
- Each session re-discovers and re-fixes the **same two bugs** in its own branch, commits, opens a new PR, and stops —
  none get merged, so the fix never reaches `main` and the next session finds the bug again. This nightly loop only
  compounds the pile unless PRs actually land.
- **Recommendation to owner**: pick one PR (latest, #468, or have an agent squash the redundant ones into a single
  branch) and merge it, then close the rest. Until that happens, treat every new "fix" PR from this loop as
  low-value — the code fix is real, but it's stuck exactly where the previous 30 attempts got stuck.
- This session did **not** close or merge anything (repo policy: merge/close decisions require owner approval).

## Snapshot (current state)

- Branch: `main`, last commit: `8a80b73 Update ci.yml` (still == PR #218 head; 0 commits landed since).
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- **Test suite (this session, sandboxed, no `sc2`/`burnysc2` installed): 395 pass / 34 skip / 0 fail** ✅
  (was 1 collection error blocking the whole suite + 12 failing before today's fixes — see below)
- Queen transfusion logic (from PR #218 era): `is_idle` guard removed, target dedup, per-queen cooldown ✅

## Resolved this run (2026-07-14)

| Item | File(s) | Notes |
|------|---------|-------|
| Collection error blocked entire suite | `tests/test_queen_transfusion.py` | Unguarded `from sc2.ids.unit_typeid import UnitTypeId` at module scope crashed collection in any env without `sc2` installed (sandbox/CI-lint jobs), aborting **all 423 tests**, not just this file. Wrapped in `try/except ImportError: pytest.skip(..., allow_module_level=True)`, matching the guard already used in the sibling file `test_queen_transfusion_manager.py`. |
| 12 combat-FSM tests fail with `RuntimeError: There is no current event loop in thread 'MainThread'` | `tests/test_combat_phase_fsm.py` | 5 call sites used `asyncio.get_event_loop().run_until_complete(...)`, which breaks on Python 3.11 once any prior test (via `pytest-asyncio`'s per-test loop) has already closed the thread's default loop. Replaced all 5 with `asyncio.run(...)`, which owns its own loop lifecycle. This is the exact bug that ~15 of the 30 piled-up PRs (titles: "event-loop crash in combat FSM tests", "Python 3.11 asyncio bug breaking 12 combat FSM tests", etc.) independently diagnosed and fixed in their own unmerged branches. |
| Sandbox test env missing `pytest-asyncio`/`pytest-timeout`/`pytest-mock` | n/a (env only, not committed) | `pytest` in this sandbox is a `uv tool install`, isolated from the system Python `pip install` target — installed the plugins into the tool venv via `uv tool install pytest --with pytest-asyncio --with pytest-timeout --with pytest-mock --force`. Not a repo change; noting here so the next session doesn't re-diagnose it. |
| CI job `python-lint-test` ("Python 린트 & 테스트") failing on PR #469 with `TypeError: Descriptors cannot be created directly` across 14 test files | `.github/workflows/ci.yml` | Real `sc2`/`s2clientprotocol` is installed in this job (unlike the sandbox), and its bundled `_pb2.py` files were generated against an older protobuf runtime than what pip now installs — breaks under strict-mode protobuf ≥4. Pre-existing on `main`: commit `8a80b73` ("Update ci.yml", 2026-06-25, direct push by owner) removed the `\|\| true` swallow from this step's two pytest commands, which had been silently hiding this exact failure. The sibling job `sc2-bot-test` already sets `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION: python` for the same reason — added the same env var to `python-lint-test`'s pytest step to match. |

**Net result: 1 collection error + 12 failures → 0 failures. Suite: 395 pass / 34 skip. Plus one CI env fix (protobuf pure-Python mode) surfaced by PR #469's checks.**

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
- **2026-07-14** — Flagged 30-PR pileup (#439–#468, nothing merged since #218). Fixed sc2-import collection error (`test_queen_transfusion.py`) + 12 combat-FSM `asyncio.get_event_loop()` failures (`test_combat_phase_fsm.py` → `asyncio.run()`). Suite: 395 pass / 34 skip / 0 fail.
