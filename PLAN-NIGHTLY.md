# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-02

---

## ⚠️ Governance blocker (read first)

As of 2026-07-02 there are **30 open PRs**, and at least **~18 of them
(#200–#217, #220–#230) are near-duplicate automated QA-cycle PRs that
independently rediscovered the same bug class** (asyncio
`get_event_loop()` deprecation in FSM tests, silently no-op async tests
on plain `unittest.TestCase`) because **none of them ever got merged
into `main`**. Every new automated session branches from the same
unfixed `main`, re-finds the same bug, and opens another draft PR that
also doesn't get merged. This is the single biggest thing blocking
forward progress — until one of these lands on `main`, this loop will
keep repeating regardless of how many more cycles run.

**Recommended action (needs owner decision, not done automatically):**
merge the most complete PR from the cluster (#221 or #224 — they
include a protobuf-collision + black/isort/CI-path fix that this
session's #231 does not) or #231 (this session, newest fix for the
no-op-async-test class + a test-collection-collision bug), then close
the rest of #200–#230 as superseded. See `MASTER_TODO_SC2.md` §1.1 for
the full PR inventory.

Also flagged: `git push` on 2026-07-02 reported **99 Dependabot
vulnerability alerts (2 critical, 38 high, 45 moderate, 14 low)** on
`main` — https://github.com/sun475300-sudo/Swarm-control-in-sc2bot/security/dependabot.
Not triaged this session (no tool access to alert detail from this
environment) — needs a manual look.

---

## Snapshot (current state, verified 2026-07-02)

- Branch: `main` @ `8a80b73` ("Update ci.yml"); working branch
  `claude/optimistic-edison-ai7vsk` (PR #231) on top of it.
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- **Test suite (freshly re-run, not copied from a prior doc claim):
  `pytest tests/ wicked_zerg_challenger/tests/` → 1164 passed / 14
  skipped / 0 failed** (1178 collected total, +1 new test added this
  session). Before this session's fixes: 20 failed (12 asyncio FSM +
  8 environment-only `cffi` issue), 2 collection errors.
- `flake8 --select=F811,F821,F823,F822 wicked_zerg_challenger/` → 0
  hits — `REMAINING_ISSUES.md` N1–N4 (duplicate method defs) confirmed
  still resolved on current main.
- **`ROADMAP.md` is significantly stale**: it lists Sprint 1 items
  (worker-harassment defense, lurker positioning, mutalisk micro,
  multi-pronged attacks, self-play league, distance caching, gas
  timing by matchup) as not-yet-implemented `구현 지시`, but all of
  them already exist in the codebase
  (`combat/lurker_positioning.py`, `combat/mutalisk_micro.py`,
  `combat/multiprong_attack.py`, `local_training/self_play_league.py`,
  `utils/distance_cache.py`, etc.). Roadmap needs a re-audit against
  actual code before it's trustworthy as a "what's left" source —
  don't blindly re-implement items it lists as open without checking
  the code first.
- Queen transfusion logic: 3 bugs fixed (`is_idle` guard removed, target dedup, per-queen cooldown) ✅ (prior session, still verified present)

## Resolved this run (2026-07-02)

| Item | File(s) | Notes |
|------|---------|-------|
| Test-collection collision | `scripts/__init__.py` (new) | Root `scripts/` had no `__init__.py` → resolved as a namespace package that collided with the unrelated `wicked_zerg_challenger/scripts/` dir once dozens of sibling test files pushed `wicked_zerg_challenger/` onto `sys.path[0]`. Broke `test_ladder_tracker.py`/`test_meta_adapter.py` collection only when the full suite ran together. Fixed by making `scripts/` an explicit package. |
| FSM `asyncio.get_event_loop()` deprecation | `tests/test_combat_phase_fsm.py` | 5 call sites replaced with `asyncio.run(...)`. Order-dependent `RuntimeError: no current event loop` affecting 12 tests. Same bug independently found by PR #220–#230. |
| Silently no-op async tests | `wicked_zerg_challenger/tests/test_production_resilience.py`, `test_opponent_modeling.py` | Both classes were plain `unittest.TestCase` with `async def test_*` methods — bodies never ran (18 tests). Switched to `IsolatedAsyncioTestCase`. |
| Stale test signature | `test_production_resilience.py` | 3 tests called removed `_get_counter_unit(race_str)` API; real signature is `_get_counter_unit(enemy_units, has_roach_warren, has_hydra_den, has_spire)`. Rewrote + added a `no-enemies` case. |
| CI: `python-lint-test` job failing on protobuf | `.github/workflows/ci.yml` | The job's `pytest tests/` step imports `sc2` but (unlike the `sc2-bot-test` job right below it) never set `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python`, so a newer `protobuf` pulled in transitively by `requirements.txt` (google-generativeai/mcp) broke `s2clientprotocol`'s generated `_pb2.py` files (`TypeError: Descriptors cannot be created directly`), 14 collection errors. Added the same env var the other job and `wicked_zerg_challenger/tests/conftest.py` already use for this. Discovered live via the PR #231 CI webhook, not locally reproducible in this sandbox (different resolved protobuf version), so verified by precedent rather than a local repro. |

**Net result: 20 failed / 2 collection errors → 0 failed. Suite: 1164 pass / 14 skip (was untested in this sandbox before — see governance blocker above for why the same fixes kept getting rediscovered without landing).**

Pushed to `claude/optimistic-edison-ai7vsk`, opened as PR #231 (draft).

## Resolved 2026-05-03 (history)

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

| #    | Item                                                     | Status | Notes |
|------|----------------------------------------------------------|--------|-------|
| P0.1 | Merge one PR from the 220–230 / 200–217 duplicate cluster | ❌ Open — needs owner | See governance blocker above. Nothing else in this backlog matters until this loop breaks. |
| P0.2 | Triage 99 Dependabot alerts (2 critical, 38 high)         | ❌ Open — needs owner | Not accessible from this session's tools; check the Security tab. |

## P1 — Important

| #    | Item                                                     | Status | Notes |
|------|----------------------------------------------------------|--------|-------|
| P1.8 | Re-audit `ROADMAP.md` against actual code                | ❌ Open | Sprint 1 items already implemented but roadmap lists them as TODO — wastes future session effort re-implementing done work. |
| P1.9 | Consider removing `--disable-warnings` from `pytest.ini` (or add a targeted lint rule) | ❌ Open | This flag suppressed the `RuntimeWarning: coroutine ... was never awaited` that would have caught the no-op-async-test bug (fixed 2026-07-02) much earlier. Removing repo-wide may surface a lot of noise — consider a narrower CI check instead (e.g. grep for `async def test_` under a class inheriting bare `unittest.TestCase`). |
| P1.10 | `REMAINING_ISSUES.md` Issue #3 (Transfusion priority) + #4 (resource-reservation race condition) | ❌ Open | Still unaddressed as of 2026-07-02; concrete patches already drafted in that doc. |
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
- **2026-07-02** — Fresh ground-truth run in a clean sandbox: fixed scripts/ namespace-package test-collection collision, FSM `asyncio.get_event_loop()` deprecation (12 tests), 2 silently no-op async `unittest.TestCase` classes (18 tests) + 3 stale-signature tests. 1164 pass / 14 skip / 0 fail. Pushed as PR #231. **Identified and documented the real blocker: ~18 near-duplicate unmerged PRs (#200–#230) from prior sessions rediscovering the same bugs because nothing lands on `main` — flagged as P0.1, needs owner action.** Also flagged 99 unreviewed Dependabot alerts (P0.2) and roadmap/code drift (P1.8).
