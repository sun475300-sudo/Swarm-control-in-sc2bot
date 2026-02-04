# Future Improvements Roadmap

This document outlines a comprehensive list of potential improvements for the Wicked Zerg Challenger project, categorized by impact and type.

## 1. Reliability & Robustness (High Priority)
*   **Standardize Error Handling**: Continue Phase 3 work.
    *   [ ] **Combat Manager**: Replace `print` debugs and silent `except: pass` blocks with `logger`.
    *   [ ] **Rogue Tactics Manager**: Unmask hidden errors in drop logic.
    *   [ ] **Intel Manager**: Ensure threat detection failures are logged.
*   **Async/Sync consistency**: Review `bot.do()` usages. Some are awaited, some are not. Standardize on `self.bot.do_actions()` or ensure consistent `await` usage where applicable.

## 2. Architecture & Maintainability
*   **Configuration Management**:
    *   [ ] **Extract Constants**: Move magic numbers (upgrade weights, unit ratios, timings) from code to a dedicated `config.py` or `constants.py`.
    *   [ ] **Dynamic Config**: Allow loading strategy parameters from a JSON/YAML file for easier tweaking without code changes.
*   **Type Hinting**:
    *   [ ] **Strict Typing**: Add `mypy` strict mode support. Many method signatures lack full type annotations.
*   **Event-Driven Communication**:
    *   [ ] **Decoupling**: Currently `BotStepIntegrator` manually calls every manager. Consider an Event Bus pattern (e.g., `on_enemy_detected`, `on_unit_created`) to decouple managers.

## 3. Testing & Quality Assurance
*   **Unit Tests**:
    *   [ ] **Test Suite**: Create a `tests/` directory with `pytest`.
    *   [ ] **Mock Bot**: Improve `fake_bot` to allow testing managers in isolation without launching SC2.
*   **CI/CD Hooks**:
    *   [ ] **Pre-commit hooks**: Setup `black` (formatter) and `ruff` (linter) to enforce style automatically.

## 4. Feature Enhancements
*   **Advanced Combat**:
    *   [ ] **Unit Micro**: Add specialized micro for Vipers (Abduct/Consume) and Infestors (Fungal Growth).
    *   [ ] **Flanking**: Implement logic to attack from multiple angles simultaneously.
*   **Machine Learning Integration**:
    *   [ ] **Training Pipeline**: Fully integrate `local_training` modules. Currently they exist but integration paths are unclear.
    *   [ ] **Model Serving**: Create a clean interface to load trained RL models for strategy selection.

## 5. Performance
*   **Profiling**:
    *   [ ] **Performance Monitor**: Add a decorator to measure execution time of each manager's `on_step`. Log warnings if any manager takes >10ms.
*   **Optimization**:
    *   [ ] **Caching**: Use `functools.lru_cache` for expensive geometry calculations (e.g., expansion distances).

## 6. Documentation
*   **Wiki/Guide**: Create a `DEVELOPER.md` guide explaining the manager architecture for new contributors.
*   **Docstrings**: Ensure all public methods have Google-style docstrings.

## 7. Specialize & Optimize (미세 컨트롤 최적화)
*   **Queen Specialization (여왕 역할 분담)**:
    *   [ ] **Inject Queen**: Dedicate queens with reserved energy exclusively for larvae injection
        *   Energy management: Save 25+ energy for inject cycles
        *   Position lock: Stay within inject range of assigned hatchery
        *   Priority override: Never use for creep/defense unless emergency
    *   [ ] **Creep Queen**: Assign queens to advance with main army for frontline creep spread
        *   Travel with army: Position queens behind main force
        *   Aggressive tumors: Plant creep along attack paths, not just expansions
        *   Safety checks: Retreat when HP < 50% or enemy air nearby
*   **Creep Highway (점막 고속도로)**:
    *   [ ] **Priority Pathing**: Instead of uniform creep spread, prioritize shortest path connections
        *   Main Base ↔ Natural ↔ Third Base (highway connections)
        *   Base ↔ Attack Target (offensive creep lanes)
        *   A* pathfinding for optimal tumor placement sequence
    *   [ ] **Dynamic Rerouting**: Adjust creep highways based on:
        *   Enemy position changes (avoid contested areas)
        *   New expansion timings
        *   Retreat paths during defensive situations
*   **Overlord Pillars (대군주 안전지대)**:
    *   [ ] **Pillar Detection System**:
        *   Hardcode known pillar positions for common ladder maps (Altitude, etc.)
        *   Runtime calculation: Detect high ground + unpathable terrain combinations
        *   Safety scoring: Distance from enemy base + air threat assessment
    *   [ ] **Strategic Positioning**:
        *   Station overlords on pillars for permanent vision
        *   Auto-replace: Send new overlord if pillar overlord dies
        *   Map coverage: Ensure 3-4 pillars cover key chokepoints and attack paths

## 8. Deep Economy (초미세 경제 최적화)
*   **Gold Base Priority (황금 기지 우선 활용)**:
    *   [ ] **Auto-Detection**: Identify gold mineral bases at game start
        *   Check for 1200+ mineral patches (gold minerals have 1500, normal 1800)
        *   Mark gold base locations in expansion planner
    *   [ ] **Instant Saturation**: When gold base secured:
        *   Transfer 16 drones immediately from main/natural
        *   Maintain perfect saturation (2 drones per mineral patch)
        *   Resource boost tracking: Log gold base income efficiency
*   **Distance Mining (거리 기반 채굴 최적화)**:
    *   [ ] **Micro-Optimization**: Assign drones to closest available mineral patch
        *   Calculate exact distance from hatchery to each mineral
        *   Rebalance assignments every 30 seconds
        *   Prevent "long walk" inefficiency (drones walking to far minerals)
    *   [ ] **Dynamic Rebalancing**:
        *   Detect mineral depletion (patches with <100 minerals)
        *   Reassign drones from depleted patches to closest alternatives
        *   Gas timing: Move closest drones to extractors when gas needed
