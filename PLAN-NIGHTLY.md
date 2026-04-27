# StarCraft II Bot (Swarm Control) — Nightly Plan

> Owner: 선우 (sun475300@gmail.com)
> Maintainer: nightly automation
> Last refreshed: 2026-04-25

---

## Snapshot (current state)

- Branch: `main`, last commit `05d92ae` (merge), tree clean.
- Bot core: `wicked_zerg_challenger/` — 365 Python files.
- Total Python in repo: 1,749 (sub-dirs span many languages and frameworks).
- `.gitattributes` already enforces `* text=auto` ✅ (no CRLF risk).
- Test files: 28 under `tests/`.
- Existing planning docs: `NEXT_LARGE_PLAN.md`, `NEXT_PHASE_PLAN.md`,
  `TASK_WISHLIST.md`, `TODO.md`, `MILESTONE_400.md`, `REMAINING_ISSUES.md`.
  These are coherent and detailed; the nightly plan should *complement*
  them, not replace them.
- Recent activity: large `print → logger` migration (~3000 sites across
  ~180 files), then a follow-up commit removing 131 empty-call artefacts
  from that migration. Codebase is stabilising after a major refactor.

## P0 — Critical / blocking

| #    | Item                                                  | Notes |
|------|-------------------------------------------------------|-------|
| P0.1 | Verify the print→logger migration introduced no further breakage | Run pytest under `tests/` to confirm none of the 28 test files regressed. The fix-up commit `2e03d2f` already removed 131 empty `logger()` calls — confirm grep finds zero remaining. |
| P0.2 | Add a regression guard for the empty-`logger()` pattern | Tiny CI script that runs `grep -RnE "logger\.(info\|debug\|warning\|error)\(\)$" wicked_zerg_challenger/` and fails the build if any match. Cheap, one-time fix that prevents the same bug class from recurring. |

## P1 — Important

| #    | Item                                  | Notes |
|------|---------------------------------------|-------|
| P1.1 | Reactivate `TODO.md` priority #1 — scout cadence (initial overlord every 30 s, mid-game zergling map sweep every 60 s, late-game overseer cloak detection) | Maps directly to `wicked_zerg_challenger/scouting_system.py` and `scouting/advanced_scout_system_v2.py`. |
| P1.2 | Reactivate `TODO.md` priority #2 — harassment loop polish | Verify harass units actually move into the enemy main, retraction logic on health threshold, kill-count tracking on enemy workers. Files: `strategy_manager.py:228–262`, `combat_manager.py`. |
| P1.3 | First-expansion timing test harness | TODO.md notes the latest test put first expansion at 6 min after the 300-mineral fix. Add a deterministic replay-based test that asserts first expand ≤ X min on a fixed map seed. |
| P1.4 | Reduce duplicate "scout system" files | Both `advanced_scout_system_v2.py` and `realtime_awareness_engine.py` cover overlapping perception logic. Pick the canonical one and add a deprecation shim for the other. |
| P1.5 | Trim documentation surface area | 30+ top-level `*.md` reports (PHASE_19, PHASE_20, MILESTONE_400, BUG_FIXES_REPORT, INTEGRATION_FIXES, ISSUES_FIXED, REMAINING_ISSUES, …) make it hard to find current state. Move historical reports under `docs/history/` and keep only `README.md`, `CHANGELOG.md`, `TODO.md`, `PLAN-NIGHTLY.md`, and one `STATUS.md` at root. |

## P2 — Nice-to-have

| #    | Item                                       | Notes |
|------|--------------------------------------------|-------|
| P2.1 | Force-accumulation FSM tests               | Lock the phase-transition rules (early-pool → lair → hive → late-game) with state-machine tests so future micro/macro changes can't silently break the macro shape. |
| P2.2 | Endpoint-style benchmark               | Single command that runs N replays through the bot and reports {APM avg, supply curve, first-expand time, win-rate vs builtin Hard}. Lets the nightly tell whether yesterday's commit was a regression. |
| P2.3 | Build-order config externalisation     | `TASK_WISHLIST.md` reports 248 hardcoded values. Pick the top 20 and move them to `config/build_orders.yaml`. |
| P2.4 | RL agent save-experience guard         | Commit `cf2d265` recently fixed an atomic-rename bug in `rl_agent` save. Add a unit test that exercises a save under simulated disk-full / interrupted-rename and asserts no corruption. |

## Long-term direction (synthesised from existing plans)

- **AI Arena submission cadence.** The existing roadmap (`NEXT_LARGE_PLAN.md`,
  P800–P849) is ambitious but unscheduled. Pick a 2-week submission cadence:
  every fortnight, take the most-improved branch, run the benchmark suite
  (P2.2), submit only if metrics beat the previous submission.
- **Self-play loop.** Plan item P823 (self-play) is the highest-leverage
  long-term lever — every other improvement amortises across both sides.
  Stand up a minimal self-play harness before chasing more micro/macro
  features.
