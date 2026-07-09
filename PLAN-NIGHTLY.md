# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-09

---

## Snapshot (current state)

- Branch: `main`, last commit: CI workflow update (`8a80b73`).
- Bot core: `wicked_zerg_challenger/` — 900+ Python files across the repo.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `ci.yml` runs flake8 + pytest (`wicked_zerg_challenger/tests/`) ✅
- **Test suite: 664 pass / 0 skip / 0 fail** ✅ (`wicked_zerg_challenger/tests/`, fresh venv, 2026-07-09)
- flake8 `F811/F821/F823/F401/E999` sweep of `wicked_zerg_challenger/`: clean (2 stray unused imports only).
- Audit finding: `REMAINING_ISSUES.md` and `TODO.md` (2026-01/04 vintage) were almost entirely stale —
  every item they listed as "open" (N1–N4, Issue #3/#4/#5/#6, TODO items 1–6) was already fixed in the
  code but never marked done in the docs. Both docs rewritten today to match actual code state; see their
  headers for verification pointers. Lesson for future nightly runs: verify against code before trusting
  doc "open" status.

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
| P2.2 | Benchmark runner                                | ❌ Open | Single command, N replays, APM/supply/win-rate report vs Hard. Needs a real SC2 client to write *and* verify — not doable from this sandbox (no game client installed). Pick up on a machine with SC2 installed. |
| P2.3 | Build-order config externalisation              | ❌ Open | Move top hardcoded values (`ZVT_BUILDS`/`ZVP_BUILDS`/`ZVZ_BUILDS` in `build_order_system.py`) to `config/build_orders.yaml`. Sizeable refactor touching all 3 matchups — deliberately deferred to its own session so it can be reviewed independently. |
| P2.4 | RL agent save-experience guard                  | ✅ Done (2026-07-09) | Found and fixed a real bug while adding the guard: `RLAgent.save_experience_data()` did `os.remove(existing)` *then* `os.rename(tmp, existing)` — if rename failed (disk full, interrupted process), the pre-existing valid save was already deleted and the new one never landed → silent data loss. Replaced with `os.replace()` (atomic overwrite on POSIX **and** Windows, no separate remove needed) + temp-file cleanup on failure. 3 new tests in `tests/test_rl_agent_save_experience.py` (roundtrip, simulated disk-full during write, simulated interrupted rename) — all pass. |
| P2.5 | Type hints + docstring pass on core modules     | 🟡 Mostly done | `core/resource_manager.py` (10/11 defs) and `core/manager_factory.py` (9/11 defs) already annotated. Remaining gaps are just `__init__(self, bot)` / `__post_init__(self)` — trivial, left as-is. |

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
- **2026-07-09** — Full re-audit: ran `wicked_zerg_challenger/tests/` (664 pass / 0 skip / 0 fail) and a targeted flake8 sweep (F811/F821/F823/F401/E999 — clean). Cross-checked every "open" item in `REMAINING_ISSUES.md` and `TODO.md` against the current code: all were already fixed (queen transfusion priority, resource-reservation lock, position_utils dedup, constants.py, duplicate-method F811s) but the docs never got updated — rewrote both to match reality. Found and fixed one real bug in the process: **P2.4** RL experience-save could silently lose data if the atomic rename step failed partway (see P2 table). Added regression tests. P2.2 (benchmark runner) and P2.3 (build-order config) confirmed still genuinely open and deferred — P2.2 needs a real SC2 client this sandbox doesn't have, P2.3 is a multi-matchup refactor better done as its own reviewed change.
