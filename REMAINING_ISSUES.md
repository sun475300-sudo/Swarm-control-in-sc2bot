# Remaining Issues & Priority Backlog

**Last refreshed:** 2026-07-03 (continuous test-and-inspect cycle, PR #239)

This file previously listed issues from 2026-01/2026-04 that have since
been verified as already resolved in the codebase (duplicate `on_step`/
`_prevent_resource_banking`/`_find_harass_target`/`build_terran_counters`
definitions, queen inject cooldown, missing upgrades, transfusion
priority, resource-reservation locking, `position_utils.py`,
`distance_cache.py`, `game_constants.py`). They are dropped from this
file; check `git log` around 2026-04-27 through 2026-06-01 if you need
the history.

---

## Resolved this cycle (2026-07-03, PR #239)

| Item | Fix |
|------|-----|
| CI red on every push/schedule since 2026-05-28 | black+isort drift (70 files) reformatted |
| `sc2bot-ci.yml` Test Suite job dead | fixed `pytest tests/unit` → `pytest tests/` (that path never existed) |
| 14 test files failing to collect | `TypeError: Descriptors cannot be created directly` (protobuf 5.x vs s2clientprotocol) — added `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` to the 2 jobs missing it |
| Integration test step failing immediately | `pytest-timeout` wasn't installed before `--timeout=120` was used |
| 12 failing tests in `test_combat_phase_fsm.py` | deprecated `asyncio.get_event_loop().run_until_complete()` → `asyncio.run()` |
| PLAN-NIGHTLY P2.4 (RL save-experience guard) | `save_experience_data()` used remove-then-rename (data-loss window on crash/failed rename) → `os.replace()` (atomic); 7 new tests |

Result: **476 pass / 12 skip / 0 fail**, full CI green (23/23 checks) for
the first time in ~5 weeks.

---

## Open backlog, priority order

### P1 — worth doing next

1. **PLAN-NIGHTLY P2.2 — Benchmark runner.** No implementation exists yet
   (`wicked_zerg_challenger/run_mass_test.py` runs real games against the
   SC2 client, which this sandbox can't execute — needs a machine with
   StarCraft II installed). Scope: one command that plays N replays/games
   and reports APM, supply, win-rate vs. a baseline (e.g. Hard AI).
2. **PLAN-NIGHTLY P2.3 — Build-order config externalisation.** Top ~20
   hardcoded build-order values in `economy_manager.py` /
   `build_order_system.py` should move to `config/build_orders.yaml`
   (file doesn't exist yet). Moderate effort, no blockers.
3. **Arena packaging is untested on PRs.** `ci.yml`'s `arena-package` job
   only runs on non-PR events (`if: github.event_name != 'pull_request'`),
   so `create_arena_package.py` and `phase50_integrated_validation.py`
   haven't been exercised by this cycle's fixes. Worth a manual
   `python create_arena_package.py --output-dir /tmp/arena --no-open`
   smoke test next session to confirm they still work end to end.
4. **134 flake8 F841/F401 findings** in `wicked_zerg_challenger/` (unused
   locals/imports) — low risk, mechanical cleanup, good candidate for a
   dedicated small PR so a real regression isn't hidden in a big diff.

### P2 — lower priority / needs a real SC2 client to validate

5. **PLAN-NIGHTLY P2.5 — type hints/docstrings on core modules.** Spot
   check found `core/manager_factory.py` and `core/resource_manager.py`
   already reasonably typed/documented; re-audit before assuming this is
   still open.
6. **~468 bare `except Exception:` blocks** repo-wide. Don't do a mass
   sweep — pick the ones in hot paths (combat_manager, economy_manager)
   that could be silently swallowing real bugs, one at a time, backed by
   a test that shows the swallowed error would otherwise surface.
7. **Sprint 8 QA (ROADMAP.md) — Medium AI win-rate testing.** Requires an
   actual StarCraft II binary + maps; not runnable in this sandbox.
   Depends on P2.2 (benchmark runner) to be worth doing in an automated
   way.

### Documentation hygiene (not urgent)

- `ROADMAP.md`, `NEXT_PHASE_PLAN.md`, `TODO.md` describe several Sprints
  as not-yet-done that are actually implemented already (RL micro
  toggle, distance cache, game constants, building_manager, resource
  locking, etc). Worth a pass to mark them done so future sessions don't
  re-investigate the same ground — flagging here rather than doing it
  now to keep this cycle's diff focused on code/tests.
