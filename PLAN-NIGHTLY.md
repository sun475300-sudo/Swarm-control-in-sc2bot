# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-18

---

## Snapshot (current state)

- Branch: `claude/optimistic-edison-8abyik`, base `main` @ `8a80b73`.
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` runs black + isort + flake8 ✅ (all clean)
- **`tests/`: 502 pass / 14 skip / 0 fail** ✅. **`wicked_zerg_challenger/tests/`: 668 pass / 0 fail** ✅ (run as two separate suites — matches how CI invokes them; running both under one `pytest` process collides on the `scripts` module name, pre-existing and out of scope).
- Queen transfusion logic: 3 bugs fixed (`is_idle` guard removed, target dedup, per-queen cooldown) ✅

## Resolved this run (2026-07-18)

| Item | File(s) | Notes |
|------|---------|-------|
| CI never actually ran `tests/` | `.github/workflows/ci.yml` | The "pytest 실행 (전체)" step ran `pytest tests/ -v --tb=short --co -q` — `--co` is **collect-only**, so ~500 tests were only ever collected, never executed, in `python-lint-test`. Removed `--co`; the job now really runs the suite. |
| `tests/unit` doesn't exist | `.github/workflows/sc2bot-ci.yml` | The `test` job ran `pytest tests/unit -v ...`; no such directory exists (flat files live directly under `tests/`). Changed to `pytest tests/ --ignore=tests/integration -v ...`. |
| `sc2` package silently degraded to broken stub classes | `requirements.txt` | Missing `loguru` (required by `sc2.bot_ai`) makes the whole `try: from sc2... except ImportError:` block in several bot modules (e.g. `scouting/advanced_scout_system_v2.py`) fall back to bare `class UnitTypeId: pass` — no import error, but every `UnitTypeId.X` access then raises `AttributeError` at call time. Pinned `loguru`, `portpicker`, `scipy` (burnysc2's real deps) and `protobuf<=3.20.3` (newer protobuf breaks `s2clientprotocol`'s pre-generated `_pb2.py` files: "Descriptors cannot be created directly"). Added `cffi` (cryptography's Fernet needs it in this environment). |
| `tests/test_combat_phase_fsm.py` — 12 failures | same file | `asyncio.get_event_loop()` is invalid outside a running loop on Python 3.11 ("no current event loop in thread"). Replaced all 5 call sites with `asyncio.run(...)`. |
| **`RLAgent.save_model` silently no-ops** | `wicked_zerg_challenger/local_training/rl_agent.py` | `tmp_path = save_path.with_suffix(".tmp")` (e.g. `model.tmp`) but `np.savez(str(tmp_path), ...)` auto-appends `.npz` to any name that doesn't already end with it → actually writes `model.tmp.npz`. The subsequent `if tmp_path.exists():` check looks for `model.tmp` and is always `False`, so the rename never happens — yet the function still logs "saved" and returns `True`. **Every `save_model()` call was a no-op that never touched the real model file**, leaving an orphaned `*.tmp.npz` each time. Fixed by giving `tmp_path` a name that already ends in `.npz`. |
| `RLAgent.save_experience_data` leaks temp file on rename failure | same file | If `os.rename` raised (e.g. disk full mid-rename), the `except` block logged and returned `False` but never removed the already-written `*.tmp.npz`. Now cleaned up in the `except` block. |
| New regression coverage | `wicked_zerg_challenger/tests/test_rl_agent_save_guard.py` (new, 7 tests) | Exercises both save paths under disk-full (`np.savez`/`np.savez_compressed` raising) and interrupted-rename (`os.rename`/`shutil.move` raising) — this is PLAN-NIGHTLY item **P2.4**. |
| `REMAINING_ISSUES.md` stale | doc | N1–N4 (duplicate-definition F811 bugs) were already fixed by PR #218; verified via `flake8 --select=F811` (0 hits) and marked resolved instead of "open". |

**Net result:** 12 failures + 0 real functional bugs found → 0 failures, plus one previously-invisible functional bug (RL model checkpoints never actually saving) fixed and covered by tests.

## Roadmap audit (2026-07-18, vs `ROADMAP.md` Sprint 1–8)

Full audit run via a dedicated agent pass, checking each roadmap task against actual code (not just filenames). Summary — only the non-DONE items:

| Task | Status | Gap |
|------|--------|-----|
| 1.1 Remove non-ASCII/emoji log chars | ❌ MISSING | `early_defense_system.py` alone still has ~91 emoji/glyph occurrences; ~112 of ~140 top-level `.py` files still contain them. Cosmetic/robustness item (console encoding crashes on some Windows locales), not attempted this run — large mechanical diff, best done as its own PR. |
| 7.2 Distance-calc caching | 🟡 PARTIAL | `utils/distance_cache.py` exists and is correctly wired into `combat_manager.py`/`economy_manager.py`, but only ~7 call sites use it while raw `.distance_to(` is still called ~60x in `combat_manager.py` and ~24x in `economy_manager.py`. Migration incomplete. |
| 7.3 Magic numbers → `GameConstants` | 🟡 PARTIAL | `utils/game_constants.py`'s `GameFrequencies`/`EconomyConstants` exist and are used in a few files, but ~84 raw `% 22`/`% 33`/`% 66`/etc. magic-number checks remain across ~30 other files. |
| 8.2 Arena package validation | 🟡 PARTIAL | `create_arena_package.py` builds the ZIP but the roadmap's checklist (10MB hard limit, 320ms/step profiling gate) isn't automated/enforced — currently manual-only. |

All of Sprints 1–6 (and 7.1) are confirmed DONE with matching constants/method names. These four gaps are the accurate remaining backlog — not the roadmap's original wording, which is otherwise stale.

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
| P2.4 | RL agent save-experience guard                  | ✅ Done | `test_rl_agent_save_guard.py` (7 tests) — found and fixed a real bug: `save_model` never actually saved (tmp-file suffix mismatch made the rename a permanent no-op while still returning `True`); also fixed a temp-file leak in `save_experience_data` on rename failure. |
| P2.5 | Type hints + docstring pass on core modules     | ❌ Open | `core/resource_manager.py`, `core/manager_factory.py`. |
| P2.6 | Distance-cache migration completion             | ❌ Open | (new, from 2026-07-18 roadmap audit) Only ~7 of ~90+ `distance_to(` call sites in `combat_manager.py`/`economy_manager.py` use `DistanceCache`. |
| P2.7 | Magic-number → GameConstants adoption            | ❌ Open | (new) ~84 raw `% 22`/`% 33`/etc. checks remain outside the 3 files that already import `game_constants`. |
| P2.8 | Non-ASCII/emoji log-character cleanup            | ❌ Open | (new, was Sprint 1 Task 1.1) ~112 of ~140 files under `wicked_zerg_challenger/` still use ⚪✓✅🔴❌ etc.; large mechanical diff, do as its own PR. |
| P2.9 | Arena package checklist automation               | ❌ Open | (new) `create_arena_package.py` has no automated 10MB size gate or 320ms/step profiling check — currently manual verification only. |

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
- **2026-07-18** — CI was silently only *collecting* (not running) `tests/` (`--co` flag) — fixed. Fixed `tests/unit` path in `sc2bot-ci.yml` (dir never existed). Pinned missing/incompatible deps (`loguru`, `portpicker`, `scipy`, `protobuf<=3.20.3`, `cffi`) that made `sc2.ids.unit_typeid.UnitTypeId` silently degrade to a broken stub — root cause of the "`UnitTypeId` has no attribute `OVERLORD`" class of failures. Fixed 12 `test_combat_phase_fsm.py` failures (`asyncio.get_event_loop()` → `asyncio.run()`, Python 3.11). **Found and fixed a real production bug:** `RLAgent.save_model()` had a tmp-filename/`.npz`-suffix mismatch that made every save silently no-op while still returning `True` — model checkpoints were never actually persisted. Also fixed a temp-file leak in `save_experience_data()`. Added 7 regression tests (P2.4, closed). Ran a full roadmap audit (Sprint 1–8): everything is DONE except 1.1/7.2/7.3/8.2, now tracked as P2.6–P2.9. Closed stale REMAINING_ISSUES.md N1–N4 (already fixed by PR #218, verified via `flake8 --select=F811`). Result: `tests/` 502 pass / 14 skip, `wicked_zerg_challenger/tests/` 668 pass, 0 fail overall.
