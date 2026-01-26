# WiekdZergBot Logic Improvement Tasks

- [x] Analyze existing "improved" modules (`advanced_building_manager`, `aggressive_tech_builder`, `production_resilience`) <!-- id: 0 -->
- [x] Consolidate Defense Logic (Priority 1) <!-- id: 1 -->
    - [x] Create `DefenseCoordinator` class
    - [x] Migrate `EarlyDefenseSystem` logic
    - [x] Migrate `MultiBaseDefense` logic
    - [x] Migrate `EmergencyMode` logic
- [x] Commander Learning System (Phase 2) <!-- id: 2 -->
    - [x] Design `commander_knowledge.json` structure
    - [x] Create `KnowledgeManager` component
    - [x] Extract hardcoded builds to JSON
    - [x] Refactor `BuildOrderSystem` to use `KnowledgeManager`
- [ ] Centralize State (Phase 3) <!-- id: 3 -->
    - [ ] Create `Blackboard` / `GameState` class
    - [ ] Refactor managers to read/write to Blackboard
- [x] Fix Blackboard attribute errors <!-- id: 4 -->
- [x] Fix Units API compatibility issues <!-- id: 5 -->