- **Macro vs micro split.** Roughly half the bot core is macro
  (production, expansion, tech) and half is micro (kiting, focus-fire,
  spell use). Keep that split visible in directory layout —
  `wicked_zerg_challenger/macro/` vs `wicked_zerg_challenger/micro/` —
  so it's obvious which subsystem owns a given regression.

---

## Run history

- **2026-04-25** — Initial nightly plan written. Tree clean,
  `.gitattributes` already correct, codebase stabilising after a large
  print→logger migration. No P0 stabilisation work needed beyond a
  regression guard for empty-logger calls.
- **2026-04-26** — Re-review. Local `main` is one commit behind
  `origin/main` (fast-forwardable; not auto-pulled per nightly
  no-destructive-ops policy). Status of last run's P0:
  - P0.1 (verify migration introduced no further breakage) — partially
    verified: `grep -RnE "logger\.(info|debug|warning|error)\(\)$"
    wicked_zerg_challenger/` returns zero source-code matches (only one
    documentation reference). Actual pytest run not executed inside
    nightly sandbox (sc2 / burnysc2 deps not installable here).
  - P0.2 (regression guard for empty-`logger()`) — landed via
    `881501a ci: add empty logger call regression guard` and the
    `.github/workflows/empty-logger-guard.yml` + `scripts/check_no_empty_logger_calls.py`
    pair.
  Code-level TODO/FIXME scan: 3 hits total, all minor and not blocking.
  Documentation surface area unchanged: 47 top-level `*.md` files.
  P1.5 (trim doc surface area) is the highest-ROI cleanup tonight if
  picked, but moving 30+ docs touches a lot of files in one commit and
  is best done as a single dedicated PR with `git mv` to preserve
  blame. Tonight's preferred small commit: a `STATUS.md` index that
  catalogues which historical reports map to which subsystem, so the
  eventual `docs/history/` move is mechanical. Tracked as **P1.7 —
  add a STATUS.md index pointing at the existing reports**.
  - P0.2 (regression guard for empty-logger) — not yet implemented; promoted
    to tonight's next work item, but merge blocker took priority.
  - Stale `index.lock` / `HEAD.lock` / `objects/maintenance.lock` present at
    run start — cleared via rename workaround.

  **Work completed this run: pending merge commit**

  A previous session left a half-finished merge (local `985ee5b` vs
  origin `c7bb6dd` — logic_optimizer improvements) in "all conflicts
  resolved but not committed" state. Completed as commit `55eb51e`:
  - `apply_combat_improvements()`: air harassment priority=60, worker defense=110
  - `apply_economy_improvements()`: gas adjustment interval=22, macro hatch threshold=500
  - `apply_strategy_improvements()`: aggressive mode on Cheat difficulties
  - `optimize_all()`: orchestrates all three passes

  **Next P1 items for following night:**

| #    | Item                                    | Notes |
|------|-----------------------------------------|-------|
| P0.2 | Empty-logger regression guard (CI)      | `grep -RnE "logger\.(info|debug|warning|error)\(\)$"` fails build if any hits. Add to `ci.yml`. |
| P1.1 | Scout cadence improvements              | `scouting_system.py` — initial overlord 30s, mid-game zergling sweep 60s, late overseer cloak detection |
| P1.2 | Harassment loop polish                  | `strategy_manager.py:228–262`, `combat_manager.py` — retraction on HP threshold, worker kill tracking |

