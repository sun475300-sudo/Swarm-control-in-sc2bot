# Improvement Tracker

Living backlog for the Wicked Zerg SC2 bot, re-derived from the repo's many
planning docs (`ROADMAP.md`, `MASTER_TODO_SC2.md`, `TODO.md`,
`NEXT_LARGE_PLAN.md`, `NEXT_PHASE_PLAN.md`, `PLAN-NIGHTLY.md`,
`tomorrow_plan.md`, `MASSIVE_FIX_PLAN.md`, `PROJECT_REVIEW_REPORT.md`,
`STRATEGY_PLAN.md`) cross-referenced against the actual code and `git log`,
plus test-suite runs, on 2026-07-03.

Update this file (don't create a new dated report) as items are closed or
new ones are found — that's the whole point of having one tracker instead of
another one-off snapshot doc.

## Headline finding

Most of the tactical/roadmap backlog in the older planning docs is **already
implemented**. Several docs (`ROADMAP.md`, `MASSIVE_FIX_PLAN.md`) frame their
tasks as urgent/not-started, but nearly all of the concrete engineering work
they describe already exists in code — in some cases the code matches the
roadmap's own proposed snippets verbatim (e.g. `intel_manager.py`'s
`BUILD_PATTERNS` dict). Treat those docs as historical context, not a current
plan. The real remaining gaps are narrower: closing the verification loop
(did the fixes move the win rate?), CI/process hygiene, and specific
matchup-micro polish.

## Status (2026-07-03)

- `tests/` — 502 passed, 0 failed, 14 skipped (all skips are optional-dep or
  missing-`config.yaml` gated).
- `wicked_zerg_challenger/tests/` — 661 passed, 0 failed.
- `flake8 --select=E9,F63,F7,F82` (critical: syntax errors, undefined names)
  — 0 findings repo-wide.
- `black --check` / `isort --check-only` — clean repo-wide (was 66 + 19 files
  out of compliance; fixed).

## P0 — Bugs / broken functionality affecting correctness or test health

1. **No post-fix win-rate validation exists.** `MASSIVE_FIX_PLAN.md`'s 19.3%
   win-rate figure and `ROADMAP.md`'s "45–50%" estimate both predate all 8
   of `MASSIVE_FIX_PLAN.md`'s own P0 fixes, which are already present in
   code (`grep "FIX P0-"` in `production_resilience.py`, `blackboard.py`,
   `strategy_manager_v2.py`, `economy_manager.py`). No document reports an
   actual re-measured win rate after that patch wave. Run
   `wicked_zerg_challenger/run_mass_test.py` (10 games each ZvT/ZvP/ZvZ vs
   Medium/Hard) to get ground truth before planning further tactical work.
   Needs a real StarCraft II client + maps, so this can't run in a headless
   CI sandbox — needs a session with the game installed.
2. **protobuf/s2clientprotocol version conflict breaks collection for some
   test files** (`TypeError: Descriptors cannot be created directly`) per
   `BUG_ERROR_LOG.md` ENV-001. Re-check whether this is still reproducible
   given the dependency versions currently pinned in `requirements.txt`.
3. **`sc2bot-ci.yml` lint gate** (black/isort/flake8/mypy --strict/bandit)
   — `black`/`isort` are now clean repo-wide; mypy --strict and bandit are
   `continue-on-error: true` so they don't block, but nobody is reading
   their output either. Low urgency to fix now that the blocking legs pass;
   worth revisiting when someone has bandwidth to triage the informational
   findings.
4. **~460 bare `except Exception:` blocks** across `wicked_zerg_challenger/`
   (up from "≈360+" reported previously), several in production/strategy
   code paths. This is the single biggest correctness-risk pattern in the
   codebase — it's the exact class of bug that let N1–N4 (shadowed duplicate
   methods, fixed in commit `e648ae4`) go unnoticed. Needs a triage pass:
   which excepts are load-bearing (expected failure modes) vs. silently
   hiding bugs.
5. **Stale open-PR inventory.** `MASTER_TODO_SC2.md` §1.1 lists ~16 open
   Claude-authored PRs as of 2026-04-26; several have since merged (e.g.
   PR #218). Re-audit open PRs before starting new overlapping work.

## P1 — Roadmap items still genuinely unimplemented

6. Matchup-specific combat micro not found in code: Protoss Psionic Storm
   dodge, Terran siege-tank surround micro (`STRATEGY_PLAN.md` Phase 5.1).
7. Attack-timing thresholds (`combat_manager.py:1901-1916`, supply
   16/25/35/45) don't reflect `MASSIVE_FIX_PLAN.md` P1-4's data-driven
   recommendation (supply 80 first push / 150 main push, derived from an
   88-game loss analysis where 86% of losses ended at supply 0–9).
8. `combat_manager.py` is ~5,000 lines, still a single-file god-object
   mixing micro/macro/threat-eval. The P3-3 split into
   `MicroController`/`MacroDecisions`/`ThreatEvaluator` was never done
   (unlike the analogous StrategyManager→BuildingManager split, which is
   done).
9. `_combat_power()` (`combat_manager.py:3070`) is HP×supply-weighted but
   not DPS-weighted per `MASSIVE_FIX_PLAN.md` P1-1
   (`(hp+shield) * (1 + dps/10)`).
10. No single benchmark-runner command producing an APM/supply/win-rate
    report vs Hard AI (`PLAN-NIGHTLY.md` P2.2).
11. Build-order values (13-pool timing, gas-start-drone-count, etc.) are
    still hardcoded in Python instead of `config/build_orders.yaml`
    (`PLAN-NIGHTLY.md` P2.3) — blocks quick tuning without redeploys.
12. No test exercises `save_experience()` (`local_training/rl_agent.py`)
    under disk-full / interrupted-rename conditions.
13. CI hygiene: add `fail-fast: false` to matrix jobs so one Python version
    failing doesn't cancel siblings (done for the lint matrix in this pass,
    see CHANGELOG); consider consolidating black+isort+flake8 → `ruff`;
    add a coverage floor to `sc2bot-ci.yml`; add a dependency lockfile.
