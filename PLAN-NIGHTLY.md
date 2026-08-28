# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-19

---

## 🔴 P0 finding (2026-07-19): the recurring automation loop itself, not missing fixes, is now the blocker

- **~507 open PRs against `main`, only 2 ever merged** (#218, #533). Confirmed via `search_pull_requests`.
- At least 8 independent prior sessions today alone (#543–#550) reached the same conclusion and recommended the same thing: stop commissioning more one-off fix PRs, triage the backlog instead.
- One session (#548) measured PR creation timestamps and found ~13 PRs opened within a single hour on 2026-07-18 — inconsistent with the requested "daily" cadence. The trigger/schedule that invokes this recurring session is very likely firing far more often than intended.
- This session (PR #551) could not inspect or change that trigger config from inside the repo (`CronList` is session-scoped and empty — the trigger lives in the Claude Code on the web environment settings, outside this session's reach). **Action needed from the repo owner:** check the trigger/schedule configured for this repo in the Claude Code on the web UI and confirm it's actually set to daily, not hourly-or-more.
- Several already-open PRs fix real, independently-verified bugs and are ready for owner review/merge: **#544** (`RLAgent.save_model()` atomic-rename no-op), **#545** (race-specific upgrade priority never applied), **#549** (`IntegrationHub.generate_test_script()` crash), **#550** (5 state-machine bugs where a transient signal permanently latches a degraded mode), **#551** (this session — opponent-learning crash, see below).

## Resolved this run (2026-07-19, PR #551)

`OpponentModeling.on_game_end()` (`wicked_zerg_challenger/opponent_modeling.py`) re-accessed `.value` on strings already stored by `_add_signal()` (`observed_signals` holds `StrategySignal.value`, not the enum member) — raised `AttributeError` on every game where any early-game signal fired (early pool, fast expand, etc. — routine). Silently swallowed by a broad `except Exception` in `wicked_zerg_bot_pro_impl.py`'s `on_end()`, so `model.update_from_game()`/`save_models()` never ran: **opponent-learning persistence silently never worked**. Also fixed: dead writes to non-existent `game_won`/`game_lost` fields (real field is `game_result`), and a masked `.models` → `.opponent_models` typo one line below that only stayed hidden because the above bug threw first. 2 regression tests added. `wicked_zerg_challenger/tests/` 661 → 663 passed, `tests/` unchanged at 502 passed/14 skipped.

## Other candidates found this run, not yet fixed (flagged for a future session — do not re-discover from scratch)

- `harassment_coordinator.py`: `zergling_runby_active` is set `True` once and never reset — permanently disables `MultiProngCoordinator` attack initiation and synchronized-strike run-bys after the first zergling run-by of the game. Same "transient flag never resets" shape as the 5 bugs already fixed in PR #550 — worth checking whether #550's pattern-fix approach can extend here.
- `advanced_scout_system_v2.py`: the zergling-patrol dispatch path never registers units into `_patrol_units`, so `active_scouts` permanently latches at `MAX_SCOUTS["ZERGLING"]` and silently kills further zergling scouting after ~3-4 minutes.
- `advanced_micro_controller_v3.py`: 5 sub-classes (`RavagerMicro`, `LurkerMicro`, `QueenMicro`, `ViperMicro`, `CorruptorMicro`) have exception handlers referencing `self.logger`, which is never initialized in `__init__` — any exception path in these classes raises a second `AttributeError` masking the original error.

---

## 🔴 P0 finding (2026-07-18): CI itself was blocking every merge

As of 2026-07-18 the repo had **494 open PRs and only 8 ever merged**
(last merge: PR #218, 2026-06-01). Root cause: `sc2bot-ci.yml`'s `test`
job depends on `lint`, and `lint` runs `black --check --diff .` /
`isort --check-only --diff .` against the **whole repo**. `main` had
66 files that already failed `black --check`, so `lint` failed on
every PR regardless of content, `test` never ran, and CI could never
go green. Once that was fixed (PR #533), the `test` job ran for the
first time ever and immediately surfaced three more real CI bugs:
wrong test path (`tests/unit` doesn't exist), missing `pytest-timeout`
for the `--timeout=120` flag, `wicked_zerg_challenger/tests/` (661
tests, most of the actual bot-logic coverage) never wired into CI at
all, and a missing `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` env
var (needed because `s2clientprotocol`'s generated `_pb2` files predate
the installed protobuf runtime's C++ backend) in **both** `ci.yml` and
`sc2bot-ci.yml`. See PR #533 for the full diff/fix.

**Action needed from the repo owner:** merge PR #533 first, then decide
a policy for the other ~490 open PRs (rebase + re-review in batches,
enable auto-merge on green CI, or close superseded duplicates) — CI
being permanently red is very likely why none of them ever merged.

## Snapshot (current state)

- Branch: `main`, last commit: queen transfusion + requirements-dev.txt session
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` runs black + isort + flake8 — **was red on every PR since before 2026-06-01; fixed in PR #533 (2026-07-18), pending merge**
- **Test suite (local verification, 2026-07-18): `tests/` 502 passed/14 skipped, `tests/integration` 10 passed, `wicked_zerg_challenger/tests/` 661 passed — 0 failures across all three**
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
