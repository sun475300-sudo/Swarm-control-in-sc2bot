# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-09

---

## Snapshot (current state)

- Branch: `claude/optimistic-edison-ynsiem`, off `main` @ `8a80b73`.
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI blocking gate: `sc2bot-ci.yml` black/isort/flake8(E9,F63,F7,F82) ✅ clean on touched files
- **Test suite: 512 pass / 14 skip / 0 fail** ✅ (was 490 pass / 12 fail / 14 skip before this run)
- Note: other parallel `claude/optimistic-edison-*` branches are active in this repo (separate
  automated sessions) — several have failing `black --check` gates on their own diffs. Not this
  branch's scope; do not touch those branches.

## Resolved this run (2026-07-09)

| Item | File(s) | Notes |
|------|---------|-------|
| `test_combat_phase_fsm.py` 12/23 tests failing | `tests/test_combat_phase_fsm.py` | `asyncio.get_event_loop()` raises `RuntimeError: no current event loop` under pytest-asyncio 1.4.0 / Python 3.11. Replaced all 5 call sites with `asyncio.run(...)`. |
| **`RLAgent.save_model()` was a silent no-op** | `wicked_zerg_challenger/local_training/rl_agent.py` | `np.savez()` auto-appends `.npz` to any name that doesn't already end in it; `save_path.with_suffix(".tmp")` never matched the file numpy actually wrote (`model.tmp.npz`), so the rename step was always skipped, the function still returned `True`, and a stray `.tmp.npz` leaked on every call. Every RL checkpoint save has effectively been a no-op. Fixed to compute the tmp path the same way `save_experience_data` does. |
| Data-loss window in atomic save | same file | Both `save_model()` and `save_experience_data()` used `os.remove()` + `os.rename()`; a crash/failure between those two calls left neither file in place. Switched both to `os.replace()` (atomic on POSIX + Windows). `save_experience_data()` also now cleans up its temp file on failure. |
| No test coverage for RL save paths | `tests/test_rl_agent_save.py` (new, 10 tests) | Covers: save actually writes target, no orphan tmp files, weight round-trip, overwrite of existing file, disk-full failure preserves prior data, interrupted-rename failure preserves prior data. This directly closes P2.4 below. |

### Environment setup notes (for future runs)

- System `pip3 install burnysc2` fails building the `mpyq` wheel on this
  container's Debian-patched setuptools (`AttributeError: install_layout`).
  Use a clean venv instead: `python3 -m venv .venv && source .venv/bin/activate
  && pip install --upgrade pip setuptools wheel && pip install -r
  requirements-dev.txt && pip install burnysc2`. Builds cleanly there.
- `requirements-dev.txt` alone is not enough to import `tests/test_queen_transfusion.py`
  and friends — they need the real `sc2` package (`burnysc2`), not just pytest deps.

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
| P2.1 | Force-accumulation FSM tests                    | ✅ Done | `tests/test_combat_phase_fsm.py` — 23/23 passing. Regressed to 12/23 failing (pytest-asyncio version bump broke `asyncio.get_event_loop()`), re-fixed 2026-07-09. |
| P2.2 | Benchmark runner                                | ❌ Open | Single command, N replays, APM/supply/win-rate report vs Hard. |
| P2.3 | Build-order config externalisation              | ❌ Open | Move top-20 hardcoded values to `config/build_orders.yaml`. |
| P2.4 | RL agent save-experience guard                  | ✅ Done | Found + fixed `save_model()` silent no-op bug (tmp-path mismatch with numpy's auto `.npz` suffix) and a remove-then-rename data-loss window in both save paths. 10 new tests in `tests/test_rl_agent_save.py` covering disk-full and interrupted-rename. |
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
- **2026-05-04 / 05-06** — P1.6, P1.7 (queen transfusion) landed. 468 pass / 15 skip / 0 fail.
- **2026-06-01 / 06-02** — PR #218: stabilized suite further (F821 NameErrors, shadowed duplicate methods, missing methods called from production paths). Merged to `main`.
- **2026-07-09** — Ran full suite fresh (`pip install -r requirements-dev.txt burnysc2` in a clean venv): found `test_combat_phase_fsm.py` had regressed to 12/23 failing (`asyncio.get_event_loop()` incompatible with pytest-asyncio 1.4.0) — fixed. Found and fixed **P2.4**: `RLAgent.save_model()` was silently failing to save on every call due to a tmp-path/np.savez `.npz`-suffix mismatch, plus a data-loss window in the remove-then-rename atomic-save pattern used by both `save_model()` and `save_experience_data()`. Added 10 regression tests. Final: 512 pass / 14 skip / 0 fail.
