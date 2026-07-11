# Project Status & Documentation Index

> Single-page entry point into the documentation. Plan item **P1.5**
> (in `PLAN-NIGHTLY.md`) moved the 15 phase/bug historical reports below
> under `docs/history/`; the root copies have been deleted. A further
> batch of historical/manual docs (Korean session reports, architecture
> maps, etc.) is still awaiting the same move — see `docs/history/README.md`.

## ⚠️ Known security issue (unresolved)

`SENSITIVE_INFO_REPORT.md` documents Gemini API keys that were once
hardcoded in this repo. The key *files* were later removed from the
working tree, but the actual key values are still recoverable from git
history (confirmed present via `git log --all -S <key-prefix>`, ~5
commits each, for all 3 keys the report lists). **This repo is public.**
Anyone can retrieve the full keys from history right now. This needs:
1. Rotate/revoke all keys listed in `SENSITIVE_INFO_REPORT.md` in the
   issuing Google account — this cannot be done from inside the repo.
2. Separately and deliberately (not as a routine maintenance step):
   scrub the secrets from git history (e.g. `git filter-repo`) and
   force-push. This rewrites history for every clone/collaborator, so
   it needs the repo owner's explicit go-ahead before anyone runs it.

## Active / canonical (read these first)

| Document | Purpose |
|----------|---------|
| `README.md`                 | Project overview, install, run instructions. |
| `README_한국어.md`            | 한국어 개요 (mirror of `README.md`). |
| `CHANGELOG.md`              | Versioned change log. |
| `TODO.md`                   | Live to-do list (priority-ordered). |
| `TASK_WISHLIST.md`          | Longer-horizon task ideas / wishlist. |
| `PLAN-NIGHTLY.md`           | Nightly automation plan (P0/P1/P2). |
| `NEXT_LARGE_PLAN.md`        | Multi-phase roadmap (P800+ items, AI Arena). |
| `NEXT_PHASE_PLAN.md`        | Near-term phase plan. |
| `REMAINING_ISSUES.md`       | Known issues / open bug list. |
| `SECURITY.md`               | Security disclosure & coordinated reporting. |
| `SOUL.md`                   | Project north-star / design philosophy. |

## Architecture & code maps

| Document | Purpose |
|----------|---------|
| `CONTROL_FLOW_DIAGRAM.md`   | High-level control-flow diagram of the bot. |
| `FILE_DEPENDENCIES.md`      | Module-level dependency map. |
| `MODIFICATION_LIST.md`      | List of recent modifications (per-file). |
| `project_features.md`       | Feature inventory. |

## Phase / milestone reports (historical, moved to `docs/history/`)

| Document | Phase / scope |
|----------|---------------|
| `docs/history/MILESTONE_400.md`                      | Milestone 400 summary. |
| `docs/history/PHASE_19_SPELLCASTER_COMPLETION.md`    | Phase 19 (spellcasters). |
| `docs/history/PHASE_20_HIVE_TECH_COMPLETION.md`      | Phase 20 (hive tech). |
| `docs/history/PHASE_19_20_FINAL_SUMMARY.md`          | Phases 19+20 combined wrap-up. |
| `docs/history/EXPANSION_OPTIMIZATION_REPORT.md`      | Expansion-timing tuning report. |
| `docs/history/FINAL_OPTIMIZATION_SUMMARY.md`         | End-of-cycle optimization summary. |
| `docs/history/FINAL_QUICK_WINS_COMPLETION.md`        | Quick-wins wrap-up. |
| `docs/history/QUICK_WINS_IMPLEMENTATION.md`          | Quick-wins implementation notes. |
| `docs/history/ADDITIONAL_IMPROVEMENTS_REPORT.md`     | Misc improvement report. |
| `optimization_report_20260124.md`       | Dated optimization report. Still at root — candidate for `docs/history/`. |
| `docs/history/PROJECT_REVIEW_REPORT.md`              | Whole-project review. |
| `docs/history/SESSION_SUMMARY.md`                    | Working-session summary. |

## Bug & incident reports (historical, moved to `docs/history/`)

| Document | Scope |
|----------|-------|
| `docs/history/BUG_ERROR_LOG.md`             | Aggregated error log. |
| `docs/history/BUG_FIXES_REPORT.md`          | Aggregated bug fixes. |
| `docs/history/INTEGRATION_FIXES.md`         | Integration-level fixes. |
| `docs/history/ISSUES_FIXED.md`              | Per-issue fix log. |
| `SENSITIVE_INFO_REPORT.md`     | Sensitive-info exposure scan results. **See warning below — the keys it references are still recoverable from git history.** |
| `logic_test_results.md`        | Logic-test result snapshot. Still at root — candidate for `docs/history/`. |

## Manuals & training material

| Document | Purpose |
|----------|---------|
| `JARVIS_QA_MANUAL.md`       | QA manual (carry-over from sister project). |
| `future_improvements.md`    | Notes on future improvements. |
| `tomorrow_plan.md`          | Working "tomorrow plan" notes. |

## Korean-language reports (historical — candidate for `docs/history/`)

These are detailed Korean reports written during specific working
sessions and are largely retrospective. Most have an English-language
counterpart above.

- `개선_및_훈련_현황_보고서.md`
- `개선_현황_보고서.md`
- `개선_현황_보고서_최종.md`
- `부모님_연구보고서.md`
- `스타크래프트_2_AI_고도화_기획안.md`
- `인공지능에게_물어본_나의_인생고민.md`
- `최종_통합_개선_보고서.md`
- `프로젝트_설명문.md`
- `프로젝트_전체_진행_보고서.md`
- `프로젝트_전체_최적화_보고서.md`
- `학습_시스템_수정_보고서.md`

---

_Generated by nightly automation 2026-04-26. Update when the
`docs/history/` move lands so live links don't break._
