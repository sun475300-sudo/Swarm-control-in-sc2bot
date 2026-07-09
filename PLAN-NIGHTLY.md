# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-09

---

## ⚠️ GOVERNANCE ALERT (2026-07-09) — read this before starting a new test/fix cycle

The repo currently has **334 open pull requests**, almost all opened by this same
nightly automation loop since **2026-04-20**, and **none of them have ever been
merged**. `main` is still sitting near where it was months ago while dozens of
branches independently re-fix the *same* handful of root problems:

- `sc2bot-ci.yml`'s `test` job calling `pytest tests/unit` (a directory that has
  never existed) — refixed by at least ~60 separate PRs (#313–#372 alone) in the
  last 3 days.
- `asyncio.get_event_loop()` order-dependent crashes in `test_combat_phase_fsm.py`.
- black/isort formatting drift blocking the `lint` → `test` dependency chain.

**PR #372** (`claude/optimistic-edison-3jsqye`, opened 2026-07-09, base = current
`main` tip, `mergeable_state: clean`, all 23 checks green) already contains a
verified fix for all three: 502 (root `tests/`) + 661 (`wicked_zerg_challenger/tests/`)
+ 10 (`tests/integration/`) = **1173 passed, 0 failed, 14 skipped (env-gated)**.

**Recommendation:** merge #372, then close the ~333 other stale duplicates (most
predate it and are superseded). Until that happens, every new automated session
should **check `list_pull_requests(state=open)` for an existing fix before
re-doing the CI-path/asyncio/formatting work** — this doc alone wasn't enough to
prevent 300+ duplicates, so the check needs to happen in-session, not just in docs.
This is flagged for the repo owner to confirm before any bulk merge/close, since
that's a shared-state action outside a single session's authority.

## Snapshot (current state)

- Branch: `main` @ `8a80b73` ("Update ci.yml", manual, 2026-06-25).
- Bot core: `wicked_zerg_challenger/` — 417+ Python files across 10+ subdirs (grew from 179 in May).
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` lint job (black/isort/flake8) is clean on `main`, but the
  **`test` job has been broken since it was written** (`pytest tests/unit` — nonexistent
  path, exit code 4 every run) — see Governance Alert above. Fix is ready in PR #372,
  unmerged.
- Static sweep this run: `py_compile` clean across all of `wicked_zerg_challenger/`;
  AST scan for duplicate method defs within a class → **0 found** (the N1–N4 items in
  `REMAINING_ISSUES.md` — duplicate `on_step`/`_prevent_resource_banking`/
  `_find_harass_target`/`build_terran_counters` — are already fixed in the code that
  doc just hadn't been updated to reflect).
- `economy/queen_transfusion_manager.py` — `REMAINING_ISSUES.md` Issue #3 (priority-based
  smart transfusion) is fully implemented and wired into `bot_step_integration.py`
  (`Phase 21` init), not just proposed.

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

## Run history

- **2026-04-25** — Initial nightly plan.
- **2026-04-26** — P0.2 (empty-logger CI guard) landed.
- **2026-04-27** — black + isort + flake8 all clean.
- **2026-04-28** — Harassment retraction logic hardened (P1.2).
- **2026-05-01** — P1.1 scout cadence, P1.2 harassment, P1.3 expansion timing, P1.5 doc history. Commit blocked by index.lock.
- **2026-05-02** — P0 scout import mismatch fixed. P1.4 deprecation shim. P2.1 FSM tests 23/23 pass.
- **2026-05-03** — **Test suite cleared:** 90 failures → 0. Fixed pytest-asyncio, torch stubs (qmix/mappo), stale __init__ exports (mappo/comm_learning), gas threshold test, crypto skipif guards. Final: 398 pass / 20 skip / 0 fail.
- **2026-07-09** — **Governance audit, not another CI-fix duplicate.** Discovered 334 open PRs (accumulated since 2026-04-20) from repeated nightly cycles, none merged; `main` still has the `tests/unit`-path CI bug live. Verified via `py_compile` + AST scan that `REMAINING_ISSUES.md` N1–N4 (duplicate method defs) and Issue #3 (transfusion priority) are already fixed/implemented in code — that doc was just stale, causing wasted re-investigation. Refreshed `PLAN-NIGHTLY.md`/`STATUS.md`/`REMAINING_ISSUES.md` to match reality and added the alert above. Recommended action: merge PR #372 (verified green, 1173 tests passing) and close the superseded duplicates. **Did not open a new PR for the CI fix itself** since #372 already covers it — opening a 335th duplicate would make the problem worse, not better.
