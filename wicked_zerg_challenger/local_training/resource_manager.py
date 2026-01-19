# -*- coding: utf-8 -*-
"""
Enhanced Resource Manager

Manages worker (drone) assignment to minerals and gas, optimizes resource gathering,
and prevents resource waste by ensuring efficient distribution.
"""

from typing import Any, List, Dict, Optional, Tuple
from dataclasses import dataclass

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
except ImportError:
    class UnitTypeId:
        DRONE = "DRONE"
        EXTRACTOR = "EXTRACTOR"
        HATCHERY = "HATCHERY"
        LAIR = "LAIR"
        HIVE = "HIVE"
    Point2 = Any

try:
    from config import Config
    WORKERS_PER_BASE = getattr(Config, 'WORKERS_PER_BASE', 16)
    WORKERS_PER_GAS = getattr(Config, 'WORKERS_PER_GAS', 3)
    MAX_WORKERS = getattr(Config, 'MAX_WORKERS', 60)
except (ImportError, AttributeError):
    WORKERS_PER_BASE = 16
    WORKERS_PER_GAS = 3
    MAX_WORKERS = 60


@dataclass
class BaseResourceInfo:
    """Resource information for a base"""
    base: Any
    mineral_workers: int
    gas_workers: int
    total_workers: int
    target_mineral_workers: int
    target_gas_workers: int
    minerals_nearby: int
    extractors: List[Any]


