# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-10

---

## ⚠️ Governance alert (2026-07-10) — read before starting a new session

This repo has **340 open pull requests** (`gh pr list`/GitHub search, 2026-07-10),
almost all opened by this same nightly automated loop since 2026-04-20, and
**only PR #218 has ever been merged**. `main`'s last commit is 2026-06-25
("Update ci.yml") — **15 days with zero merges** despite a continuous nightly
test/fix cycle. Dozens of the open PRs (at least #369–#378) independently
re-fix the *exact same two bugs* (the `tests/unit` CI path that doesn't exist,
and `asyncio.get_event_loop()` flakiness in `test_combat_phase_fsm.py`) because
each session starts fresh from a stale `main` that never absorbs prior fixes.

**This is very likely the single highest-priority blocker for real progress.**
None of these sessions (including this one) has repo-owner authority to
bulk-merge/close PRs unilaterally — that decision needs the owner
(sun475300-sudo) to either merge the best candidate (e.g. #372, which bundles
the CI path fix + asyncio fix + black/isort + wires `wicked_zerg_challenger/tests`
into CI, verified clean) and close the superseded duplicates, or explicitly
authorize an automated session to do so. Until that happens, expect every
future nightly session to keep rediscovering already-fixed issues.

## Snapshot (current state)

- Branch: `main` @ `8a80b73` ("Update ci.yml", 2026-06-25). Working session on
  `claude/optimistic-edison-3nyi7o`.
- Bot core: `wicked_zerg_challenger/` — 180+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` — test job path (`pytest tests/unit`) is still broken on
  `main` as of this refresh; see governance alert above (several unmerged PRs
  already fix it, none landed).
- **Test suite (this session, clean env): `tests/` 502 pass / 14 skip / 0 fail;
  `wicked_zerg_challenger/tests/` 667 pass / 0 fail** (was 490/12-fail/14-skip
  and 661/0-fail respectively before this session's fixes below).

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
- **2026-07-10** — Nightly test/inspect cycle. Found the 340-open-PR governance
  problem (see alert above) — recommend repo owner action before any more
  sessions duplicate work. Fixed real issues in this PR:
  - `tests/test_combat_phase_fsm.py`: 12 tests failed with
    `RuntimeError: no current event loop` — `asyncio.get_event_loop()` →
    `asyncio.run(...)` (same root cause independently found/fixed by ~10 other
    open PRs; not a new discovery, but needed for this session's own suite to
    be green).
  - **Issue #5 actually wired in** (was previously only claimed done in
    unmerged drafts): `utils/position_utils.get_center_position()` existed but
    had 0 callers and couldn't even be imported without `sc2` installed
    (unguarded `from sc2.position import Point2`, unlike every sibling module).
    Fixed the import guard, then replaced 11 duplicate inline centroid
    calculations across `combat_manager.py`, `micro_controller.py`,
    `combat_phase_controller.py`, `combat/micro_combat.py` (x2),
    `combat/infestor_tactics.py`, `combat/combat_execution.py`,
    `combat/expansion_defense.py`, `battle_preparation_system.py`, and
    `idle_unit_manager.py` with real calls to it. Added
    `wicked_zerg_challenger/tests/test_position_utils.py` (6 tests, including
    one that blocks `sc2` via `sys.meta_path` to lock in the import-guard fix).
  - Re-verified N1-N4 (duplicate method defs) via a fresh AST scan — still 0
    duplicates, confirming several previous sessions' claims. Re-verified
    Issue #3 (transfusion priority) and Issue #4 (resource reservation lock)
    are genuinely implemented and wired in. Updated `REMAINING_ISSUES.md`
    accordingly.
  - Test suite: `tests/` 502 pass/14 skip (was 490 pass/12 fail before the
    asyncio fix), `wicked_zerg_challenger/tests/` 667 pass (was 661, +6 new).
