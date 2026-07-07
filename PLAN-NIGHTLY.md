# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-07

---

## Snapshot (current state)

- Branch: `claude/optimistic-edison-fyzxv0` (PR pending), base `main` last commit 8a80b73 (2026-06-25).
- Bot core: `wicked_zerg_challenger/` — 417 Python files across 10+ subdirs (the ~300 other top-level dirs — rust/haskell/kotlin/terraform/kafka clones — are unrelated scaffolding, not live bot code).
- Root `tests/` (516 collected) and `wicked_zerg_challenger/tests/` (661) are two separate suites; CI previously only ran the latter for real (see Resolved 2026-07-07).
- **Test suite: `tests/` 502 pass / 14 skip / 0 fail** ✅ (was silently only collected, never executed, in CI — see below). `wicked_zerg_challenger/tests/` 661/661 pass (unchanged, confirmed by audit).

## Resolved this run (2026-07-07)

| Item | File(s) | Notes |
|------|---------|-------|
| N7: CI never actually ran `tests/` | `.github/workflows/ci.yml` | "pytest 실행 (전체)" step ran `pytest tests/ --co` (collect-only) — removed the flag. Also added `requirements-dev.txt` install so `pytest-asyncio`/`pytest-timeout`/`pytest-mock` are present in CI. |
| N8: order-dependent FSM test failures | `tests/test_combat_phase_fsm.py` | 5 helpers used `asyncio.get_event_loop().run_until_complete(...)`, which crashes with `RuntimeError: no current event loop` when run after other async tests in the same session (12 failures). Replaced with `asyncio.run(...)`. |
| N9: `sc2bot-ci.yml` referenced nonexistent `tests/unit` | `.github/workflows/sc2bot-ci.yml` | Repo has flat `tests/test_*.py` + `tests/integration/`, no `tests/unit/`. Fixed to `pytest tests/ --ignore=tests/integration`; also installs `requirements-dev.txt`. |
| N10: `test_expansion_timing.py` (P1.3, 22 tests) always skipped | `tests/test_expansion_timing.py` | Used `from wicked_zerg_challenger.economy_manager import ...` (package-qualified), which fails because `economy_manager.py`'s internal `from config.unit_configs import ...` only resolves when `wicked_zerg_challenger/` itself is on `sys.path` (the convention every other test file uses). These 22 regression tests for the "6min→1min expansion" bug had *never actually run*. Fixed to match convention — now genuinely passing. |
| N11: 2 more silently-always-skipped test files | `tests/test_advanced_scout_system_v2.py` (19 tests), `tests/test_harassment_coordinator.py` (22 tests) | Root cause: a *different* bug — these did their `wicked_zerg_challenger` import inside `setup_method` (per-test, late), and the repo has an unrelated top-level `./utils/` package that collides with `wicked_zerg_challenger/utils/`; late imports lost the race and resolved the wrong `utils`, hiding `ModuleNotFoundError: No module named 'utils.logger'` behind a bare `except ImportError: pytest.skip(...)`. Passed in the full suite by luck of file-ordering, but skipped 100% of the time in isolation — a real, provable coverage gap. Fixed by moving the import to module level (matches the pattern used by every reliably-passing test file in this suite). |

**Net result: no regressions, but ~65 tests (22+19+22+12-order-flakiness) that were either never running or order-dependently flaky are now genuinely exercised on every run.** See `REMAINING_ISSUES.md` N7-N12 for full detail (N12 — `test_phase10_improvements.py`, 11 tests, same root cause as N11 — deferred as a follow-up, file has more entangled classes).

## Historical (2026-05-04 and earlier)

- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` runs black + isort + flake8 ✅ (all clean as of 2026-05-04; not re-verified this run — black/isort not installed in this sandbox, flagged as P2 below)
- **Test suite: 468 pass / 15 skip / 0 fail** (2026-05-04 baseline, superseded by the numbers above)
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

*No P0 items this run.* (N7-N9 CI blockers fixed this run — see Resolved above — demoted from what would have been P0.)

## P1 — Important

| #    | Item                                                     | Status | Notes |
|------|----------------------------------------------------------|--------|-------|
| P1.1 | Scouting cadence improvements                            | ✅ Done | `phase_scout_cadence.py` + tests, confirmed passing 2026-07-07. |
| P1.2 | Harassment retraction + worker-kill tracking hardening   | ✅ Done | `harassment_coordinator.py`; tests were silently skipped until N11 fix (2026-07-07), now confirmed 22/22 passing. |
| P1.3 | First-expansion timing test harness                      | ✅ Done (tests now actually run) | `tests/test_expansion_timing.py` — was 100% silently skipped since creation (N10), fixed 2026-07-07, 22/22 passing. Underlying claim (bot expands at ~1min not ~6min) is only unit-tested against the decision function with mocks — still needs a real/replay-based check, see P2.2. |
| P1.4 | Reduce duplicate scout system files                      | ✅ Done | Canonical: `AdvancedScoutingSystemV2`; tests were silently skipped until N11 fix, now confirmed 19/19 passing. |
| P1.5 | Trim top-level doc surface area                          | ❌ Not done | Still 47+ overlapping docs at repo root (`docs/history/` never populated — re-opening this from the old "✅ Done"). |
| P1.6 | Add `pytest-asyncio` to `requirements-dev.txt`           | ✅ Done | Present; also now actually installed in both CI workflows (was missing from `ci.yml`'s install step until 2026-07-07). |
| P1.7 | Queen transfusion logic bugs                              | ✅ Done | 14 tests passing, confirmed 2026-07-07. |
| P1.8 | `test_phase10_improvements.py` StrategyManager tests silently skip in isolation (N12) | ❌ Open | Same root cause as N11 (`utils` package name collision + deferred import). 11 tests. File has more entangled test classes — needs a careful pass, not a quick copy-paste fix. |
| P1.9 | Verify "encoding error" claims (ROADMAP.md Sprint 1 Task 1.1) | ❌ Open | ROADMAP.md still lists this unresolved; TODO.md (Jan 2026) claims it was fixed. Contradiction not yet re-verified this run — check `early_defense_system.py`/`build_order_executor.py` for non-ASCII chars for real. |
| P1.10 | Combat kite/retreat stub always-attacks (`combat/micro_combat.py:1329`) | ❌ Open | Explicit "for now, just attack" stub; directly affects unit trades/win rate. |

## P2 — Nice-to-have

| #    | Item                                            | Status | Notes |
|------|-------------------------------------------------|--------|-------|
| P2.1 | Force-accumulation FSM tests                    | ✅ Done | `tests/test_combat_phase_fsm.py` — 23 tests; fixed an order-dependent failure (N8) 2026-07-07, now robust regardless of run order. |
| P2.2 | Benchmark runner                                | ❌ Open | Single command, N replays, APM/supply/win-rate report vs Hard. Would also give a real (non-mocked) answer to the expansion-timing question in P1.3. |
| P2.3 | Build-order config externalisation              | ❌ Open | Move top-20 hardcoded values to `config/build_orders.yaml`. |
| P2.4 | RL agent save-experience guard                  | ❌ Open | Unit test for save under disk-full / interrupted-rename. |
| P2.5 | Type hints + docstring pass on core modules     | ❌ Open | `core/resource_manager.py`, `core/manager_factory.py`. |
| P2.6 | `situational_awareness.py:148-190` threat/opportunity levels | ❌ Open | Only 2 of 5 enum levels ever returned; likely causes over/under-reaction in combat decisions. |
| P2.7 | `tech_coordinator.py:137-140` tech-prerequisite validation | ❌ Open | No real validation; relies on callers being correct — latent invalid-build-order bug source. |
| P2.8 | black/isort/flake8 lint gate actually green      | ❌ Open | MASTER_TODO_SC2.md (stale) claimed 48+ unformatted files under pinned `black==26.3.1`; not re-verified this run (black/isort not installed in this sandbox) — verify and run formatting once so the gate is genuinely green, not just non-blocking. |
| P2.9 | Triage 14 redundant "Claude improvement cycle" branches | ❌ Open | Avoid re-fixing what another branch already fixed; close/merge before starting unrelated new work. |

## Long-term direction

- **AI Arena submission cadence.** 2-week cadence: benchmark suite (P2.2), submit only if metrics improve.
- **Self-play loop.** `NEXT_LARGE_PLAN.md` P823 — highest-leverage long-term improvement.
- **Macro / micro directory split.** Keep `wicked_zerg_challenger/macro/` vs `wicked_zerg_challenger/micro/`.

---

---

## Run history

- **2026-04-25** — Initial nightly plan.
- **2026-04-26** — P0.2 (empty-logger CI guard) landed.
- **2026-04-27** — black + isort + flake8 all clean.
- **2026-04-28** — Harassment retraction logic hardened (P1.2).
- **2026-05-01** — P1.1 scout cadence, P1.2 harassment, P1.3 expansion timing, P1.5 doc history. Commit blocked by index.lock.
- **2026-05-02** — P0 scout import mismatch fixed. P1.4 deprecation shim. P2.1 FSM tests 23/23 pass.
- **2026-05-03** — **Test suite cleared:** 90 failures → 0. Fixed pytest-asyncio, torch stubs (qmix/mappo), stale __init__ exports (mappo/comm_learning), gas threshold test, crypto skipif guards. Final: 398 pass / 20 skip / 0 fail.
- **2026-05-04 → 2026-06-25** — Gap in this doc; see `git log` (PR #218 "stabilize SC2 bot test suite", 6 rounds: fixed 7 failing tests + 1 collection error, 6 F821 NameErrors, removed shadowed duplicate methods, implemented previously-undefined called methods) — `wicked_zerg_challenger/tests/` reached 661/661.
- **2026-07-07** — Full re-audit (see `REMAINING_ISSUES.md` N7-N12). Confirmed N1-N4 (old F811 dupes) already resolved by the June work. Found and fixed 3 CI/test-infra bugs that were hiding real coverage gaps: CI collect-only flag (N7), an order-dependent async test bug (N8), a nonexistent CI test path (N9), and 2 test files that were *always* silently skipped due to import bugs (N10 expansion timing, N11 scout/harassment — 63 tests total newly/reliably executing). `tests/` now 502 pass / 14 skip / 0 fail, robust to run order. Refreshed P1/P2 backlog with concrete file:line targets from the audit for the next round.
