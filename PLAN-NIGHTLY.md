# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-12

---

## ⚠️ Read this first (2026-07-12)

This doc was stale for ~2 months (last refreshed 2026-05-04) while the
nightly/automated cycle kept running. In that gap it accumulated **~30 open
draft PRs (`#397`–`#427`)**, almost all independently re-fixing the exact
same two bugs (asyncio event-loop test crash, black/isort CI gate) without
ever merging one. `sc2bot-ci.yml` has been **red on `main` since 2026-05-28**
as a direct result — every run fails at the blocking `black --check` step
and every downstream job (tests, docker, deploy) shows `skipped`.

**PR #427 fixes both root causes and is verified green through the lint
matrix; Test Suite job was still running as of this writing.** Action for
the maintainer: merge #427 (or whichever duplicate you prefer), then close
the rest of `#397`–`#426` as superseded. Until one fix actually lands on
`main`, every future automated cycle will keep rediscovering the same
"CI is red" state and re-spend effort on it instead of moving forward.

## Snapshot (current state, verified 2026-07-12 in a fresh sandbox)

- Branch: `main` was still on the pre-fix commit (`8a80b73`) as of this
  writing; fix lives on `claude/optimistic-edison-nac9jn` (PR #427).
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` lint (black/isort/flake8-critical) — **red since
  2026-05-28**, fixed on PR #427 (66 files black-reformatted, 5 files
  isort-fixed at repo root, matching CI's exact `black --check --diff .` /
  `isort --check-only --diff .` invocation).
- **Test suite (fresh env, after fix): `tests/` 502 pass / 14 skip / 0 fail;
  `wicked_zerg_challenger/tests/` 661 pass / 0 fail.**
- flake8 F811 (silently-shadowed duplicate methods, the N1-N4 items from
  `REMAINING_ISSUES.md`) — **0 findings**, confirms PR #218's cleanup holds.
- flake8 F821/F823 (undefined-name runtime crashers) — **0 findings**.
- bandit (`wicked_zerg_challenger/`, `-ll`) — 6 findings: 3× medium
  "unsafe torch.load" (imitation_learner.py:496, ppo_agent.py:702,
  batch_trainer.py:68 — checkpoints are plain dict/tensor/int/float, safe
  candidates for `weights_only=True`, but **not applied yet** — no torch
  install in the sandbox to verify against, don't want to ship an untested
  change to model-checkpoint loading); 1× high "shell injection" in
  `tools/monitor_background_training.py:42` — false positive, the
  `os.system()` arg is a hardcoded `'cls'/'clear'` literal, not user input.
- GitHub Dependabot: **99 open alerts** (2 critical, 37 high, 46 moderate,
  14 low) on `main` — not triaged this round, flagging for visibility.
- Queen transfusion logic: 3 bugs fixed (`is_idle` guard removed, target dedup, per-queen cooldown) ✅ (carried over from prior session)

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

| #    | Item                                                      | Status | Notes |
|------|-----------------------------------------------------------|--------|-------|
| P0.1 | `sc2bot-ci.yml` red on `main` since 2026-05-28             | 🟡 Fix ready, unmerged | PR #427. Root cause: 66 files not black-formatted + 5 files isort-broken at repo root; blocking `black --check --diff .` step fails and cascades to skip every downstream job. |
| P0.2 | ~30 open duplicate PRs (`#397`-`#427`), none merged        | ❌ Open — needs maintainer decision | Each prior automated cycle re-fixed the same asyncio/black bug on a fresh branch instead of building on a merged baseline. Recommend: merge one, close the rest as superseded. |

## P1 — Important

| #    | Item                                                     | Status | Notes |
|------|----------------------------------------------------------|--------|-------|
| P1.1 | Scouting cadence improvements                            | ✅ Done | `phase_scout_cadence.py` + tests written. |
| P1.2 | Harassment retraction + worker-kill tracking hardening   | ✅ Done | `harassment_coordinator.py` updated. |
| P1.3 | First-expansion timing test harness                      | ✅ Done | `tests/test_expansion_timing.py` 20 tests. |
| P1.4 | Reduce duplicate scout system files                      | ✅ Done | Canonical: `AdvancedScoutingSystemV2`. Deprecation shim + import fix done. |
| P1.5 | Trim top-level doc surface area                          | ✅ Done | 15 historical docs moved to `docs/history/`. |
| P1.6 | Add `pytest-asyncio` to `requirements-dev.txt`           | ✅ Done | `requirements-dev.txt` created with pytest-asyncio>=0.23.0 and all dev deps. |
| P1.7 | Queen transfusion logic bugs                              | ✅ Done | Fixed `is_idle` blocking combat-phase transfusions, added target dedup, added per-queen cooldown (1.5s). 14 new tests in `tests/test_queen_transfusion.py`. |
| P1.8 | `test_combat_phase_fsm.py` order-dependent event-loop crash | ✅ Done (PR #427) | `asyncio.get_event_loop().run_until_complete()` → `asyncio.run()`. Failed only when run after other async tests closed the loop (11/23 tests, full-suite-only repro). |
| P1.9 | Triage 99 open Dependabot alerts (2 critical, 37 high)   | ❌ Open | Not triaged this round — needs its own pass, likely several separate PRs by package. |

## P2 — Nice-to-have

| #    | Item                                            | Status | Notes |
|------|-------------------------------------------------|--------|-------|
| P2.1 | Force-accumulation FSM tests                    | ✅ Done | `tests/test_combat_phase_fsm.py` — 23 tests all passing. |
| P2.2 | Benchmark runner                                | ❌ Open | Single command, N replays, APM/supply/win-rate report vs Hard. |
| P2.3 | Build-order config externalisation              | ❌ Open | Move top-20 hardcoded values to `config/build_orders.yaml`. |
| P2.4 | RL agent save-experience guard                  | ❌ Open | Unit test for save under disk-full / interrupted-rename. |
| P2.5 | Type hints + docstring pass on core modules     | ❌ Open | `core/resource_manager.py`, `core/manager_factory.py`. |
| P2.6 | Harden `torch.load()` calls with `weights_only=True` | ❌ Open | 3 call sites (`imitation_learner.py:496`, `ppo_agent.py:702`, `batch_trainer.py:68`). bandit B614 medium. Checkpoints are plain dict/tensor/int/float so should be safe, but needs a torch-enabled environment to verify before shipping. |
| P2.7 | ~80+ F841 unused-local-variable flake8 findings | ❌ Open | Cosmetic, non-blocking (flake8 full run is `continue-on-error` in CI). Low priority cleanup candidate. |

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
- **2026-07-12** — Doc was stale for ~2 months; found `sc2bot-ci.yml` red on `main` since 2026-05-28 and ~30 unmerged duplicate PRs all re-fixing the same two bugs. Fixed both root causes on PR #427 (black/isort repo-wide reformat + `asyncio.run()` fix for order-dependent FSM test crash). Verified clean: `tests/` 502 pass/14 skip/0 fail, `wicked_zerg_challenger/tests/` 661 pass/0 fail, 0 F811/F821 findings. Flagged 99 open Dependabot alerts and 3 `torch.load` hardening candidates for a future round. **Action needed from maintainer: merge #427, close #397-#426 as superseded.**
