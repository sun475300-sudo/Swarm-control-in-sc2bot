# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-20

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

- Branch: `claude/optimistic-edison-wd3iv0`
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` runs black + isort + flake8 — **was red on every PR since before 2026-06-01; fixed in PR #533 (2026-07-18), pending merge**
- **Test suite (local verification, 2026-07-20): `tests/` 502 passed/14 skipped, `wicked_zerg_challenger/tests/` 661 passed → after this run's fixes, 673 passed — 0 failures across both**
- Queen transfusion logic: 3 bugs fixed (`is_idle` guard removed, target dedup, per-queen cooldown) ✅

## Resolved this run (2026-07-20)

| Item | File(s) | Notes |
|------|---------|-------|
| RL experience save could permanently lose data | `local_training/rl_agent.py` | `save_experience_data()` removed the destination file before renaming the temp file in; a failure between those two steps (disk full, interrupted write) destroyed the last-known-good data instead of just failing the update — an orphaned `.tmp.npz` in the repo was evidence this had happened. Switched to `os.replace()` (atomic, no unsafe window) + temp-file cleanup on failure. New test: `tests/test_rl_agent_save_experience.py` (P2.4, now done). |
| `formation_manager.py` crashed on every real direction computation | `combat/formation_manager.py` | `Point2.normalized` is a `@property` in the installed python-sc2 version, not a method — every `.normalized()` call (5 call sites) raised `TypeError: 'Point2' object is not callable` whenever the direction vector was non-zero, i.e. on every real in-game call. No test exercised these paths with a non-origin base position, so `form_concave`/`get_optimal_position` had effectively never worked at runtime. Fixed all 5 sites to use property access. New tests: `tests/test_formation_manager_roach_hydra.py`. |
| Roach-hydra combined formation (ROADMAP.md Task 4.3) | `combat/formation_manager.py` | Confirmed genuinely missing by a code audit (everything else in ROADMAP.md Sprints 1-8 was already implemented). Roaches now hold the front line toward the enemy; hydralisks hold a rear line 6 range back; only activates when both types are present, other compositions unaffected. |

## Resolved previous run (2026-05-03)

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
| P2.4 | RL agent save-experience guard                  | ✅ Done | Fixed real data-loss bug in `save_experience_data()` (see 2026-07-20 run) + regression test. |
| P2.5 | Type hints + docstring pass on core modules     | ❌ Open | `core/resource_manager.py`, `core/manager_factory.py`. |
| P2.6 | `utils/game_constants.py` is dead code           | ❌ Open | 241 lines of constants (`GameFrequencies`, `EconomyConstants`, etc.) fully defined but zero references anywhere in the codebase — either wire in to replace the magic numbers it was meant to replace, or remove. |

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
- **2026-07-20** — Fresh baseline confirmed clean (502/14/0 in `tests/`, 661/0/0 in `wicked_zerg_challenger/tests/`, matching 2026-07-18 exactly — no regressions). Audited ROADMAP.md against actual code: nearly all Sprint 1-8 items already implemented; only two real gaps found (roach-hydra formation, dead `GameConstants` module). Fixed P2.4 (RL experience save could permanently lose data on rename failure — real bug, not just a missing test). Found and fixed a second, more severe bug: `formation_manager.py` crashed on every real (non-origin-base) direction computation because `.normalized()` was called as a method on what is actually a `@property` in the installed python-sc2 version — the entire formation system had never worked at runtime. Implemented the roach-hydra formation (ROADMAP Task 4.3). Suite grew to 673 passing in `wicked_zerg_challenger/tests/`, 0 failures.
