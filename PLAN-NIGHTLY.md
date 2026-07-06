# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-06

---

## Snapshot (current state)

- Branch: `main`, worked from `claude/optimistic-edison-nrzf4c`.
- Bot core: `wicked_zerg_challenger/` — 179+ Python files across 10+ subdirs.
- `.gitattributes` enforces `* text=auto` ✅
- CI: `sc2bot-ci.yml` lint (black/isort/mypy/bandit) still fails on main (66 files need black, several isort errors) — now **non-blocking** (`continue-on-error: true` on the `lint` job) so it no longer blocks `test`/`build`/`deploy`. Formatting cleanup is still tracked as open work (see P3 below), not resolved.
- **`pip install -r requirements.txt` is broken (`ResolutionImpossible`)** in a clean environment — reproduced live, not just theoretical. Root cause: pip's classic resolver can't settle the `s2clientprotocol`/`google-generativeai`/`boto3`/`mcp` graph (many unbounded `>=` pins) and backtracks for 10+ minutes before failing outright. `uv pip install` resolves the same file in ~27s. All 4 CI steps that ran `pip install -r requirements.txt` (`ci.yml` x4, `sc2bot-ci.yml` x1) now use `uv pip install --system -r requirements.txt` instead.
- **Test suite: 505 pass / 11 skip / 0 fail** ✅ ( full `sc2` install + fixes below — previously would not even collect without an `sc2` stub/install).
- `sc2bot-ci.yml` "Test Suite" job's unit-test step pointed at `pytest tests/unit` — **that directory doesn't exist**, so the step always failed. Fixed to `pytest tests/ --ignore=tests/integration`.

## Resolved this run (2026-07-06)

| Item | File(s) | Notes |
|------|---------|-------|
| `sc2` install fails in clean env | environment | `burnysc2`/`mpyq` sdist fails to build under vendored setuptools distutils (`AttributeError: install_layout`). Fix: `SETUPTOOLS_USE_DISTUTILS=stdlib pip install burnysc2 sc2reader`. Not a repo change, but needed to get real (non-stub) test coverage in a fresh sandbox. |
| `pip install -r requirements.txt` fails outright | `.github/workflows/ci.yml`, `.github/workflows/sc2bot-ci.yml` | Reproduced `ResolutionImpossible` from a clean env — this is CI-breaking, not just slow. Switched all 5 `pip install -r requirements.txt` CI steps to `uv pip install --system -r requirements.txt` (resolves in ~27s vs 10+ min pip backtrack-then-fail). Matches `MASTER_TODO_SC2.md` S3.2 recommendation. |
| `sc2bot-ci.yml` lint job blocks test/build/deploy | `.github/workflows/sc2bot-ci.yml` | `test` job has `needs: lint`; lint (black/isort/mypy --strict/bandit) fails on main today (66 files need `black`, multiple `isort` errors) so the whole pipeline (test → build → push → deploy) never runs. Added `continue-on-error: true` to the `lint` job (matches `MASTER_TODO_SC2.md` 1.6 option 1) plus `fail-fast: false` on its matrix (matches S3.1) so one Python version failing doesn't cancel the others. Formatting itself is **not** fixed — tracked separately, see P3. |
| `sc2bot-ci.yml` "Run unit tests" step targets nonexistent path | `.github/workflows/sc2bot-ci.yml` | `pytest tests/unit` — no such directory exists (canonical suite is `tests/`, per `pytest.ini`). Step always failed. Fixed to `pytest tests/ --ignore=tests/integration`. |
| `tests/test_combat_phase_fsm.py` — 12 failures | `tests/test_combat_phase_fsm.py` | `asyncio.get_event_loop().run_until_complete(...)` — Python 3.10+ no longer auto-creates a loop on the main thread when none is running, so `get_event_loop()` raises `RuntimeError: There is no current event loop`. Replaced all 5 call sites with `asyncio.run(...)`. All 23 tests in the file now pass; full suite: 493→505 passed, 12→0 failed. |
| `sc2bot-ci.yml` "Run integration tests" step missing `pytest-timeout` | `.github/workflows/sc2bot-ci.yml` | Surfaced by PR #303's own CI run: once the `lint`-gate fix let the `test` job actually execute for the first time, `pytest tests/integration -v --timeout=120` failed with `unrecognized arguments: --timeout=120` — the job's "Install dependencies" step never installed `pytest-timeout` (it's only in `requirements-dev.txt`, which this step doesn't use). Pre-existing latent bug, invisible until the job could run at all. Added `pytest-timeout` to the install line. |

**Net result: requirements.txt install now works from a clean environment (previously failed outright); CI pipeline is no longer wedged behind lint; 12 real test failures fixed; the newly-unblocked integration-test step's missing `pytest-timeout` dependency fixed. Suite: 505 pass / 11 skip / 0 fail.**

## Previously resolved (2026-05-03)

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
|------|-----------------------------------------------------------|--------|-------|
| P0.1 | `pip install -r requirements.txt` fails outright in CI    | ✅ Done | Switched to `uv pip install --system` in all 5 CI steps (2026-07-06). |
| P0.2 | `sc2bot-ci.yml` lint failure wedges test/build/deploy     | ✅ Done | `continue-on-error: true` + `fail-fast: false` on `lint` job (2026-07-06). |
| P0.3 | `sc2bot-ci.yml` unit-test step targets nonexistent `tests/unit` | ✅ Done | Fixed to `tests/ --ignore=tests/integration` (2026-07-06). |

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

## P3 — Formatting / lint debt (now non-blocking, still needs real cleanup)

| #    | Item                                            | Status | Notes |
|------|--------------------------------------------------|--------|-------|
| P3.1 | `black` formatting pass                          | ❌ Open | 66 files need reformatting. Do as a dedicated formatting-only PR (per `MASTER_TODO_SC2.md` §3 risk note — a broad black pass on main will conflict with any in-flight branches). |
| P3.2 | `isort` import-order pass                        | ❌ Open | Multiple files fail `isort --check-only`, incl. `mappo_marl/__init__.py`, `mappo_marl/sc2_mappo_agent.py`, `wicked_zerg_challenger/tests/test_zvz_phase3.py`, `test_zvt_phase1.py`. |
| P3.3 | `mypy --strict` baseline                         | ❌ Open | Currently non-blocking/informational only; needs a per-module baseline before it can gate CI. |
| P3.4 | Re-enable lint as blocking once P3.1–P3.3 land   | ❌ Open | Remove `continue-on-error` from `sc2bot-ci.yml` lint job once black/isort are clean on main. |

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
- **2026-07-06** — CI infra pass: `requirements.txt` install (was outright broken, `ResolutionImpossible`) fixed via `uv`; `sc2bot-ci.yml` lint job unblocked (`continue-on-error`, `fail-fast: false`) so test/build/deploy run even while black/isort are dirty; `tests/unit` (nonexistent path) fixed to real path; 12 `asyncio.get_event_loop()` failures in `test_combat_phase_fsm.py` fixed via `asyncio.run()`. Suite: 505 pass / 11 skip / 0 fail. Formatting debt tracked as new P3 (open, not fixed — needs its own PR per repo risk notes).
