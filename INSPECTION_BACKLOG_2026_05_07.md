# SC2 Bot — Inspection Backlog (2026-05-07)

> Branch: `claude/stoic-shannon-SoFae`
> Driven by iterative test/inspect/improve cycles requested by the user.
> Source: `pytest tests/` + grep audit of `wicked_zerg_challenger/`.

---

## Test baseline (after S0 fixes in this branch)

```
372 passed, 35 skipped, 0 failed
```

S0 fixes already committed in this cycle:
- `tests/test_queen_transfusion.py` — guarded `from sc2.ids.unit_typeid import UnitTypeId` with try/except so collection no longer aborts in environments without `python-sc2`.
- `integration_hub.py` — three real bugs fixed (see Cycle 1 below).

35 skips are environmental (numpy/torch/sc2/yaml not installed) or conditional on missing `config.yaml` — not blocking.

---

## Cycle 1 — Bug fixes (DONE in this commit)

| File | Issue | Fix |
|---|---|---|
| `tests/test_queen_transfusion.py:11` | Hard `from sc2 import ...` aborts pytest collection on machines without `python-sc2`. Sister tests already guard. | Added `try/except ImportError → pytest.skip(allow_module_level=True)`. |
| `integration_hub.py:52` | `self.project_root = project_root or Path(__file__).parent.parent` resolved one level too high. Result: `_check_go_server`, `_check_cpp`, `_check_kotlin`, `_check_android` always returned **False** because they look one directory above the repo. | Changed to `Path(__file__).parent`. Verified: `go=True, cpp=True, android=True` now. |
| `integration_hub.py:211` (generated test script body) | `str(__file__).parent.parent` — string has no `.parent` attribute → would `AttributeError` on first run. | Wrapped in `Path(...)`. |
| `integration_hub.py:244` | `hub = IntegrationHub()` runs at **import time**, doing filesystem checks and triggering rust accel side effects on every import. Made unit testing impossible. | Moved instantiation under `if __name__ == "__main__":` block. |

---

## Cycle 2 — Exception-handling tightening (NEXT)

| File | Line | Severity | Action |
|---|---|---|---|
| `wicked_zerg_challenger/queen_manager.py` | 195, 302, 357, 381, 513, 536, 707, 796, 835, 860, 892, 950, 1007, 1099, 1150, 1164, 1203, 1221, 1235, 1265 | MED | 20 occurrences of `except Exception as e:` — narrow at least the easy ones (AttributeError / KeyError / ValueError) so real bugs surface instead of being swallowed. |
| `wicked_zerg_challenger/queen_manager.py:892` | LOW | Bare `except Exception:` (no binding) — should at minimum log the error before swallowing. |
| `wicked_zerg_challenger/combat_manager.py` | 379, 415, 455, 487, 509 | LOW | Empty `except` blocks for ImportError fallbacks — add a one-line module-level logger.debug so silent failures aren't invisible. |
| `wicked_zerg_challenger/economy_manager.py:719` | LOW | Bare `pass` — document intent (`# noqa: silent fallback when ...`). |
| `wicked_zerg_challenger/combat_manager.py:224` | LOW | Commented-out `# return` — delete or convert to inline note about why it's disabled. |

---

## Cycle 3 — Magic-number extraction

`combat_manager.py` (4335 lines) has lots of inline literals; extracting these reduces re-tuning friction:

| Constant family | Sample lines | Suggested name |
|---|---|---|
| Frame-skip interval `22` | 169, 184 | `COMBAT_CHECK_INTERVAL_FRAMES = 22` |
| Logging cadence `50` frames | 260, 374, 450, ... | `LOG_INTERVAL_FRAMES = 50` |
| Game-time phase thresholds (60s, 180s, 270s, 300s, 420s, 480s, 600s, 900s) | 390, 434, 459, ... | `class CombatPhaseTimings` (Enum) |
| Unit-count comp thresholds (6, 12, 4, 24, 5, 40) | 400, 481, 499 | `class UnitCompositionThresholds` |

`economy_manager.py` (3616 lines):

| Constant family | Lines | Suggested name |
|---|---|---|
| Resource thresholds (550, 600, 800, 1200) | 69, 73, 87, 98–103 | `class EconomyConfig` |
| Race-keyed gas timing (Z=90, T=75, P=105) | 98–103 | `RACE_GAS_TIMING = {Race.Z: 90, ...}` |

`queen_manager.py`:
- Time checks `30s`, `60s`; resource thresholds `150` minerals; distance bands `30`, `12`, `25` (lines 237, 292, 303, 400, ...).

---

## Cycle 4 — Long-function refactors (high-risk, plan only for now)

These are flagged but do **not** apply yet — they are large and a refactor cycle should be its own PR. Listed here so cycles can pick them up when the test net is denser.

| File:line | Function | Lines | Action |
|---|---|---|---|
| `economy_manager.py:298` | `_should_delay_opening_expansion` | **1108** | Split into supply / creep / gas / opponent-pressure sub-checks. |
| `economy_manager.py:1406` | `_get_first_larva` | 879 | Separate priority scoring, hatchery selection, fallback. |
| `combat_manager.py:110` | `reset` | 912 | Group state init / task assign / execution. |
| `combat_manager.py:1404` | `_find_weakest_enemy` | 345 | Extract per-unit-type prioritization. |
| `combat_manager.py:3220` | `_get_enemy_base_location` | 389 | Extract base detection + caching. |
| `queen_manager.py:540` | `_is_base_under_attack` | 563 | Split threat detection / range checks / unit filtering. |
| `queen_manager.py:307` | `_assign_queen_roles` | 233 | Pull each role-assignment branch out. |
| `queen_manager.py:71` | `__init__` | 236 | Move config loading + module wiring to helpers. |

---

## Cycle 5 — Test-net densification

Before doing risky refactors, add tests around the hot paths so regressions surface:

- Add `tests/test_integration_hub.py` covering `get_status`, `combat_analysis`, `_python_formation` (line/circle), and `run_benchmark` shape.
- Add unit tests for the magic-number constants once extracted (so accidental changes break tests).
- Tag the existing `pytest.skip(...)` markers with categories: `requires_numpy`, `requires_torch`, `requires_sc2`, so CI can filter.

---

## Cycle 6+ — Carry-over from prior MASTER_TODO_SC2.md

Still open from prior cycles:
- `integration_hub.py` audit (cycle 1 picked up 3 bugs — more remain — partial done)
- mypy strict-equality rollout per module
- `detect-secrets` results review
- Path-dependency / config-loader consistency audit

---

## Summary table — fix priority

| Priority | Cycle | Issue | Status |
|---|---|---|---|
| P0 | 1 | `integration_hub` `project_root` off-by-one | DONE |
| P0 | 1 | `test_queen_transfusion` import guard | DONE |
| P1 | 2 | queen_manager broad-exception narrowing | NEXT |
| P1 | 2 | combat_manager silent ImportError handlers | NEXT |
| P2 | 3 | combat_manager magic-number extraction | LATER |
| P2 | 3 | economy_manager magic-number extraction | LATER |
| P3 | 4 | long-function refactors (`_should_delay_opening_expansion` etc.) | PLAN |
| P3 | 5 | test-net densification | PLAN |
