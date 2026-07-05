# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-05

---

## Snapshot (current state)

- Branch: `claude/optimistic-edison-fbfjiw` (based on `main` after PR #218 + `ci.yml` update).
- Bot core: `wicked_zerg_challenger/` — 1,233 Python files. **This is the only test suite that gates real bot quality** — run with `pytest wicked_zerg_challenger/tests/ -v`. Root-level `tests/` is a separate, mostly-unrelated suite (stale duplicate SC2-bot tests + a bundled JARVIS/crypto-trading project) — keep it green too since CI still touches it, but it is not where SC2 bot feature work should be verified.
- **`wicked_zerg_challenger/tests/`: 648 pass / 13 skip / 0 fail** ✅ (matches PR #218's reported 661/661).
- **root `tests/`: 486 pass / 12 skip / 0 fail** ✅ (was 12 failing in `test_combat_phase_fsm.py` before this run — see below).
- ROADMAP.md Sprint 1 (encoding, worker-harassment defense, harass-unit reach/return, 1-min expansion timing) — **verified done** in current code, despite some historical docs (`REMAINING_ISSUES.md`, `TODO.md`) still describing them as open. Those docs are stale as of PR #218 and have not been corrected yet.
- ROADMAP.md Sprint 2.3 (build-pattern recognition 12→25) — code-complete (13 new patterns detected + Blackboard-wired) but was **test-incomplete**: only 2/13 new patterns had unit tests. Fixed this run (see below).
- ROADMAP.md Sprint 7.2 (DistanceCache) — class exists, tested in isolation, but barely wired into hot paths (`combat_manager.py` routes only 3 of ~63 distance calls through it, `economy_manager.py` only 2 of ~26). Effectively dead code in practice — **next priority**.
- ROADMAP.md Sprint 7.3 (GameConstants/GameFrequencies replacing magic numbers) — **not done**: 193 raw iteration-modulo magic numbers remain across 67 files, including in files that already import `GameFrequencies`.
- New, previously undocumented defect found this run: genuine mojibake (broken CJK decoding) in ~15 files (`local_training/reward_system.py`, `local_training/aggressive_tech_builder.py`, `unit_factory.py`, several `tools/*.py`, `*_workflow.py`) — Korean docstrings rendered as garbled glyphs/`????`. Not yet fixed.

## Resolved this run (2026-07-05)

| Item | File(s) | Notes |
|------|---------|-------|
| 12 failing tests: `asyncio.get_event_loop()` deprecated under Python 3.11 (`RuntimeError: There is no current event loop in thread 'MainThread'`) | `tests/test_combat_phase_fsm.py` | Replaced with `asyncio.new_event_loop()` at all 5 call sites. 23/23 tests in file now pass; root `tests/` suite back to 0 failures. |
| Sprint 2.3 test gap: 11 of 13 new build-pattern detectors (`2_1_1_medivac_drop`, `widow_mine_drop`, `mech_transition`, `cannon_rush`, `dt_rush`, `void_ray_rush`, `immortal_allin`, `archon_transition`, `ling_rush`, `muta_rush`, `nydus_rush`) had no unit test | `wicked_zerg_challenger/tests/test_sprint2_scouting_intel.py` | Added one test per pattern, asserting detected pattern name + recommended response + relevant Blackboard flags (`enemy_aggression`, `AIR_THREAT_INCOMING`, `cloak_tech_detected`, etc.). All 13/13 `BUILD_PATTERNS` entries now covered. |

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

## P1 — Important (next priorities, verified against current code 2026-07-05)

| #    | Item                                                     | Status | Notes |
|------|----------------------------------------------------------|--------|-------|
| P1.1 | Wire `DistanceCache` into actual hot paths                | ❌ Open | `utils/distance_cache.py` works and is unit-tested, but `combat_manager.py` routes only 3/~63 `distance_to` call sites through it (`economy_manager.py`: 2/~26). Replace remaining raw `.distance_to()` calls in per-frame hot loops (`respond_to_worker_harassment`, `manage_harass_units`, `_safe_distance`) with `self.distance_cache.get(...)`. Roadmap Sprint 7.2. |
| P1.2 | Replace magic-number iteration moduli with `GameFrequencies` | ❌ Open | 193 raw `% 11/22/33/44/66/110/220/330/660` checks remain across 67 files, including inside `combat_manager.py` (17 sites) and `economy_manager.py` (5 sites) which already import `GameFrequencies`. Roadmap Sprint 7.3. Do incrementally file-by-file to keep diffs reviewable — do not bulk-sweep. |
| P1.3 | Fix genuine mojibake (broken CJK encoding)                | ❌ Open | ~15 files have corrupted Korean docstrings/comments (`local_training/reward_system.py`, `local_training/aggressive_tech_builder.py`, `unit_factory.py`, several `tools/*.py`, `*_workflow.py`). Distinct from the already-fixed emoji/symbol cleanup (Sprint 1.1). Needs care: check git blame/history for a pre-corruption revision before rewriting by hand. |
| P1.4 | Verify Sprint 4/5/8 roadmap status                        | ❌ Open | Combat micro (lurker positioning, mutalisk hit-and-run, roach-hydra formation, multi-pronged attacks), defense systems (proxy defense, drop defense, all-in detection), and QA/Arena packaging have not yet been checked against current code — unknown if done/partial/missing. |

## P2 — Nice-to-have

| #    | Item                                            | Status | Notes |
|------|-------------------------------------------------|--------|-------|
| P2.1 | Benchmark runner                                | ❌ Open | Single command, N replays, APM/supply/win-rate report vs Hard. Roadmap Sprint 8.1 (`run_mass_test.py`). |
| P2.2 | Build-order config externalisation              | ❌ Open | Move top-20 hardcoded values to `config/build_orders.yaml`. |
| P2.3 | RL agent save-experience guard                  | ❌ Open | Unit test for save under disk-full / interrupted-rename. |
| P2.4 | Type hints + docstring pass on core modules     | ❌ Open | `core/resource_manager.py`, `core/manager_factory.py`. |
| P2.5 | Unify `BUILD_PATTERNS` dict with legacy elif-chain patterns | ❌ Open | `intel_manager.py` has 13 dict-driven patterns (Sprint 2.3, now fully tested) plus ~12 separate hardcoded elif patterns (bio/mech/rush/stargate/robo/etc.) that predate it — not unified into one 25-entry table as the roadmap literally describes. Low priority: both paths work today. |

## Long-term direction

- **AI Arena submission cadence.** 2-week cadence: benchmark suite (P2.1), submit only if metrics improve.
- **Self-play loop.** `NEXT_LARGE_PLAN.md` P823 — highest-leverage long-term improvement.
- **Macro / micro directory split.** Keep `wicked_zerg_challenger/macro/` vs `wicked_zerg_challenger/micro/`.
- **MASTER_TODO_SC2.md S0/S1** — 16 open "Claude improvement cycle" draft PRs (#15–#30) still need human redundancy triage before any close/merge; automation must not auto-close or force-merge these.

---

## Run history

- **2026-04-25** — Initial nightly plan.
- **2026-04-26** — P0.2 (empty-logger CI guard) landed.
- **2026-04-27** — black + isort + flake8 all clean.
- **2026-04-28** — Harassment retraction logic hardened (P1.2).
- **2026-05-01** — P1.1 scout cadence, P1.2 harassment, P1.3 expansion timing, P1.5 doc history. Commit blocked by index.lock.
- **2026-05-02** — P0 scout import mismatch fixed. P1.4 deprecation shim. P2.1 FSM tests 23/23 pass.
- **2026-05-03** — **Test suite cleared:** 90 failures → 0. Fixed pytest-asyncio, torch stubs (qmix/mappo), stale __init__ exports (mappo/comm_learning), gas threshold test, crypto skipif guards. Final: 398 pass / 20 skip / 0 fail.
- **2026-06-02** — PR #218 merged: `wicked_zerg_challenger/tests/` suite stabilized to 661/661 (648 pass / 13 skip), 6 `F821` NameError bugs fixed, 5 shadowed-duplicate-method (`F811`) bugs fixed, several called-but-never-defined methods implemented.
- **2026-06-25** — `ci.yml` blocking-mode restored (removed `|| true` suppressors on pytest steps).
- **2026-07-05** — Verified ROADMAP.md Sprint 1/2.1/3/7.2 implementation status against current code (see Snapshot above); fixed 12 failing tests in `tests/test_combat_phase_fsm.py` (Python 3.11 `asyncio.get_event_loop()` deprecation); added 11 missing Sprint-2.3 build-pattern unit tests (13/13 patterns now covered). Both suites green: `wicked_zerg_challenger/tests/` 648/13/0, root `tests/` 486/12/0. Next: wire `DistanceCache` into hot paths, replace magic-number moduli with `GameFrequencies`, fix mojibake in ~15 files, check Sprint 4/5/8 status.
