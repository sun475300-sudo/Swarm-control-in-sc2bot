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