14. 14 pytest skip/xfail cases across 4 test files never labeled as
    "intentional env-dependency" vs "broken, needs fix."
15. 27 TODO/FIXME markers across 7 files; `check_missing_logic.py`'s own
    TODOs are worth prioritizing since that tool catches
    called-but-never-defined bugs (see commit `fb0d61f`).
16. Type hints + docstring pass on `core/resource_manager.py`,
    `core/manager_factory.py`.
17. `REMAINING_ISSUES.md`'s open verification checklist (pathfinding cache
    correctness, unit-filtering optimization, Blackboard update-frequency,
    counter-build re-verification, scouting/expansion timing re-check)
    was never closed out.

## P2 — Planned improvements not yet started

18. Overseer/changeling automated cloak-detection deployment (ROADMAP 2.5).
19. Zergling map-patrol route system (ROADMAP 2.2).
20. Verify multi-prong attack group-splitting matches the 60/25/15% spec
    with distance-based staggered departure (ROADMAP 4.4).
21. Defense investment cap: commit ~50% of army to defense, stage the rest
    (`MASSIVE_FIX_PLAN.md` P1-5).
22. Verify spell-caster automation (Viper/Infestor) against
    `MASSIVE_FIX_PLAN.md` P2-6/P2-7's specific ability list.
23. Per-frame threat-scan caching to stay inside the 320ms/step Arena
    budget (`MASSIVE_FIX_PLAN.md` P2-2, P2-10).
24. Building auto-rebuild on destruction for core tech buildings.
25. Verify overlord safety repositioning actually reduces AA sweep losses.
26. Log-spam cooldown for repeated "CRITICAL THREAT DETECTED!"-style
    messages (`MASSIVE_FIX_PLAN.md` P3-1).
27. Per-manager `on_step` performance profiling against the 320ms budget.
28. Audit whether each `BUILD_PATTERNS` response actually fires end-to-end
    (detection is confirmed present; response wiring is unverified).
29. Codecov threshold enforcement per critical module.
30. ~~`IMPROVEMENT_TRACKER.md` cycle 6+ table referenced but missing~~ —
    fixed by creating this file.

## P3 — Nice-to-have / stretch / speculative

31. Verify RL-vs-rule-based auto-fallback comparison loop.
32. Curriculum-learning Stage 3 (macro+combat fusion) reward function.
33. Verify self-play ELO/matchmaking formula against spec.
34. Re-run and record the AI Arena package final checklist.
35. Mutation testing / SonarQube / dynamic profiling adoption.
36. Elite AI 50%+ win-rate stretch goal, MCTS/AlphaZero experiment.
37. TensorRT inference acceleration / Rust module expansion.
38. Real-time in-game dashboard (check for overlap with `sc2-ai-dashboard`
    first — significant functionality may already be shipped there).
39. Detailed per-matchup result logging (build order + timeline, not just
    win/loss).
40. F841 unused-variable cleanup in `visuals`/`make_pptx` (cosmetic).

## Docs that look stale/superseded — candidates to archive

- `NEXT_LARGE_PLAN.md`, `NEXT_PHASE_PLAN.md`, `PROJECT_REVIEW_REPORT.md` —
  generic ML-ops/infra scope-creep (Ray, K8s, TensorRT, ETL) with no
  SC2-gameplay content and no evidence any of it executed.
- `tomorrow_plan.md`, `TODO.md` — 2026-01-25/26 vintage; every concrete item
  is already implemented in current code.
- `BUG_ERROR_LOG.md` — one concrete bug (BUG-001) already fixed; keep only
  if ENV-001 (protobuf) still reproduces in real CI.
- `ROADMAP.md` — not worthless, but badly out of date (Sprints 1–5, 7 are
  essentially complete); needs a refresh pass rather than being treated as
  the current plan.
- Root-level historical `*_REPORT.md`/`*_SUMMARY.md`/`*_COMPLETION.md`
  files that already have copies under `docs/history/` per
  `PLAN-NIGHTLY.md` P1.5 — the root copies were never deleted after being
  copied.
- Two personal (non-project) Korean-language files at repo root
  (`부모님_연구보고서.md`, `인공지능에게_물어본_나의_인생고민.md`) look like
  accidental commits — worth confirming with the repo owner before any
  cleanup pass touches them.
