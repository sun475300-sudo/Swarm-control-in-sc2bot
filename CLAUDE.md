# Working agreement for automated / scheduled sessions

This repo runs a recurring automated "test → find issues → fix → commit →
push → draft PR" task. Read this file **before** touching anything —
it exists because that automation ran unchecked and produced a large,
costly backlog (see below). Every fresh session starts with no memory
of prior sessions, so this file is the only place that knowledge persists.

## Before you write a single line of code

1. **Check the current open-PR count first**
   (`search_pull_requests` with `is:pr is:open`, or
   `mcp__github__list_pull_requests`). If it's already large
   (roughly >15–20), treat that as a signal that something is wrong
   with the workflow itself, not with the bot code — see "If the PR
   count is already large" below.
2. **Check for an existing open PR that already covers the fix you're
   about to make** before pushing a new branch. Skim titles/bodies for
   the failing test name, file, or symptom. If one exists and looks
   correct, do not re-derive and re-push the same fix — say so in your
   final report instead of opening another duplicate PR.
3. Only push a new branch/PR when you have work that is **not**
   already covered by an existing open PR.

## Merge / PR-lifecycle rules (durable — do not override)

- **No auto-merge, ever.** All PRs land only after the human owner
  (sun475300@gmail.com) reviews and merges them. This is a standing
  policy (see `MASTER_TODO_SC2.md` § 3, "머지 금지"), not a
  per-session choice.
- **No bulk-closing PRs** without the owner's explicit go-ahead in the
  conversation. Flagging duplicates in your report is fine; closing
  them yourself is not.
- **No direct push to `main`, no force-push, ever.** All changes go
  through a feature branch + draft PR.

## If the PR count is already large

As of 2026-07-18 this repo had **487 open PRs against 8 ever merged**
(last merge: PR #218, 2026-06-01). The overwhelming majority were
independent, automated re-diagnoses of the *same* handful of root
causes (`tests/test_combat_phase_fsm.py` using the deprecated
`asyncio.get_event_loop()` pattern; repo-wide `black`/`isort` drift
blocking `sc2bot-ci.yml`'s strict, repo-wide — not diff-scoped — lint
gate). Every automated session found a red test suite, "fixed" it
locally, and opened yet another draft PR, because:

- No session merges its own PR (see rule above), so `main` never
  actually improves.
- No session had visibility into the ~470 other sessions that hit the
  exact same failure and already opened a fix for it.

**If you find yourself about to open PR #488 for a problem that
#495–#525 already fixed independently, stop.** Instead:

1. Confirm the test suite is actually green (see "Sanity check"
   below) — if the fix already exists in an open PR, `main` is still
   red, but the fix doesn't need to be rediscovered again.
2. Report the current backlog size and point at the single best
   existing candidate PR (check `mergeable_state: clean` + a full test
   plan in the body) instead of adding another one.
3. Spend the rest of the session on work that is genuinely
   **not yet represented** in any open PR — check `TODO.md`,
   `PLAN-NIGHTLY.md`, `REMAINING_ISSUES.md`, `NEXT_LARGE_PLAN.md` for
   items with no corresponding open PR, or do a fresh pass focused on
   bot *behavior* (win rate, build-order timing) rather than
   lint/test-infra, which is almost certainly already over-covered.

## Sanity check before claiming "tests are failing"

```bash
python3 -m venv /tmp/sc2venv && source /tmp/sc2venv/bin/activate
pip install -r requirements-dev.txt burnysc2
python3 -m pytest -q                                   # root tests/ (pytest.ini scopes here)
cd wicked_zerg_challenger && python3 -m pytest tests -q # bot-specific suite (separate pytest.ini scope)
```

Both suites were fully green (502 passed / 14 skipped, and 661 passed)
as of 2026-07-18 once the `asyncio.get_event_loop()` fix below is
applied. If your run shows different numbers, note the delta in your
report — don't assume prior reports (including this one) are still
accurate without checking.

## Known root causes already diagnosed (check before re-diagnosing)

- `tests/test_combat_phase_fsm.py`: 5 call sites use
  `asyncio.get_event_loop().run_until_complete(...)`, which raises
  under Python 3.11 with no running loop on the thread. Fix is
  `asyncio.run(...)`. Already fixed on this branch; also present in
  open PRs #495–#525 (pick one, don't re-fix).
- `sc2bot-ci.yml`'s "Lint & Type Check" job runs `black --check --diff .`
  and `isort --check-only --diff .` **repo-wide**, not scoped to the
  diff. `main` has had unformatted files for a long time, so this gate
  blocks *every* PR regardless of correctness — this, not the FSM bug,
  is the actual reason the merge count has stayed at 8. PR #521
  reportedly applied `black`+`isort` repo-wide (66 files, mechanical
  only) and is worth checking as a merge candidate for clearing the
  gate once and for all.

## Scheduling note

The recurring task prompt asks for a **daily** check-in. Observed PR
creation timestamps show this firing roughly **hourly** instead — that
mismatch is very likely what produced the 487-PR backlog. If you have
visibility into the schedule/trigger configuration, flag this
explicitly in your report; it's a config problem, not a code problem.
