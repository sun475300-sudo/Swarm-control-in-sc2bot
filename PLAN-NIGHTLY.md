# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-07-19

---

## 🔴 P0 finding (2026-07-19): the CI fix didn't solve the merge pile-up — it needs a human triage decision, not another automated fix PR

PR #533 (merged 2026-07-18) fixed the actual root cause of red CI
(repo-wide black/isort check), but the PR count kept growing anyway:
**510 open PRs as of today, only 9 ever merged in the repo's entire
history** (#42, #44, #49, #218, #533 + 4 older). At least 9 sessions
in a row (#543–#553, all opened 2026-07-19 alone) independently
rediscovered this same pile-up, flagged it in their own PR description,
and then each added yet another PR anyway instead of stopping. This
session broke that cycle: no new bug-fix PR was opened, and a
full read-only triage of all 510 open PRs was run instead. Full
methodology and exhaustive PR-number lists are in the PR that carries
this doc update; summary here:

**Cluster breakdown** (root cause → how many open PRs duplicate it):

| Cluster | Count | Status |
|---|---|---|
| `asyncio.get_event_loop()` deprecation in `test_combat_phase_fsm.py` | 198 | **Already fixed on `main`** — all stale, safe to close |
| Repo-wide black/isort CI-lint-gate failure | 63 | **Fixed by merged #533** — all but #543 stale |
| Generic "iterative test/improve cycle" titles (Korean + English), no specific bug | 88 | Can't verify individually; mostly Apr–Jun, likely stale |
| `scripts/__init__.py` missing → namespace-package collision | 4 | **Still broken on `main`** (verified directly) |
| `RLAgent.save_model()` `.tmp`/`.tmp.npz` atomic-rename no-op | 4 | **Still broken on `main`** (verified directly) |
| Silently-skipped async tests (`TestCase` + unwaited `async def test_*`) | 18 | Real bug class; #532/#552 most complete |
| Lurker burrow-to-attack dead code | 5 | Real; #531 and #537 touch the same function, will conflict |
| Centroid/position-calc dedup refactor | 5 | Refactor; #536 most complete |
| Pure "PR pile-up" meta-commentary, no code diff | 7-8 | #548 is the exception (adds real `CLAUDE.md`) |

**Recommended to merge** (ranked; each fixes a still-live bug or adds
real value, verified independently — not just by trusting the PR's own
description): **#544, #550, #551, #532, #549, #545, #531, #536, #546,
#543, #547, #548.**

**Recommended to bulk-close as stale/duplicate**: the full
asyncio-cluster and black/isort-cluster PR-number lists (~260 PRs),
plus #534/#535/#553 (scripts/ dupes of #544), #304/#524/#535
(save_model dupes of #544), #552 (async-test dupe of #532),
#328/#430/#443 (lurker dupes of #531), #72/#326/#379/#471 (centroid
dupes of #536), and the 12 oldest open PRs (#15/#16/#18-21/#28/#31/
#45-48, stale since April with zero follow-up). Exhaustive numbers are
in this session's PR description, not duplicated here to keep this
doc lean.

**Other things worth the owner's attention:**
- PR volume was ~1-4/day through April, ~7-15/day in May, then
  **15-23 PRs/day every day since 2026-07-02** — confirms several
  prior sessions' suspicion that the automation trigger is firing much
  more often than the requested "daily" cadence. Worth checking the
  trigger/schedule config directly.
- **~98-99 open Dependabot alerts** on `main` (2 critical, 37 high, 46
  moderate, ~13-14 low), reported independently by #533/#541/#542.
  No open PR in the backlog touches these — needs a separate pass.
- CI is otherwise green on `main` post-#533 (lint/test/build/registry
  jobs); only `Deploy Rolling Update` is red (no `KUBE_CONFIG` secret,
  fixed by #546).

**Action needed from the repo owner** — this cannot be resolved by
another automated fix-and-push cycle: (1) decide on the merge/close
list above, (2) check the trigger schedule config for the actual
firing frequency, (3) decide whether to schedule a Dependabot triage
pass separately.

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
- **2026-07-19** — **Deliberately opened no new fix PR.** Full read-only triage of all 510 open PRs instead: confirmed test health matches today's other sessions (0 failures), confirmed `main` is otherwise healthy, and produced the cluster/merge/close breakdown above. Root cause of the pile-up is now a human review bottleneck + an overly-frequent trigger, not missing fixes — see P0 finding above.
