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

### 2026-07-11 — Resolved this run (CI green-up, continued)

| Item | File(s) | Notes |
|------|---------|-------|
| `sc2bot-ci.yml` Test Suite job pointed at a directory that never existed | `.github/workflows/sc2bot-ci.yml` | `pytest tests/unit` — `tests/unit` has never existed anywhere in this repo's git history. This job `needs: lint`, and the lint job's `black --check` was failing on `main` independent of any PR, so this job had apparently never run to completion before — fixing lint exposed it. Repointed at `pytest wicked_zerg_challenger --cov=wicked_zerg_challenger` (672 tests, matches the bot's real suite). Also added `pytest-timeout` to the install step - the integration-test step passes `--timeout=120` but nothing installed the plugin that flag requires. |
| `burnysc2`'s `sc2/main.py` imports `async_timeout`, which its own package metadata never declares | `requirements.txt`, `wicked_zerg_challenger/requirements.txt` | Any code path that does `from sc2 import maps` (or otherwise loads `sc2/main.py`) throws `ModuleNotFoundError: No module named 'async_timeout'` on a fresh install of just `requirements.txt` (`pip show burnysc2` confirms its declared `Requires:` list omits it). This broke collection of `wicked_zerg_challenger/test_10games.py`, `test_3games.py`, and `test_multitask_destruction.py` in CI once the Test Suite job actually started running. Added `async_timeout>=4.0.0` as an explicit direct dependency in both requirements files (burnysc2 itself is third-party and can't be patched here). |

### 2026-07-11 — Resolved this run

| Item | File(s) | Notes |
|------|---------|-------|
| Viper spells silently no-op | `combat/viper_tactics.py`, `combat/smart_consume.py`, `spellcaster_automation.py`, `spell_unit_manager.py` | 8 wrong `AbilityId` string names across 4 files (`EFFECT_VIPERABDUCT`→`EFFECT_ABDUCT`, `EFFECT_BLINDINGCLOUD`→`BLINDINGCLOUD_BLINDINGCLOUD`, `EFFECT_PARASITICBOMB`→`PARASITICBOMB_PARASITICBOMB`, `VIPERCONSUMESTRUCTURE_YOURBUILDINGS`→`VIPERCONSUMESTRUCTURE_VIPERCONSUME`, `CONSUME_VIPER`→`VIPERCONSUME_VIPERCONSUME`, `EFFECT_VIPERCONSUME`→ split into `VIPERCONSUMESTRUCTURE_VIPERCONSUME`/`VIPERCONSUME_VIPERCONSUME` by target type, `ABDUCT_ABDUCT`→`EFFECT_ABDUCT`). None of these enum members exist in `python-sc2`'s `AbilityId`, so every `if AbilityId.X in abilities` guard was always `False` and the cast never fired — every `try/except` around the call site swallowed nothing because the code never even reached the `.do()` call. **Effect: Vipers on the battlefield have never cast Abduct, Blinding Cloud, Parasitic Bomb, or refilled energy via Consume through either of the two independent code paths that implement it.** Found by an advisor sub-agent bug hunt, independently verified against the installed `AbilityId` enum, then a repo-wide scan for the same class of bug turned up the rest. |
| Nydus Network cargo permanently stuck | `combat/harassment_coordinator.py:960` | `AbilityId.UNLOADALL_NYDUSNETWORK` doesn't exist (SC2 API naming quirk: correct is `UNLOADALL_NYDASNETWORK`). Units loaded into a Nydus Network for a drop could never be unloaded; the raised exception also aborted the rest of that `on_step` pass, intermittently skipping `_auto_adjust_aggressive_mode`/`_track_worker_kills`. |
| Baneling manual detonation never fires | `spell_unit_manager.py` (2 call sites), `comprehensive_unit_abilities.py` (2 call sites) | `AbilityId.EFFECT_EXPLODE` doesn't exist (correct: `EXPLODE_EXPLODE`). |
| Overlord "generate creep" harass never fires + wrong call shape | `comprehensive_unit_abilities.py:594` | `AbilityId.GENERATECREEP_GENERATECREEP` doesn't exist (correct: `BEHAVIOR_GENERATECREEPON`, a no-target toggle). The old code also passed a `target_position`, which is invalid for a toggle-behavior ability — fixed the call shape too. |
| Corruptor → Broodlord morph never fires | `unit_morph_manager.py:390` | `AbilityId.MORPH_BROODLORD` doesn't exist (correct: `MORPHTOBROODLORD_BROODLORD`). This is the live morph manager (wired via `bot_step_integration.py`); the late-game Broodlord transition has silently never worked. |
| Same class of bug in dead code | `local_training/advanced_building_manager.py` | `MORPH_RAVAGER`/`MORPH_BROODLORD` → `MORPHTORAVAGER_RAVAGER`/`MORPHTOBROODLORD_BROODLORD`. Fixed even though `AdvancedBuildingManager` is currently unused/uninstantiated anywhere in the codebase (working equivalents exist elsewhere) — left as a landmine otherwise. |

None of the above had test coverage encoding the broken behavior (confirmed: full suite was 672/672 passing both before and after the fix), which is exactly why they went unnoticed — nothing exercises the actual `.do()` call against a real or mocked SC2 API surface that would catch an invalid enum member. **Follow-up idea for a future run:** a cheap regression guard — a test that walks every `AbilityId.<NAME>` / `UnitTypeId.<NAME>` / `UpgradeId.<NAME>` / `BuffId.<NAME>` literal referenced in `wicked_zerg_challenger/` (excluding tests) and asserts the member exists on the installed enum — would have caught all of these mechanically. Not implemented yet.

Also fixed the same run: the CI-blocking `black --check --diff .` gate in `sc2bot-ci.yml` had been failing on `main` for a long time (66 pre-existing non-compliant files, unrelated to any single PR) — reformatted the whole repo with `black .` + `isort .` (both are deterministic, non-behavioral) so the gate is meaningful again. Separately, `.github/workflows/ci.yml`'s "Python 린트 & 테스트" job has an unrelated, pre-existing failure in the JARVIS crypto-trading/tool-orchestrator test suite (root-level `tests/`, not `wicked_zerg_challenger/`) — a `pyo3_runtime.PanicException` from the `cryptography` package's Rust bindings plus some `pytest-asyncio` event-loop errors in `tests/test_combat_phase_fsm.py` (a different file from the one of the same name under `wicked_zerg_challenger/tests/`). Confirmed via GitHub Actions history this was already failing on `main` before this branch existed (e.g. run for commit `8a80b735` "Update ci.yml") — out of scope for this SC2-bot-focused pass, left open, noted here so it isn't rediscovered as "new."

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
| P2.2 | Benchmark runner                                | ✅ Done (pre-existing, doc was stale) | `run_mass_test.py` already implements this: single command, matrix of maps x races x difficulties (incl. Hard), win-rate JSON report to `mass_test_results.json`. Requires a real SC2 game client to execute — cannot be run inside this headless review sandbox, only verified by reading the source. |
| P2.3 | Build-order config externalisation              | ❌ Open | Move top-20 hardcoded values to `config/build_orders.yaml`. No such file exists yet. |
| P2.4 | RL agent save-experience guard                  | ✅ Done (2026-07-11) | `tests/test_rl_agent_save_experience.py` — 4 new tests covering success, `np.savez_compressed` raising `OSError(ENOSPC)` (disk full), `os.rename` raising `OSError` (interrupted rename), and overwrite-of-stale-file. All confirm `save_experience_data()` returns `False` and never raises, and never leaves a partially-written target file. |
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
