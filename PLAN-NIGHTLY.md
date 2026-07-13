# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-05-04

---

## Snapshot (current state)

- Branch: `main`, last commit: queen transfusion + requirements-dev.txt session
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` runs black + isort + flake8 ✅ (all clean)
- **Test suite: 468 pass / 15 skip / 0 fail** ✅ (was 398/20/0 two nights ago)
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
| P2.2 | Benchmark runner                                | 🟡 Partial | `run_mass_test.py` exists (single-command, N games, win-rate by difficulty/race, JSON report) but has no APM or supply tracking — spec's "APM/supply" half is still open. |
| P2.3 | Build-order config externalisation              | ❌ Open | `build_order_system.py` still hardcodes `ZVT_BUILDS`/`ZVP_BUILDS`/`ZVZ_BUILDS` as Python dicts; no `config/build_orders.yaml` exists anywhere in the repo (verified 2026-07-13). |
| P2.4 | RL agent save-experience guard                  | ✅ Done | `wicked_zerg_challenger/tests/test_rl_agent_save_guard.py` (landed via open PR #434, not yet merged to `main`). |
| P2.5 | Type hints + docstring pass on core modules     | ✅ Done | Verified 2026-07-13: `core/resource_manager.py` and `core/manager_factory.py` already have full type hints and Args/Returns docstrings on every method. Doc was stale. |

## Resolved this run (2026-07-13)

| Item | File(s) | Notes |
|------|---------|-------|
| `tests/test_combat_phase_fsm.py` asyncio crash | `tests/test_combat_phase_fsm.py` | `asyncio.get_event_loop().run_until_complete(...)` raises `RuntimeError: no current event loop` on Python 3.11 under pytest-asyncio auto mode. Replaced 5 call sites with `asyncio.run(...)`. This exact bug had already been independently re-discovered and fixed in ~9 open, unmerged draft PRs (#428-#437) — see governance note below. |
| `requirements.txt`, `wicked_zerg_challenger/requirements.txt` | pins | Added `async_timeout>=4.0.0` (burnysc2 imports it but modern `aiohttp` no longer pulls it in transitively — silent `ImportError` degrades `sc2` imports to broken dummy stubs in modules with unguarded try/except) and `cffi>=1.15.0` (cryptography's Rust backend needs it explicitly on some resolves). |
| ROADMAP Sprint 4.4 "다방면 협공 — 동시 도착을 위한 거리 역산" | `wicked_zerg_challenger/combat/multi_prong_coordinator.py` | Implemented: `_compute_departure_times()` estimates per-prong travel time from centroid distance / representative unit speed, delays faster/closer prongs so all prongs' estimated arrival times line up; `_execute_multi_prong()` holds undeparted units in place instead of attacking early. 7 new regression tests in `tests/test_multi_prong_coordinator.py`. Group-size ratio (60/25/15%) from the same task spec is still open. |
| Doc audit | `ROADMAP.md`, `REMAINING_ISSUES.md`, this file | Verified P2.5 and REMAINING_ISSUES #3/#4 were already done (docs were stale); confirmed P2.2 and P2.3 are genuinely still open; confirmed Sprint 7.3 (magic-number → `GameConstants` migration) is only ~11% adopted (24 named-constant call sites vs. ~195 raw `% <n>` frame-count checks across 72 files) — flagged as a large, low-risk-per-file but high-file-count cleanup candidate, not attempted this run. |

**Test suite: 502 pass / 14 skip / 0 fail (`tests/`) + 668 pass / 0 fail (`wicked_zerg_challenger/tests/`, +7 new)** — both trees must be run as separate `pytest` invocations; running them together still hits the pre-existing `scripts` package name collision (documented in PR #430, not yet fixed on `main`).

### ⚠️ Process/governance note (important — repo owner action needed)

As of 2026-07-13 this repository has **~10 open draft PRs** (`#428`–`#437`, all `claude/optimistic-edison-*`) that independently rediscover and fix the *same* `asyncio.get_event_loop()` bug and `async_timeout` pin — none merged. `main`'s last merge was PR #218. Every automated session re-derives the same baseline from scratch because nothing lands. Recommend the repo owner merge one canonical fix (e.g. #437, the most recent and broadest-verified) and close the other ~9 as duplicates, so future nightly runs start from a fixed baseline instead of re-finding the same issue. This session did not merge or close anything — that's a repo-owner decision, not something to do unilaterally from an automated loop.

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
- **2026-07-13** — Fixed the recurring `asyncio.get_event_loop()` FSM test crash (12 tests) and pinned `async_timeout`/`cffi`. Implemented ROADMAP Sprint 4.4 simultaneous-arrival departure staggering for multi-prong attacks (+7 tests). Verified P2.5 and REMAINING_ISSUES #3/#4 already resolved (stale docs updated); confirmed P2.2/P2.3 genuinely open. Flagged the ~10-PR unmerged-duplicate backlog for repo-owner triage.
