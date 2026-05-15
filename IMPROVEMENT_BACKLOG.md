# SC2 Commander Bot — Improvement Backlog (Discovery from Testing)

Generated: 2026-05-15 — discovered by running the full pytest suite and inspecting failure causes.

## Test baseline

- Total collected: **606** (after env fixes)
- Pass (with `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python`): **604**
- Collection errors: **2** (`tests/test_blackboard.py`, `tests/test_sprint8_qa.py`)
- Raw failures without env workaround: **31** (all root-caused to one issue: optional sc2 import block swallows only `ImportError` and not `TypeError`).

## Priority 0 — Test infra unblocks

| # | Item | Symptom | Root cause |
|---|------|---------|------------|
| P0.1 | `tests/test_blackboard.py` collection fails | `cannot import name 'Blackboard'` | `Blackboard` alias missing in `blackboard.py`; test asserts `Blackboard is GameStateBlackboard` |
| P0.2 | `tests/test_sprint8_qa.py` collection fails | `No module named 'mpyq'` via `run_mass_test.py` → `sc2.main` | Hard import of `sc2.main` at module top; should be lazy/optional |
| P0.3 | 31 false failures without env override | `Point2 is None`, `UnitTypeId has no attribute X` | 55+ modules use `except ImportError:` only; protobuf incompat raises `TypeError`, which leaks through and sets all sc2 symbols to `None` |

## Priority 1 — Hardening optional sc2 imports (sweeping fix)

Files that use `except ImportError:` with `from sc2...` and need to also catch `TypeError`:

```
blackboard.py, adaptive_build.py, advanced_worker_optimizer.py, combat_phase_controller.py,
building_manager.py, creep_automation_v2.py, advanced_micro_controller_v3.py,
aggressive_strategies.py, creep_expansion_system.py, creep_manager.py, dynamic_counter_system.py,
early_defense_system.py, build_order_system.py, bot_step_integration.py, micro_controller.py,
multi_base_defense.py, economy_manager.py, combat_manager.py, creep_denial_system.py,
game_data_logger.py, composition_optimizer.py, harassment_extension.py, creep_highway_manager.py,
macro_cycle.py, early_scout_system.py, defense_coordinator.py, map_awareness.py,
opponent_modeling.py, overlord_vision_network.py, production_controller.py
... (55 total)
```

## Priority 2 — Engine/runtime robustness

| # | Item |
|---|------|
| P2.1 | `predict_enemy_position` returns `None` silently when `Point2` is None — should fall back to plain tuple or skip with logging |
| P2.2 | `RavagerMicro.find_best_bile_target` uses hard-coded `range_limit = 9`; should be data-driven (Ravager `bonus_range` from upgrade) |
| P2.3 | Cooldown durations are hard-coded across micros — centralize in a `ability_constants.py` |
| P2.4 | Multiple modules silently degrade when sc2 fails to import; we lose visibility — add one-time WARNING log in optional-import fallback |

## Priority 3 — Code quality / dead branches

| # | Item |
|---|------|
| P3.1 | `if not Point2:` is brittle; prefer explicit `if Point2 is None` |
| P3.2 | `import math` inside hot loops (e.g. `predict_enemy_position`) — hoist to module scope |
| P3.3 | Tests in `test_advanced_micro_v3.py` use `Mock(spec=[])` but rely on attribute assignment — fragile against mock policy changes |

## Execution plan (rolling cycles)

Each cycle = (1) run tests → (2) fix top issues → (3) commit → (4) push → repeat.

- Cycle 1: P0.1 + P0.3 (blackboard alias + sc2 import hardening, batch 1)
- Cycle 2: P0.3 batch 2 + P0.2 (lazy import of sc2.main)
- Cycle 3: P2.1 + P3.1 + P3.2 (predict_enemy_position robustness)
- Cycle 4: P2.4 (visibility logging for fallback imports)
- Cycle 5: Continued sweeps + code quality
