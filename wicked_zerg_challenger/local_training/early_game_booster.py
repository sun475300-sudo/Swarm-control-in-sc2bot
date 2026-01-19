# -*- coding: utf-8 -*-
"""
Early Game Build Order Booster

Strengthens early game build order to reduce defeats within 3 minutes.
Focuses on:
1. Maximum drone production priority
2. Improved supply management (Overlord timing)
3. Early building construction accuracy
4. Resource gathering priority
"""

from typing import Any, Optional
from enum import Enum, auto

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    class UnitTypeId:
        DRONE = "DRONE"
        OVERLORD = "OVERLORD"
        SPAWNINGPOOL = "SPAWNINGPOOL"
        EXTRACTOR = "EXTRACTOR"
        HATCHERY = "HATCHERY"
        LARVA = "LARVA"
        ZERGLING = "ZERGLING"
        QUEEN = "QUEEN"

try:
    from config import get_learned_parameter
except ImportError:
    def get_learned_parameter(parameter_name: str, default_value: Any = None) -> Any:
        return default_value


class EarlyGamePhase(Enum):
    """Early game phases (first 3 minutes)"""
    INITIAL = auto()  # 0-60s: Initial drone production
    BUILDING = auto()  # 60-120s: Key buildings (Pool, Gas)
    EXPANSION = auto()  # 120-180s: Natural expansion preparation


