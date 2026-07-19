# Working agreement for automated / scheduled sessions

This repo runs a recurring automated "test → find issues → fix → commit →
push → draft PR" task. **Read this file before touching anything.** It
exists because that automation ran unchecked and produced a large, costly
backlog (see below). Every fresh session starts with no memory of prior
sessions, so this file is the only place that knowledge persists.

## Before you write a single line of code

1. **Check the current open-PR count first**
   (`search_pull_requests` with `is:pr is:open`, or `list_pull_requests`).
   If it's already large (roughly >15-20), treat that as a signal that
   something is wrong with the workflow/schedule itself, not with the bot
   code — see "If the PR count is already large" below.
2. **Check for an existing open PR that already covers the fix you're
   about to make** before pushing a new branch. Skim titles/bodies for the
   failing test name, file, or symptom. If one exists, do not re-derive and
   re-push the same fix — say so in your report instead of opening another
   duplicate PR.
3. Only push a new branch/PR when you have work that is **not** already
   covered by an existing open PR.

## Merge / PR-lifecycle rules (durable — do not override)

- **No auto-merge, ever.** All PRs land only after the human repo owner
  reviews and merges them. This is a standing policy (see
  `MASTER_TODO_SC2.md` §3, "머지 금지"), not a per-session choice.
- **No bulk-closing PRs** without the owner's explicit go-ahead in the
  conversation. Flagging duplicates/stale PRs in your report is fine;
  closing them yourself is not.
- **No direct push to `main`, no force-push, ever.** All changes go
  through a feature branch + draft PR.

## If the PR count is already large

As of 2026-07-19 this repo had **~504 open PRs against only 2 ever
merged** (#218, #533). The overwhelming majority are independent,
automated re-diagnoses of the *same* handful of root causes — most
visibly ~13 separate PRs (#491, #493, #503, #517, #520, #521, #522, #523,
#526, #527, #528, #529, #530), all created within the same hour on
2026-07-18, all fixing the identical `tests/test_combat_phase_fsm.py`
`asyncio.get_event_loop()` deprecation bug. **That bug is already fixed
on `main`** (verified 2026-07-19: `test_combat_phase_fsm.py` — 23/23
pass, no `get_event_loop` usage left in `tests/`) — so all ~13 of those
PRs are now stale/obsolete and are safe candidates for the owner to
close without re-review.

This happened because:
- No session merges its own PR (see rule above), so visibility into
  "did this already land on main" requires an explicit check — sessions
  that skipped it re-fixed an already-fixed bug.
- No session had visibility into the ~500 other sessions that hit the
  same failure and already opened a fix for it.

**If you find yourself about to open a PR for a problem an existing
open PR (or `main` itself) already fixes, stop.** Instead:

1. Confirm what's actually true on `main` right now (run the suite,
   `grep` for the pattern) — don't trust an old PR body or report number
   without re-checking; state is drifting fast in this repo.
2. Report the current backlog size and point at the single best existing
   candidate PR (check `mergeable_state: clean` + a full test plan in the
   body) instead of adding another one.
3. Spend the rest of the session on work that is genuinely **not yet
   represented** in any open PR — check `TODO.md`, `PLAN-NIGHTLY.md`,
   `REMAINING_ISSUES.md`, `NEXT_LARGE_PLAN.md`, `ROADMAP.md` for items
   with no corresponding open PR, or focus on bot *behavior* (win rate,
   build-order timing) rather than lint/test-infra, which is almost
   certainly already over-covered.

## Sanity check before claiming "tests are failing"

```bash
pip install -r requirements-dev.txt   # pytest-asyncio/-timeout/-mock, cffi
pip install burnysc2                  # may fail to build in some sandboxes
                                       # (mpyq wheel build error) — that is
                                       # an environment issue, not a repo bug
python3 -m pytest tests/ -q --ignore=tests/test_queen_transfusion.py
cd wicked_zerg_challenger && python3 -m pytest tests -q
```

`tests/` (excluding the one file that hard-requires the real `sc2`
package) was fully green as of 2026-07-19: **395 passed, 33 skipped**.
If your run shows different numbers, note the delta in your report —
don't assume prior reports (including this one) are still accurate
without checking. Missing `pytest-asyncio`/`cffi` in a fresh sandbox
produces false-negative failures ("async def functions are not natively
supported", `pyo3_runtime.PanicException` from `cryptography`) that look
like real bugs but are only a missing-dependency artifact — install
`requirements-dev.txt` before trusting any red run.

## Scheduling note

The recurring task prompt asks for a **daily** check-in. Observed PR
creation timestamps (e.g. 13 PRs within roughly one hour on 2026-07-18)
show this firing far more often than daily — that mismatch is very
likely what produced the 504-PR backlog. If you have visibility into the
schedule/trigger configuration that invokes this session, flag the
actual firing interval explicitly in your report; it's a scheduling
config problem, not a code problem, and no amount of in-session
discipline fixes it if the trigger itself fires hourly.