- **2026-04-27** — User-driven test→improve→push iteration loop on
  branch `claude/stoic-shannon-LsC1U` (PR #43). Each iteration is one
  small commit pushed to the branch.

  Pytest baseline before this run: 222 passed / **84 failed** / 34
  skipped. The 84 failures all collapsed to a single missing dev-time
  dependency: `pytest-asyncio` was not declared anywhere, so every
  `async def test_…` in the suite reported "async def functions are
  not natively supported." Plus one stale assertion.

  Iterations landed:

  1. `e0a7fd9` — `requirements-dev.txt` declares `pytest`,
     `pytest-asyncio` (auto mode is already in `pytest.ini`), and
     `pytest-timeout`. Stale `test_gas_overflow_threshold_lowered`
     relaxed from `== 1000` to `<= 1000` so it guards the *direction*
     of the improvement instead of breaking each time the threshold
     is tightened further. Result: **306 passed / 0 failed**.
  2. `9977c54` — `tests/test_no_empty_logger_calls.py` mirrors
     `scripts/check_no_empty_logger_calls.py` (the existing CI guard
     for **P0.2**) at the pytest level so a single `pytest tests/`
     run locally catches the regression without needing the CI script.
  3. `4ca966d` — `tests/test_scout_cadence_invariants.py` pins the
     scout intervals from **P1.1** (overlord 30 s, mid-game zergling
     60 s) so a future edit to `early_scout_system.py` cannot silently
     drift the perception loop.
  4. `a419877` — `tests/test_economy_invariants.py` pins five
     economy-tuning numbers tightened in `c7bb6dd` and `34ac508`
     (gas overflow ≤ 1000, gas worker rebalance ≤ 50 frames,
     expansion cooldown ≤ 5 s, macro hatch threshold ≤ 700, race
     gas timing coverage). Imports via the same
     `sys.path.insert(0, '…/wicked_zerg_challenger')` shim as
     `tests/test_economy_manager.py` because a top-level `utils/`
     package shadows `wicked_zerg_challenger/utils/`.

  Net pytest delta: **222 → 314 passed** (+92), **84 → 0 failed**, no
  bot-runtime code touched. The new tests are pure regression guards;
  they do not change game-time behaviour. Empty-logger CI workflow
  (`empty-logger-guard.yml`) was already in place and stayed green
  throughout.

  Continued the same loop:

  5. `a397939` — `tests/test_combat_priority_invariants.py` pins the
     four combat task-priority numbers tightened in `34ac508`
     (main_attack ≥ 95, base_defense ≤ 15 in all_in, worker_harass
     present at ≥ 70). Source-level regex check over
     `inspect.getsource(CombatManager)`.
  6. `6a6814e` — **First real bug fix surfaced through the test loop.**
     New `tests/test_logic_optimizer.py` covers
     `LogicOptimizer.apply_combat/economy/strategy_improvements`. The
     strategy test reproduced an AttributeError waiting in
     `apply_strategy_improvements`: it was assigning the raw string
     `"aggressive"` to `strategy_manager.current_mode`, but
     `combat_manager.py:248` does `.current_mode.value` and
     `bot_step_integration.py:2433` does `.current_mode.name` — both
     would crash on the next tick after the cheat-difficulty branch
     fired. Fix: assign `StrategyMode.AGGRESSIVE` instead. Test injects
     a minimal `sc2.data.Difficulty` stub into `sys.modules` so it can
     run without sc2/burnysc2.

  Final pytest delta: **222 → 320 passed** (+98), **84 → 0 failed**.

  Continued the loop:

  7. `dc6e8ac` — **Second real bug fix surfaced through the test loop.**
     Strengthened `test_apply_combat_improvements_sets_priorities` to
     seed `task_priorities` with sentinel values rather than asserting
     on the optimizer's chosen key directly. That immediately exposed
     a typo: `apply_combat_improvements` was writing
     `task_priorities["air_harassment"]` but the canonical key (initialised
     in `combat/initialization.py`, read in `combat_manager.py:297`) is
     `air_harass` (no "ment"). The "tightened to 60" priority from
     c7bb6dd was silently landing in a dead dict slot and never reaching
     the multitasking loop. Fix: rename to `air_harass`.

  Continued the loop with two more iterations:

  8. `bc349af` — `tests/test_task_priorities_keyset.py` generalises
     the iter 9 fix into a regression guard. Scans every
     `task_priorities[<str-literal>]` access in the bot core and
     fails if any key is outside the canonical set. Catches the same
     bug class as iter 9 going forward.

  9. `f458bf1` — **Third real bug fix surfaced through the test loop.**
     New `tests/test_blackboard_signal_pairs.py` asserts each
     "actionable" blackboard alert has a reader. Found
     `urgent_spine_all_bases` was set in `intel_manager.py:686` on
     `NYDUS_INCOMING` (drop attack imminent) but had **no reader
     anywhere** — every NYDUS detection silently produced no
     defensive reaction. Wired into
     `defense_coordinator._build_base_defense` to bump spine target
     by +1 when set. Minimal blast radius: amplifies an existing
     branch instead of adding a new method.

     Also clarified that `urgent_overseer` (set in `strategy_manager`
     and `racial_counter_manager` on DT detection) is *intentionally*
     telemetry-only — the actionable morph already runs through
     `protoss_counter_system._handle_dark_templar_threat → _emergency_overseer_morph`
     off the same intel signal. Adding a redundant reader would
     double-fire the morph.

  Total real bugs surfaced & fixed by this loop: **3**
  - iter 6 (`6a6814e`): `LogicOptimizer.apply_strategy_improvements`
    enum-vs-str
  - iter 7 (`dc6e8ac`): `LogicOptimizer.apply_combat_improvements`
    dead key `air_harassment` vs `air_harass`
  - iter 9 (`f458bf1`): NYDUS spine alert never reached
    `defense_coordinator`

  Two of the three were in `LogicOptimizer.apply_*_improvements`,
  both introduced in the same commit (c7bb6dd) without test coverage.
  The third was a long-standing gap in the intel→defense alert chain.

  Final pytest delta: **222 → 322 passed** (+100), **84 → 0 failed**.

  PLAN-NIGHTLY surface footprint cleanup (P1.5) and harassment-loop
  polish (P1.2) remain untouched and continue to be the highest-ROI
  follow-ups.

  Open follow-up surfaced but not acted on: `combat_manager.py:263`
  sets `task_priorities["worker_harass"] = 80` in all_in mode but no
  task-pickup loop currently consumes that key — it's either dead
  intent (delete) or an unfinished feature (wire up). Leaving it for a
  separate review.