class EarlyGameBooster:
    """
    Early game build order booster to prevent 3-minute defeats
    """
    
    def __init__(self, bot: Any) -> None:
        self.bot = bot
        self.phase = EarlyGamePhase.INITIAL
        
        # Early game targets
        self.target_drones_by_60s = 16  # Target: 16 drones by 1 minute
        self.target_drones_by_120s = 24  # Target: 24 drones by 2 minutes
        self.target_drones_by_180s = 30  # Target: 30 drones by 3 minutes
        
        # Supply management
        self.overlord_supply_threshold = 3  # Build Overlord when supply_left < 3
        self.overlord_early_threshold = 13  # Build first Overlord at supply 13
        
        # Building timing
        self.pool_supply_target = get_learned_parameter("spawning_pool_supply", 17.0)
        self.gas_supply_target = get_learned_parameter("gas_supply", 17.0)
        
    def get_current_phase(self) -> EarlyGamePhase:
        """Determine current early game phase"""
        time = getattr(self.bot, "time", 0.0)
        if time < 60:
            return EarlyGamePhase.INITIAL
        elif time < 120:
            return EarlyGamePhase.BUILDING
        else:
            return EarlyGamePhase.EXPANSION
    
    async def boost_early_game(self) -> None:
        """
        Main early game booster function
        Called every step during first 3 minutes
        """
        b = self.bot
        time = getattr(b, "time", 0.0)
        
        # Only active during first 3 minutes
        if time > 180:
            return
        
        self.phase = self.get_current_phase()
        
        # Priority 1: Supply management (CRITICAL - prevents supply block)
        await self._ensure_supply()
        
        # Priority 2: Drone production (MAXIMUM PRIORITY)
        await self._maximize_drone_production()
        
        # Priority 3: Key buildings (Pool, Gas)
        await self._build_key_structures()
        
        # Priority 4: Resource gathering optimization
        await self._optimize_resource_gathering()
    
    async def _ensure_supply(self) -> None:
        """
        Ensure supply is available - prevents supply block
        This is CRITICAL for early game success
        """
        b = self.bot
        supply_used = getattr(b, "supply_used", 0)
        supply_left = getattr(b, "supply_left", 0)
        supply_cap = getattr(b, "supply_cap", 200)
        
        # Early game: Build first Overlord at supply 13
        if supply_used >= self.overlord_early_threshold and supply_used < 15:
            overlords = b.units(UnitTypeId.OVERLORD)
            if overlords.amount <= 1:  # Only 1 starting Overlord
                larvae = b.units(UnitTypeId.LARVA).ready
                if larvae.exists and b.can_afford(UnitTypeId.OVERLORD):
                    larva = larvae.first
                    try:
                        if hasattr(larva, 'train'):
                            result = larva.train(UnitTypeId.OVERLORD)
                            if hasattr(result, '__await__'):
                                await result
                        if b.iteration % 50 == 0:
                            print(f"[EARLY BOOST] [{int(b.time)}s] Building first Overlord at supply {supply_used}")
                    except Exception:
                        pass
        
        # Standard: Build Overlord when supply_left < threshold
        if supply_left < self.overlord_supply_threshold and supply_cap < 200:
            larvae = b.units(UnitTypeId.LARVA).ready
            if larvae.exists and b.can_afford(UnitTypeId.OVERLORD):
                if b.already_pending(UnitTypeId.OVERLORD) == 0:
                    larva = larvae.first
                    try:
                        if hasattr(larva, 'train'):
                            result = larva.train(UnitTypeId.OVERLORD)
                            if hasattr(result, '__await__'):
                                await result
                        if b.iteration % 50 == 0:
                            print(f"[EARLY BOOST] [{int(b.time)}s] Building Overlord (supply_left: {supply_left})")
                    except Exception:
                        pass
    
    async def _maximize_drone_production(self) -> None:
        """
        Maximize drone production in early game
        This is the highest priority during first 3 minutes
        """
        b = self.bot
        time = getattr(b, "time", 0.0)
        supply_used = getattr(b, "supply_used", 0)
        
        # Count current drones
        drones = b.units(UnitTypeId.DRONE)
        drone_count = drones.amount if hasattr(drones, 'amount') else len(list(drones))
        
        # Check if we need more drones
        target_drones = self._get_target_drone_count(time)
        if drone_count >= target_drones:
            return  # Already have enough drones
        
        # Get available larvae
        larvae = b.units(UnitTypeId.LARVA).ready
        if not larvae.exists:
            return
        
        # Check supply
        supply_left = getattr(b, "supply_left", 0)
        if supply_left < 1:
            # Need Overlord first
            return
        
        # Produce drones from ALL available larvae
        larvae_list = list(larvae)
        drones_produced = 0
        
        for larva in larvae_list:
            if not hasattr(larva, 'is_ready') or not larva.is_ready:
                continue
            
            # Check supply again
            supply_left = getattr(b, "supply_left", 0)
            if supply_left < 1:
                break
            
            # Check if we can afford drone
            if not b.can_afford(UnitTypeId.DRONE):
                break
            
            # Produce drone
            try:
                if hasattr(larva, 'train'):
                    result = larva.train(UnitTypeId.DRONE)
                    if hasattr(result, '__await__'):
                        await result
                    drones_produced += 1
                    
                    if drones_produced == 1 and b.iteration % 50 == 0:
                        print(f"[EARLY BOOST] [{int(b.time)}s] Producing drones (target: {target_drones}, current: {drone_count})")
            except Exception:
                pass
        
        if drones_produced > 0 and b.iteration % 50 == 0:
            print(f"[EARLY BOOST] [{int(b.time)}s] Produced {drones_produced} drones (total: {drone_count + drones_produced})")
    
    def _get_target_drone_count(self, time: float) -> int:
        """Get target drone count based on game time"""
        if time < 60:
            return self.target_drones_by_60s
        elif time < 120:
            return self.target_drones_by_120s
        elif time < 180:
            return self.target_drones_by_180s
        else:
            return 30  # Default after 3 minutes
    
    async def _build_key_structures(self) -> None:
        """
        Build key structures (Spawning Pool, Gas) at optimal timing
        """
        b = self.bot
        supply_used = getattr(b, "supply_used", 0)
        time = getattr(b, "time", 0.0)
        
        # Spawning Pool: Build at target supply
        if not b.units(UnitTypeId.SPAWNINGPOOL).exists and b.already_pending(UnitTypeId.SPAWNINGPOOL) == 0:
            if supply_used >= self.pool_supply_target:
                if b.can_afford(UnitTypeId.SPAWNINGPOOL) and b.townhalls.exists:
                    try:
                        main_base = b.townhalls.first
                        await b.build(
                            UnitTypeId.SPAWNINGPOOL,
                            near=main_base.position.towards(b.game_info.map_center, 5)
                        )
                        if b.iteration % 50 == 0:
                            print(f"[EARLY BOOST] [{int(b.time)}s] Building Spawning Pool at supply {supply_used}")
                    except Exception:
                        pass
        
        # Gas Extractor: Build at target supply
        if not b.structures(UnitTypeId.EXTRACTOR).exists and b.already_pending(UnitTypeId.EXTRACTOR) == 0:
            if supply_used >= self.gas_supply_target:
                if b.can_afford(UnitTypeId.EXTRACTOR):
                    geysers = b.vespene_geyser if hasattr(b, "vespene_geyser") else []
                    if geysers:
                        target = geysers.first if hasattr(geysers, "first") else list(geysers)[0]
                        try:
                            await b.build(UnitTypeId.EXTRACTOR, target)
                            if b.iteration % 50 == 0:
                                print(f"[EARLY BOOST] [{int(b.time)}s] Building Gas Extractor at supply {supply_used}")
                        except Exception:
                            pass
    
    async def _optimize_resource_gathering(self) -> None:
        """
        Optimize resource gathering in early game
        Ensure all drones are gathering resources
        """
        b = self.bot
        drones = b.units(UnitTypeId.DRONE)
        
        if not drones.exists:
            return
        
        # Count idle drones
        idle_drones = [drone for drone in drones if drone.is_idle]
        
        if idle_drones and b.townhalls.exists:
            main_base = b.townhalls.first
            minerals = b.mineral_field.closer_than(10, main_base.position)
            
            if minerals.exists:
                for drone in idle_drones[:5]:  # Process up to 5 at a time
                    try:
                        mineral = minerals.closest_to(drone.position)
                        await b.do(drone.gather(mineral))
                    except Exception:
                        pass
