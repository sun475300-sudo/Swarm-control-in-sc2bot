# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-20

---

## 🔴 P0 finding (2026-07-20, still unresolved): PR backlog governance, not code

**517 open PRs, only ~9 ever merged, ever.** Growing 15-23 PRs/day since
2026-07-02 — far faster than the "daily" cadence this automation is
supposed to run at. PR #554 (2026-07-19) already did a full triage with a
ranked merge list (12 PRs, including `CLAUDE.md` guardrail PR #548) and a
~340-PR stale/duplicate close list. PR #548 already adds the exact
guardrail needed to stop the pile-up. **Neither is merged**, so neither
has taken effect — 25+ more duplicate PRs were opened after #554 posted
this exact warning, because `CLAUDE.md`/this doc's update only take effect
once merged into `main`, and no session merges its own PR (repo policy).
**The single highest-leverage action available is for the repo owner to
merge #548 and #554's recommended list.** No amount of further automated
diagnosis fixes this — it needs a human to click merge. Also: ~98
Dependabot alerts (2 critical, 37 high) on `main`, untouched by any open
PR — separate triage needed.

## 🗂️ Full ROADMAP.md audit (2026-07-20): all ~30 Sprint 1-8 tasks

Static-code audit (5 parallel readers, one per sprint group) checking each
task against its literal spec, not just "does a similarly-named function
exist." Full detail in session transcript; condensed here.

**DONE, matches spec, no action needed:** 1.1 (except referenced file
`build_order_executor.py` doesn't exist — renamed to `build_order_system.py`,
doc is stale), 1.2, 1.3, 1.4, 2.1, 2.3, 3.2, 3.4, 5.1, 5.2, 6.3, 8.1
(tooling only, no games run), 8.2 (tooling exists at
`tools/package_for_aiarena.py`, not the roadmap's named path).

**Fixed this session (commit `43298f3`):**
- 4.2 Mutalisk magic-box formation — was practically unreachable because
  the stacking hit-and-run path ran unconditionally before
  `should_use_magic_box()` was checked.
- 5.3 `queen_defense_mode` — set by strategy_manager's all-in response but
  never read by queen_manager. Wiring this in required also fixing a
  latent permanent-latch bug (flags were only cleared when the enemy
  expanded, never when an approaching army was repelled/retreated).

**PARTIAL / real gaps still open, prioritized by win-rate impact:**

| Task | Gap | Effort |
|---|---|---|
| 3.1 + 3.3 | `production_resilience.py` (the actual live larva-spend authority, called every step) never receives threat-level drone/army throttling — it owns its own disconnected `EconomyCombatBalancer` whose `apply_threat_level()` is never called. The roadmap's `spend_larva()` priority function is fully spec-compliant but is dead code — real larva spend is split across `economy_manager.py`, `production_controller.py`, and `production_resilience.py` (~2200 lines), uncoordinated. | medium-large |
| 4.1 | Two independent, live lurker burrow/unburrow systems (`combat/micro_combat.py:manage_lurker_positioning` and `combat/lurker_ambush.py:LurkerAmbushSystem`) issue commands to the same `LURKERMP` units every frame — likely command-thrashing. | small (pick one authority) |
| 4.4 | Two independent, live multi-prong-attack systems (`combat_manager._execute_multi_prong_attack`, triggered at 60+ supply; `bot_step_integration`'s `MultiProngCoordinator`, runs every step) can issue conflicting orders on overlapping units. A third module, `combat/multiprong_attack.py`, is fully dead. | small-medium |
| 4.3 | Roach-hydra "retreat" branch is a copy-paste no-op (both if/else arms do the same thing) and no caller ever passes `retreat=True` anyway — rear-guard-on-disengage is unimplemented in practice. | small-medium |
| 4.5 | The roadmap-spec'd `manage_combat`/`_should_skip_combat_frame` frame-skip function is never called; a different, more sophisticated unit-count-based dynamic skip runs instead (not a bug, just doc/reality mismatch — plus a third, fully dead `FrameSkipManager` module). | small (delete dead code, update doc) |
| 6.1 | RL micro path has per-call timeout fallback but no session-level "auto-disable if underperforming rule-based" — and `use_rl_micro` is never set `True` anywhere, so it's fully dormant by default (matches spec's "default off," just never actually exercised). | small |
| 6.2 | Stage-3 curriculum reward + transfer-learning logic is correct but `configure_stage3()` has no live caller — no training script drives macro→combat→combined progression. | medium |
| 7.1 | Building-placement did move out of `strategy_manager.py` into `building_manager.py` as intended, but counter/composition/timing-attack logic (~5,157 combined lines across `strategy_manager.py` + the actually-live `strategy_manager_v2.py`) still far exceeds "strategy-state decisions only." | large |
| 7.2 | `utils/distance_cache.py` is correctly implemented but barely adopted — `strategy_manager.py` doesn't use it at all (0 references, 8 raw `distance_to` calls); `combat_manager.py`/`economy_manager.py` use it at only ~3-4 call sites each vs dozens of raw calls. | medium (mechanical, repo-wide) |
| 7.3 | `utils/game_constants.py` is complete and well-designed but `strategy_manager.py`/`strategy_manager_v2.py` (largest files) never import it at all — 0 `GameFrequencies`/`EconomyConstants` usage despite raw magic-number iteration checks throughout. | medium (mechanical) |

**Cleanup-only findings (no win-rate impact, real maintenance/confusion risk):**
~5,200 lines of fully dead/unwired code across 12 `combat/` modules
(`air_unit_manager.py`, `baneling_bomb.py` — confusingly named near-dupe of
the *live* `baneling_tactics.py`, `multiprong_attack.py`,
`lurker_positioning.py`, `queen_walk.py`, `viper_tactics.py`, etc.); two
incompatible same-named `ThreatLevel` enums in `economy_manager.py` vs
`blackboard.py`; `local_training/self_play.py` orphaned duplicate of
`training_pipeline.py`/`self_play_league.py`; stale `RLAGENT_DISABLED.md`
contradicting current code (RL agent is in fact re-enabled under
`train_mode`); dead unreachable block in `economy_manager.py:2296-2334`;
bare `except Exception: continue/pass` with no logging in
`combat/base_defense.py` and `early_defense_system.py` hot paths (silently
swallows real bugs); `scouting_system.py`'s `deploy_changeling()` is a dead
duplicate missing the spec's energy≥50 gate (the live, correct
implementation is in `scouting/advanced_scout_system_v2.py`);
`enemy_expansion_spotted` blackboard key is set 3x, read 0x; no
Hydralisk-Den-existence gate on the air-threat response fallback.

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
