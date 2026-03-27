# Enhanced Scouting System Implementation Plan

## Goal
Significantly improve the bot's map awareness and adaptability by enhancing the `ActiveScoutingSystem`. Transition from simple periodic Zergling runs to a multi-unit, dynamic scouting engine that feeds real-time intelligence to the `StrategyManager`.

## User Review Required
> [!NOTE]
> This change will increase APM usage slightly due to more frequent micro-management of scout units.
> Also, gas consumption may slightly increase due to Overseer morphing (50/50 cost).

## Proposed Changes

### 1. Active Scouting System Upgrade
**File**: `wicked_zerg_challenger/active_scouting_system.py`

#### [MODIFY] `active_scouting_system.py`
- **Dynamic Scouting Interval**:
    - Default: **25 seconds** (was 40s)
    - Alert Mode (Info Stale/Unknown): **15 seconds**
- **Multi-Unit Support**:
    - **Zerglings**: Ground speed scouting (cheap, fast).
    - **Overseers**: Air scouting + Detection (Changeling usage).
    - **Overlords** (with Speed Upgrade): Backup air scouting.
- **Smart Target Selection**:
    - Prioritize **unseen expansions** > **enemy main** > **watchtowers**.
    - Avoid sending scouts to recently cleared locations (unless verifying expansion).
- **Blackboard Integration**:
    - Push updates to `blackboard.enemy_info` immediately upon detection.

### 2. Intel Manager Refinement
**File**: `wicked_zerg_challenger/intel_manager.py`

#### [MODIFY] `intel_manager.py`
- **Build Pattern Confidence**:
    - Add confidence score to build pattern detection.
    - Differentiate between "Suspected" and "Confirmed" tech.
- **Counter Unit Recommendation**:
    - Refine `recommended_response` to provide strictly ranked counter units based on hard data.

## Verification Plan

### Automated Tests
- **Mock Unit Test**: Simulate an enemy base and verify `ActiveScoutingSystem` dispatches a scout within 30 seconds.
- **Data Integrity**: Verify Blackboard receives the correct "Enemy Race" and "Build Pattern" after a scout reaches the target.

### Manual Verification
- Watch the bot in a 1v1 vs AI.
- Confirm Overseers are morphed and sent to scout when Lair is ready.
- Check if the bot reacts to an enemy Spire by building Spores/Hydras (via Blackboard).
