# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-14

---

## ⚠️ Top blocker: PR pileup, needs a human (2026-07-14)

**30+ open draft PRs (#436-466)** on this repo, almost all independently
re-discovering and re-fixing the *same* two bugs:
1. `black`/`isort` formatting drift on `main` since commit `8a80b73`.
2. `asyncio.get_event_loop().run_until_complete(...)` in
   `tests/test_combat_phase_fsm.py` — order-dependent: passes in isolation,
   fails with `RuntimeError: There is no current event loop in thread
   'MainThread'` when the full suite runs and an earlier async test closes
   the default loop first. Fix: use `asyncio.run(...)` per call instead.

Repo policy (see `MASTER_TODO_SC2.md` §3) forbids agents from merging or
closing PRs — every PR needs human review. Because nothing has merged since
PR #218, every new nightly session starts from the same broken `main` and
repeats the cycle. **Recommended action: review and merge one canonical fix
PR (e.g. #465 or #466), then close the redundant #436-465 range.** Until a
human does this, expect the pileup to keep growing by ~1 PR/hour.

(Also surfaced by GitHub on push, not investigated: 99 Dependabot alerts on
`main`, 2 critical / 37 high.)

## Snapshot (current state)

- Branch: `main` @ `8a80b73` (Update ci.yml) — has had a red `black`/`isort`
  lint gate since this commit, which cancels the downstream test job.
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` lint job (black/isort) is currently **red on main** ❌
  — 66 files need `black`, ~19 files need `isort`. Not re-fixed here to
  avoid a 32nd copy of the same diff already sitting in PR #465/#466;
  merge one of those instead.
- **Test suite (this session, sandboxed — no live SC2 client available):**
  `tests/` 502 passed / 14 skipped / 0 failed. `wicked_zerg_challenger/tests/`
  661 passed / 0 failed. (Matches the ~1163-passed figure PR #466 reported.)
- Sprint 7 infra (`building_manager.py`, `utils/game_constants.py`,
  `utils/distance_cache.py`) exists but **adoption is shallow**: `DistanceCache`
  used in only 7 files while raw `.distance_to(` calls remain in 130 files
  (701 call sites). Real follow-up work, not yet claimed by any open PR.
- Sprint 8.1 (30-game Medium AI QA run) has never been executed or recorded
  — no StarCraft II client is installed in this sandbox, so it cannot be run
  here; needs a session with the actual game binary.

## Resolved this run (2026-07-14)

| Item | File(s) | Notes |
|------|---------|-------|
| Order-dependent event-loop crash | `tests/test_combat_phase_fsm.py` | Replaced 5x `asyncio.get_event_loop().run_until_complete(...)` with `asyncio.run(...)`. Verified: fails when run after other async tests in the full suite, passes reliably after the fix. Same root cause as PR #465/#466 — independently confirmed real. |
| `cffi` missing (sandbox only) | n/a | `cryptography.fernet` needs `_cffi_backend`; installed locally, not a repo change. |
| `burnysc2` install blocked by `mpyq` build failure (sandbox only) | n/a | `mpyq`'s legacy `setup.py` trips a Debian distutils bug; installed `burnysc2 --no-deps` instead (mpyq is replay-parsing only, unused by the test suite). |



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
- **2026-07-14** — Doc had gone stale for 2+ months while the repo kept moving elsewhere (main now at `8a80b73`, black/isort red, 30+ duplicate draft PRs open re-fixing the same 2 bugs). Independently re-verified the `asyncio.run()` fix for `tests/test_combat_phase_fsm.py` and confirmed the full suite (1163 tests across `tests/` + `wicked_zerg_challenger/tests/`) is green once that's applied. Did **not** redo the repo-wide black/isort reformat already sitting in PR #465/#466 — flagged the pileup as the real blocker instead of adding a 31st copy of the same diff.
