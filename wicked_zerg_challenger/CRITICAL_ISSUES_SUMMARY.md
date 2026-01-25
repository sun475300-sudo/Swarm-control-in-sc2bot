# Critical Issues Summary

Date: 2026-01-25

## Problem Analysis

### Root Cause: Workers Dying
```
[ECONOMY RECOVERY] [180s] Current: 14 workers
[ECONOMY RECOVERY] [440s] Current: 8 workers  (dropped from 29!)
```

**Workers are dying massively** - this is the #1 problem causing economic collapse.

### Secondary Issue: Multiple Expansion Logic Conflicts

The economy_manager.py has **4 different expansion systems** all running:
1. `_manage_expansion()` - main expansion logic
2. `_trigger_expansion_for_growth()` - expands when workers saturated
3. `_predict_and_expand()` - expands when minerals depleting
4. `_prevent_resource_banking()` - expands when minerals > 1000

All run every iteration and can interfere with each other.

### Evidence from Logs

```
[EXPANSION] [359s] Trying to expand: ULTRA-FAST Natural @359s (min 200, workers: 29)
[EXPANSION] [359s] Cannot afford Hatchery (need 300 minerals)
[PROACTIVE EXPAND] [365s] ULTRA-FAST Natural @365s (min 200, workers: 29) - SUCCESS
[FORCE EXPAND] 10sec INSTANT EXPAND - FORCING EXPANSION NOW!
[ECONOMY] DESPERATE EXPANSION: Force expanding! (No natural @ 365s)
```

Four different messages for the same expansion attempt!

## Fixes Applied So Far

### 1. Worker Production Priority (economy_manager.py:235-255)
- Removed 12-worker emergency cap
- Calculate minimum workers: `base_count * 16`
- Force worker production when below minimum (bypass balancer)

### 2. Critical Expansion Timing (economy_manager.py:1102-1111)
- Changed from 240s (4 min) to 120s (2 min)
- Lowered mineral requirement from 300 to 150
- Simplified afford check: `minerals >= 150` instead of `can_afford()`

### 3. Bug Fixes
- Fixed PerformanceOptimizer.on_end() crash (wicked_zerg_bot_pro_impl.py:356)
- Cleared Python bytecode cache (.pyc files)

## Next Steps Required

### Priority 1: Fix Worker Deaths
**Investigate why workers are dying:**
- Building placement bugs (workers getting stuck/trapped)?
- Combat sending workers to die?
- Banelings/splash damage?
- Check logs for "[WORKER]" or "[BASE DEFENSE]" messages

**Possible Solutions:**
- Add worker safety checks before building placement
- Prevent workers from being added to combat groups
- Add worker retreat logic when under attack

### Priority 2: Simplify Expansion Logic
**Current state:** 4 different expansion systems = conflicts

**Proposed consolidation:**
```python
async def _manage_expansion(self) -> None:
    """Single unified expansion logic"""
    game_time = self.bot.time
    townhalls = self.bot.townhalls.ready
    workers = self.bot.workers.amount
    minerals = self.bot.minerals

    # Rule 1: Natural expansion (highest priority)
    if townhalls.amount < 2 and game_time > 120 and minerals >= 200:
        await self._expand_now()
        return

    # Rule 2: Saturated workers need new base
    if workers >= townhalls.amount * 20:
        if minerals >= 300:
            await self._expand_now()
            return

    # Rule 3: Banking minerals
    if minerals > 1000 and townhalls.amount < 6:
        await self._expand_now()
        return
```

Disable/remove:
- `_trigger_expansion_for_growth()`
- `_predict_and_expand()`
- `_prevent_resource_banking()` expansion part

Keep only ONE expansion method.

### Priority 3: Add Worker Protection
```python
async def _protect_workers_from_buildings(self) -> None:
    """Ensure workers don't get stuck in buildings"""
    for worker in self.bot.workers.idle:
        # Check if worker is surrounded by buildings
        buildings_near = self.bot.structures.closer_than(2, worker)
        if len(buildings_near) >= 3:
            # Worker is trapped! Move to minerals
            nearest_mineral = self.bot.mineral_field.closest_to(worker)
            self.bot.do(worker.gather(nearest_mineral))
```

## Expected Results After Fixes

1. Workers production prioritized → economy stable
2. Single expansion logic → no conflicts
3. Worker protection → no deaths from building placement
4. Natural expansion by 2 minutes → competitive economy
5. Stable 16+ workers per base → good mineral income

## Testing Plan

1. Run 1 game with logging enabled
2. Watch worker count - should stay >= 16 per base
3. Check expansion timing - natural by 2-3 minutes
4. Monitor for "[EXPANSION]" spam - should only see 1 line per attempt
5. Check game result - should last longer, better economy

## Current Status

- ✅ Worker production priority fixed
- ✅ Critical expansion timing improved
- ✅ Python cache cleared
- ✅ PerformanceOptimizer crash fixed
- ❌ Worker deaths not fixed yet
- ❌ Multiple expansion logic not consolidated yet
- ❌ Worker protection not added yet