class ResourceManager:
    """
    Enhanced resource management system
    
    Features:
    - Optimal worker distribution (minerals vs gas)
    - Base-by-base worker assignment
    - Idle worker management
    - Resource gathering efficiency optimization
    - Waste prevention (excess resource accumulation)
    """
    
    def __init__(self, bot: Any):
        self.bot = bot
        self.last_optimization_time = 0.0
        self.optimization_interval = 2.0  # Optimize every 2 seconds
        self.base_assignments: Dict[int, BaseResourceInfo] = {}
        
    async def optimize_resource_gathering(self) -> None:
        """
        Main optimization method - called regularly to manage resources
        """
        current_time = getattr(self.bot, "time", 0.0)
        
        # Only optimize every optimization_interval seconds
        if current_time - self.last_optimization_time < self.optimization_interval:
            return
        
        self.last_optimization_time = current_time
        
        try:
            # Step 1: Handle idle workers
            await self._handle_idle_workers()
            
            # Step 2: Optimize worker distribution per base
            await self._optimize_base_worker_distribution()
            
            # Step 3: Balance workers across bases
            await self._balance_workers_across_bases()
            
            # Step 4: Ensure gas workers are assigned
            await self._assign_gas_workers()
            
        except Exception as e:
            if self.bot.iteration % 200 == 0:
                print(f"[RESOURCE_MANAGER] Error in optimization: {e}")
    
    async def _handle_idle_workers(self) -> None:
        """Assign idle workers to resources"""
        drones = self.bot.units(UnitTypeId.DRONE)
        if not drones.exists:
            return
        
        idle_drones = [drone for drone in drones if drone.is_idle]
        if not idle_drones:
            return
        
        # Find nearest base for each idle drone
        if not self.bot.townhalls.exists:
            return
        
        for drone in idle_drones[:10]:  # Process up to 10 at a time
            try:
                # Find nearest base
                nearest_base = self.bot.townhalls.closest_to(drone.position)
                
                # Find nearest mineral field
                minerals = self.bot.mineral_field.closer_than(15, nearest_base.position)
                if minerals.exists:
                    mineral = minerals.closest_to(drone.position)
                    await self.bot.do(drone.gather(mineral))
                else:
                    # No minerals nearby, move to base
                    await self.bot.do(drone.move(nearest_base.position))
            except Exception:
                pass
    
    async def _optimize_base_worker_distribution(self) -> None:
        """
        Optimize worker distribution for each base
        Target: 16 workers per base (14 minerals + 2 gas)
        """
        if not self.bot.townhalls.exists:
            return
        
        for base in self.bot.townhalls:
            try:
                base_info = self._analyze_base_resources(base)
                
                # Calculate optimal distribution
                target_minerals = WORKERS_PER_BASE - (base_info.target_gas_workers * WORKERS_PER_GAS)
                target_minerals = max(14, min(target_minerals, 16))  # 14-16 mineral workers
                
                # Count current workers at this base
                current_mineral_workers = self._count_mineral_workers(base)
                current_gas_workers = self._count_gas_workers(base)
                
                # Adjust if needed
                if current_mineral_workers < target_minerals:
                    # Need more mineral workers
                    await self._assign_workers_to_minerals(base, target_minerals - current_mineral_workers)
                elif current_mineral_workers > target_minerals + 2:
                    # Too many mineral workers, reassign some
                    excess = current_mineral_workers - target_minerals
                    await self._reassign_excess_workers(base, excess)
                
            except Exception as e:
                if self.bot.iteration % 200 == 0:
                    print(f"[RESOURCE_MANAGER] Error optimizing base {base}: {e}")
    
    def _analyze_base_resources(self, base: Any) -> BaseResourceInfo:
        """Analyze resources available at a base"""
        # Count nearby minerals
        minerals = self.bot.mineral_field.closer_than(15, base.position)
        mineral_count = minerals.amount if hasattr(minerals, 'amount') else len(list(minerals))
        
        # Count extractors at this base
        extractors = []
        if hasattr(self.bot, 'structures'):
            base_extractors = self.bot.structures(UnitTypeId.EXTRACTOR).closer_than(10, base.position)
            extractors = list(base_extractors) if base_extractors.exists else []
        
        # Calculate target gas workers
        ready_extractors = [e for e in extractors if e.is_ready]
        target_gas_workers = len(ready_extractors) * WORKERS_PER_GAS
        
        # Count current workers
        mineral_workers = self._count_mineral_workers(base)
        gas_workers = self._count_gas_workers(base)
        
        return BaseResourceInfo(
            base=base,
            mineral_workers=mineral_workers,
            gas_workers=gas_workers,
            total_workers=mineral_workers + gas_workers,
            target_mineral_workers=WORKERS_PER_BASE - target_gas_workers,
            target_gas_workers=target_gas_workers,
            minerals_nearby=mineral_count,
            extractors=extractors
        )
    
    def _count_mineral_workers(self, base: Any) -> int:
        """Count workers gathering minerals at this base"""
        drones = self.bot.units(UnitTypeId.DRONE)
        if not drones.exists:
            return 0
        
        count = 0
        minerals = self.bot.mineral_field.closer_than(15, base.position)
        
        for drone in drones:
            if drone.is_gathering and drone.order_target:
                # Check if gathering from nearby mineral
                if minerals.exists:
                    for mineral in minerals:
                        if drone.order_target == mineral.tag:
                            count += 1
                            break
        
        return count
    
    def _count_gas_workers(self, base: Any) -> int:
        """Count workers gathering gas at this base"""
        drones = self.bot.units(UnitTypeId.DRONE)
        if not drones.exists:
            return 0
        
        extractors = []
        if hasattr(self.bot, 'structures'):
            base_extractors = self.bot.structures(UnitTypeId.EXTRACTOR).closer_than(10, base.position)
            extractors = list(base_extractors) if base_extractors.exists else []
        
        if not extractors:
            return 0
        
        count = 0
        extractor_tags = {e.tag for e in extractors}
        
        for drone in drones:
            if drone.is_gathering and drone.order_target:
                if drone.order_target in extractor_tags:
                    count += 1
        
        return count
    
    async def _assign_workers_to_minerals(self, base: Any, count: int) -> None:
        """Assign workers to gather minerals at a base"""
        if count <= 0:
            return
        
        drones = self.bot.units(UnitTypeId.DRONE)
        if not drones.exists:
            return
        
        # Find available drones (idle or far from this base)
        available_drones = []
        for drone in drones:
            if drone.is_idle:
                available_drones.append(drone)
            elif not drone.is_gathering:
                # Not gathering, can reassign
                if drone.distance_to(base) > 20:
                    available_drones.append(drone)
        
        # Assign to minerals
        minerals = self.bot.mineral_field.closer_than(15, base.position)
        if not minerals.exists:
            return
        
        assigned = 0
        for drone in available_drones[:count]:
            try:
                mineral = minerals.closest_to(drone.position)
                await self.bot.do(drone.gather(mineral))
                assigned += 1
            except Exception:
                pass
    
    async def _reassign_excess_workers(self, base: Any, excess: int) -> None:
        """Reassign excess workers from this base to other bases or gas"""
        if excess <= 0:
            return
        
        drones = self.bot.units(UnitTypeId.DRONE)
        if not drones.exists:
            return
        
        # Find workers at this base that are gathering minerals
        base_drones = []
        minerals = self.bot.mineral_field.closer_than(15, base.position)
        
        for drone in drones:
            if drone.is_gathering and drone.order_target:
                if minerals.exists:
                    for mineral in minerals:
                        if drone.order_target == mineral.tag:
                            base_drones.append(drone)
                            break
        
        # Reassign excess workers
        reassigned = 0
        for drone in base_drones[:excess]:
            try:
                # Try to assign to gas first
                extractors = self.bot.structures(UnitTypeId.EXTRACTOR).ready.closer_than(10, base.position)
                if extractors.exists:
                    extractor = extractors.first
                    if extractor.assigned_harvesters < extractor.ideal_harvesters:
                        await self.bot.do(drone.gather(extractor))
                        reassigned += 1
                        continue
                
                # Otherwise, assign to another base
                if self.bot.townhalls.amount > 1:
                    other_bases = [b for b in self.bot.townhalls if b != base]
                    if other_bases:
                        other_base = other_bases[0]
                        other_minerals = self.bot.mineral_field.closer_than(15, other_base.position)
                        if other_minerals.exists:
                            mineral = other_minerals.closest_to(drone.position)
                            await self.bot.do(drone.gather(mineral))
                            reassigned += 1
            except Exception:
                pass
    
    async def _balance_workers_across_bases(self) -> None:
        """Balance workers across multiple bases"""
        if self.bot.townhalls.amount < 2:
            return
        
        # Calculate workers per base
        total_workers = self.bot.workers.amount if hasattr(self.bot.workers, 'amount') else len(list(self.bot.workers))
        workers_per_base = total_workers // self.bot.townhalls.amount
        
        # Find bases with too many or too few workers
        base_info_list = []
        for base in self.bot.townhalls:
            info = self._analyze_base_resources(base)
            base_info_list.append((base, info))
        
        # Sort by worker count
        base_info_list.sort(key=lambda x: x[1].total_workers)
        
        # Redistribute if imbalance is significant
        if base_info_list:
            min_workers = base_info_list[0][1].total_workers
            max_workers = base_info_list[-1][1].total_workers
            
            if max_workers - min_workers > 4:  # Significant imbalance
                # Move workers from bases with too many to bases with too few
                excess_bases = [b for b, info in base_info_list if info.total_workers > workers_per_base + 2]
                deficit_bases = [b for b, info in base_info_list if info.total_workers < workers_per_base - 2]
                
                for excess_base in excess_bases:
                    for deficit_base in deficit_bases:
                        excess_info = self._analyze_base_resources(excess_base)
                        deficit_info = self._analyze_base_resources(deficit_base)
                        
                        if excess_info.total_workers > deficit_info.total_workers + 2:
                            await self._move_worker_between_bases(excess_base, deficit_base, 1)
    
    async def _move_worker_between_bases(self, from_base: Any, to_base: Any, count: int) -> None:
        """Move workers from one base to another"""
        drones = self.bot.units(UnitTypeId.DRONE)
        if not drones.exists:
            return
        
        # Find workers at from_base
        from_minerals = self.bot.mineral_field.closer_than(15, from_base.position)
        workers_to_move = []
        
        for drone in drones:
            if drone.is_gathering and drone.order_target:
                if from_minerals.exists:
                    for mineral in from_minerals:
                        if drone.order_target == mineral.tag:
                            workers_to_move.append(drone)
                            break
        
        # Move to to_base
        to_minerals = self.bot.mineral_field.closer_than(15, to_base.position)
        if not to_minerals.exists:
            return
        
        moved = 0
        for drone in workers_to_move[:count]:
            try:
                mineral = to_minerals.closest_to(drone.position)
                await self.bot.do(drone.gather(mineral))
                moved += 1
            except Exception:
                pass
    
    async def _assign_gas_workers(self) -> None:
        """Ensure all extractors have optimal workers"""
        extractors = self.bot.structures(UnitTypeId.EXTRACTOR).ready
        if not extractors.exists:
            return
        
        for extractor in extractors:
            try:
                current_workers = extractor.assigned_harvesters
                ideal_workers = extractor.ideal_harvesters
                
                if current_workers < ideal_workers:
                    # Need more workers
                    needed = ideal_workers - current_workers
                    await self._assign_workers_to_gas(extractor, needed)
                elif current_workers > ideal_workers + 1:
                    # Too many workers, reassign to minerals
                    excess = current_workers - ideal_workers
                    await self._reassign_gas_workers_to_minerals(extractor, excess)
            except Exception:
                pass
    
    async def _assign_workers_to_gas(self, extractor: Any, count: int) -> None:
        """Assign workers to gather gas"""
        if count <= 0:
            return
        
        drones = self.bot.units(UnitTypeId.DRONE)
        if not drones.exists:
            return
        
        # Find nearest base
        if not self.bot.townhalls.exists:
            return
        
        nearest_base = self.bot.townhalls.closest_to(extractor.position)
        
        # Find available drones (idle or gathering minerals nearby)
        available_drones = []
        nearby_minerals = self.bot.mineral_field.closer_than(15, nearest_base.position)
        
        for drone in drones:
            if drone.is_idle:
                available_drones.append(drone)
            elif drone.is_gathering and drone.order_target:
                # Check if gathering from nearby minerals
                if nearby_minerals.exists:
                    for mineral in nearby_minerals:
                        if drone.order_target == mineral.tag:
                            available_drones.append(drone)
                            break
        
        # Assign to gas
        assigned = 0
        for drone in available_drones[:count]:
            try:
                await self.bot.do(drone.gather(extractor))
                assigned += 1
            except Exception:
                pass
    
    async def _reassign_gas_workers_to_minerals(self, extractor: Any, count: int) -> None:
        """Reassign excess gas workers to minerals"""
        if count <= 0:
            return
        
        drones = self.bot.units(UnitTypeId.DRONE)
        if not drones.exists:
            return
        
        # Find workers gathering from this extractor
        gas_workers = []
        for drone in drones:
            if drone.is_gathering and drone.order_target == extractor.tag:
                gas_workers.append(drone)
        
        # Find nearest base and minerals
        if not self.bot.townhalls.exists:
            return
        
        nearest_base = self.bot.townhalls.closest_to(extractor.position)
        minerals = self.bot.mineral_field.closer_than(15, nearest_base.position)
        
        if not minerals.exists:
            return
        
        reassigned = 0
        for drone in gas_workers[:count]:
            try:
                mineral = minerals.closest_to(drone.position)
                await self.bot.do(drone.gather(mineral))
                reassigned += 1
            except Exception:
                pass
    
    def get_resource_efficiency(self) -> Dict[str, float]:
        """
        Calculate resource gathering efficiency metrics
        
        Returns:
            Dictionary with efficiency metrics
        """
        try:
            total_workers = self.bot.workers.amount if hasattr(self.bot.workers, 'amount') else len(list(self.bot.workers))
            total_bases = self.bot.townhalls.amount if hasattr(self.bot.townhalls, 'amount') else len(list(self.bot.townhalls))
            
            if total_bases == 0:
                return {"efficiency": 0.0, "workers_per_base": 0.0}
            
            workers_per_base = total_workers / total_bases if total_bases > 0 else 0
            optimal_workers_per_base = WORKERS_PER_BASE
            
            efficiency = min(1.0, workers_per_base / optimal_workers_per_base) if optimal_workers_per_base > 0 else 0.0
            
            return {
                "efficiency": efficiency,
                "workers_per_base": workers_per_base,
                "total_workers": total_workers,
                "total_bases": total_bases
            }
        except Exception:
            return {"efficiency": 0.0, "workers_per_base": 0.0}
