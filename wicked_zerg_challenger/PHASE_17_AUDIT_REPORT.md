# Phase 17: Precision Audit Report
**Date**: 2026-02-05
**Focus**: Real-time Logic Reinforcement & Safety

## 🔴 Critical Issues (Immediate Action Required)

### 1. Spellcaster Automation Conflict
- **File**: `spellcaster_automation.py`
- **Issue**: This module issues commands directly to Queens, Ravagers, Vipers, and Infestors **without using `UnitAuthorityManager`**.
- **Impact**: `CombatManager` or `QueenManager` will fight for control of these units every frame, causing "jittering" (units moving back and forth between two orders) and failed skill casts.
- **Fix**: Integrate `UnitAuthorityManager.request_unit()` before casting spells.

### 2. Smart Surrender Logic Incomplete
- **File**: `strategy_manager_v2.py`
- **Issue**: The `_check_smart_surrender` method is mentioned in comments and `__init__`, but the call in `update()` is commented out, and the implementation logic seems missing or disconnected.
- **Impact**: The bot continues hopeless games, wasting training time.

### 3. Combat Manager & Squad Locking
- **File**: `combat_manager.py` (and `harassment_coordinator.py`)
- **Issue**: While `HarassmentCoordinator` has "squad" concepts, `CombatManager` needs to explicitly **exclude** units that are locked by other high-priority systems (like Harassment or Creep Denial) from its general army selection.
- **Verification Needed**: Confirm `CombatManager` filters out units with `unit_authority.get_params(tag).owner != "CombatManager"`.

## 🟡 Improvement Areas

### 1. Creep Denial Safety
- **File**: `creep_denial_system.py`
- **Observation**: Logic is good, but `_is_dangerous_position` relies on simple distance checks.
- **Improvement**: Integrate with `CombatManager`'s threat map or `DefenseCoordinator`'s danger zones for more accurate safety assessment.

### 2. Strategy Manager Scoring
- **File**: `strategy_manager_v2.py`
- **Observation**: `_calculate_kill_death_score` assumes `blackboard` availability.
- **Improvement**: Add robust fallback if metrics are missing to prevent strategy oscillation.

## 📋 Implementation Plan (Phase 17)

1.  **Refactor `spellcaster_automation.py`**:
    *   Inject `UnitAuthorityManager`.
    *   Request `TACTICAL` authority before casting.
    *   Release authority after cast (or hold for channel).

2.  **Enable Smart Surrender**:
    *   Uncomment and verify `_check_smart_surrender` in `strategy_manager_v2.py`.
    *   Ensure it triggers `self.bot.leave_game()` securely.

3.  **Reinforce Squad Locking**:
    *   Modify `CombatManager.py` to strictly respect `UnitAuthority`.
    *   Add "Squad Lock" visual debug text (optional).

4.  **Resource Safety**:
    *   Add `safeguard_resources()` check in `EconomyManager`.
