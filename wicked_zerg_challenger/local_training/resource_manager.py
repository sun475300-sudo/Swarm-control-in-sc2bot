# -*- coding: utf-8 -*-
"""
Resource Manager - Optimized resource gathering and worker management.

Features:
- Gas/mineral ratio optimization
- Idle worker management
- Mineral line saturation tracking
- Gas extractor timing
- Resource spending priority
"""

import logging
from typing import Dict, List

logger = logging.getLogger("ResourceManager")

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:

    class _SC2StubSymbol:
        """Sentinel sc2 enum member used when python-sc2 is unavailable.

        Hashable, comparable, stringifies to its name, but is *not* a
        Python ``str`` so build-order classifiers can distinguish stub
        enum members from upgrade-name strings."""

        __slots__ = ("_name",)

        def __init__(self, name):
            self._name = name

        def __eq__(self, other):
            if isinstance(other, _SC2StubSymbol):
                return other._name == self._name
            return NotImplemented

        def __hash__(self):
            return hash(("_SC2StubSymbol", self._name))

        def __repr__(self):
            return self._name

        def __str__(self):
            return self._name

    class _SC2StubMeta(type):
        _cache: dict = {}

        def __getattr__(cls, name):
            key = (cls.__name__, name)
            sym = cls._cache.get(key)
            if sym is None:
                sym = _SC2StubSymbol(name)
                cls._cache[key] = sym
            return sym
    class UnitTypeId(metaclass=_SC2StubMeta):
        pass


class ResourceManager:
    """
    Optimized resource gathering controller.

    Manages worker distribution for optimal income:
    - 16 workers on minerals per base (2 per patch)
    - 3 workers per extractor
    - Automatic gas timing based on tech needs
    """

    def __init__(self, bot):
        """
        Initialize resource manager.

        Args:
            bot: The main bot instance
        """
        self.bot = bot

        # Optimal saturation values
        self.optimal_mineral_workers = 16  # Per base
        self.optimal_gas_workers = 3  # Per extractor

        # Gas timing thresholds
        self.first_gas_timing = 17  # Worker count for first gas
        self.second_gas_timing = 24  # Worker count for second gas
        self.third_gas_timing = 40  # Worker count for third gas

        # Update tracking
        self.last_update = 0
        self.update_interval = 22  # ~1 second

        # Resource statistics
        self.income_history: List[Dict] = []
        self.last_minerals = 0
        self.last_gas = 0

    async def optimize_resource_gathering(self) -> None:
        """
        Main optimization loop.

        Called periodically to optimize worker distribution.
        """
        iteration = getattr(self.bot, "iteration", 0)
        if iteration - self.last_update < self.update_interval:
            return
        self.last_update = iteration

        try:
            # Track income
            self._track_income()

            # Fix idle workers
            await self._assign_idle_workers()

            # Optimize gas workers
            await self._optimize_gas_workers()

            # Build extractors if needed
            await self._auto_build_extractors()

        except Exception as e:
            if iteration % 50 == 0:
                logger.error(f"Resource manager error: {e}")

    def _track_income(self) -> None:
        """Track resource income over time."""
        minerals = getattr(self.bot, "minerals", 0)
        gas = getattr(self.bot, "vespene", 0)
        game_time = getattr(self.bot, "time", 0.0)

        mineral_income = minerals - self.last_minerals
        gas_income = gas - self.last_gas

        self.income_history.append(
            {
                "time": game_time,
                "mineral_income": mineral_income,
                "gas_income": gas_income,
            }
        )

        # Keep only last 10 entries
        if len(self.income_history) > 10:
            self.income_history.pop(0)

        self.last_minerals = minerals
        self.last_gas = gas

    async def _assign_idle_workers(self) -> None:
        """Assign idle workers to resource gathering."""
        if not hasattr(self.bot, "workers"):
            return

        workers = self.bot.workers
        if not workers:
            return

        idle_workers = workers.idle
        if not idle_workers:
            return

        townhalls = getattr(self.bot, "townhalls", [])
        if not townhalls:
            return

        for worker in idle_workers:
            # Find nearest mineral patch
            best_target = None
            best_distance = 999

            for th in townhalls:
                if not th.is_ready:
                    continue

                # Check saturation
                assigned = th.assigned_harvesters
                ideal = th.ideal_harvesters
                if assigned >= ideal + 2:
                    continue  # Over-saturated

                # Find mineral patches
                minerals = self.bot.mineral_field.closer_than(10, th)
                if minerals:
                    closest_mineral = minerals.closest_to(worker)
                    dist = worker.distance_to(closest_mineral)
                    if dist < best_distance:
                        best_distance = dist
                        best_target = closest_mineral

            if best_target:
                try:
                    result = self.bot.do(worker.gather(best_target))
                    if hasattr(result, "__await__"):
                        await result
                except Exception as e:
                    logger.error(f"Worker gather failed: {e}")
                    continue

    async def _optimize_gas_workers(self) -> None:
        """Optimize gas worker assignment."""
        if not hasattr(self.bot, "gas_buildings"):
            return

        extractors = self.bot.gas_buildings.ready
        if not extractors:
            return

        workers = getattr(self.bot, "workers", [])
        if not workers:
            return

        if self._should_prioritize_minerals_over_gas():
            await self._move_gas_workers_to_minerals(extractors)
            return

        for extractor in extractors:
            assigned = extractor.assigned_harvesters
            ideal = self.optimal_gas_workers

            if assigned < ideal:
                # Need more workers
                workers_needed = ideal - assigned

                # Find nearby workers on minerals
                nearby_workers = workers.filter(
                    lambda w: (
                        w.is_gathering
                        and not w.is_carrying_vespene
                        and w.distance_to(extractor) < 15
                    )
                )

                for _ in range(min(workers_needed, len(nearby_workers))):
                    if not nearby_workers:
                        break
                    worker = nearby_workers.closest_to(extractor)
                    try:
                        result = self.bot.do(worker.gather(extractor))
                        if hasattr(result, "__await__"):
                            await result
                        nearby_workers = nearby_workers.filter(
                            lambda w: w.tag != worker.tag
                        )
                    except Exception as e:
                        logger.error(f"Gas worker assign failed: {e}")
                        continue

            elif assigned > ideal:
                # Too many workers on gas, move some to minerals
                # This is handled by economy_manager redistribution
                pass

    def _should_prioritize_minerals_over_gas(self) -> bool:
        """Return True when gas is banked and minerals are the bottleneck.
        FIX P0-7: 더 적극적인 가스 워커 이동 (기존: gas > minerals * 3 → gas > minerals * 2)
        """
        try:
            minerals = int(getattr(self.bot, "minerals", 0) or 0)
            gas = int(getattr(self.bot, "vespene", 0) or 0)
        except (TypeError, ValueError):
            return False

        if gas >= 500 and minerals < 300:
            return True
        if gas >= 1000 and minerals < 500:
            return True
        if gas >= 2000:
            return True
        return gas > max(200, minerals * 2) and minerals < 800

    async def _move_gas_workers_to_minerals(self, extractors) -> int:
        """Move a small batch of gas workers back to mineral patches."""
        if not hasattr(self.bot, "workers") or not hasattr(self.bot, "townhalls"):
            return 0
        if not hasattr(self.bot, "mineral_field"):
            return 0

        extractor_tags = {
            getattr(extractor, "tag", None)
            for extractor in self._as_unit_list(extractors)
            if getattr(extractor, "tag", None) is not None
        }
        moved = 0

        for worker in self.bot.workers:
            if moved >= 6:
                break
            if not self._is_worker_on_gas(worker, extractor_tags):
                continue

            base = self._closest_from(self.bot.townhalls, worker)
            if not base:
                continue

            minerals = self.bot.mineral_field.closer_than(10, base)
            mineral = self._closest_from(minerals, worker)
            if not mineral:
                continue

            try:
                result = self.bot.do(worker.gather(mineral))
                if hasattr(result, "__await__"):
                    await result
                moved += 1
            except Exception as e:
                logger.error(f"Gas worker mineral reassignment failed: {e}")

        return moved

    def _is_worker_on_gas(self, worker, extractor_tags: set) -> bool:
        if getattr(worker, "is_carrying_vespene", False):
            return True

        target = getattr(worker, "order_target", None)
        if target in extractor_tags:
            return True

        target_tag = getattr(target, "tag", None)
        if target_tag in extractor_tags:
            return True

        target_type = getattr(target, "type_id", None)
        type_name = str(getattr(target_type, "name", target_type)).upper()
        return (
            "EXTRACTOR" in type_name
            or "ASSIMILATOR" in type_name
            or "REFINERY" in type_name
        )

    def _closest_from(self, units, target):
        if not units:
            return None
        if hasattr(units, "closest_to"):
            return units.closest_to(target)

        unit_list = self._as_unit_list(units)
        return unit_list[0] if unit_list else None

    def _as_unit_list(self, units) -> list:
        if not units:
            return []
        try:
            return list(units)
        except TypeError:
            return [units]

    async def _auto_build_extractors(self) -> None:
        """Automatically build extractors based on worker count."""
        if not hasattr(self.bot, "workers"):
            return

        worker_count = self.bot.workers.amount
        extractors = (
            self.bot.gas_buildings if hasattr(self.bot, "gas_buildings") else []
        )
        extractor_count = len(extractors) if extractors else 0

        # Determine desired gas geysers
        if worker_count >= self.third_gas_timing:
            desired_extractors = 3
        elif worker_count >= self.second_gas_timing:
            desired_extractors = 2
        elif worker_count >= self.first_gas_timing:
            desired_extractors = 1
        else:
            desired_extractors = 0

        # Limit by base count
        bases = getattr(self.bot, "townhalls", [])
        try:
            if hasattr(bases, "amount"):
                base_count = int(getattr(bases, "amount", 0) or 0)
            else:
                base_count = len(list(bases)) if bases else 0
        except (TypeError, ValueError):
            base_count = 0
        max_extractors = base_count * 2
        desired_extractors = min(desired_extractors, max_extractors)

        # Build extractor if needed
        pending = (
            self.bot.already_pending(UnitTypeId.EXTRACTOR)
            if hasattr(self.bot, "already_pending")
            else 0
        )
        if self._should_delay_extractor(extractor_count, pending):
            return
        if extractor_count + pending < desired_extractors:
            if self.bot.can_afford(UnitTypeId.EXTRACTOR):
                await self._build_extractor()

    def _should_delay_extractor(self, extractor_count: int, pending: int) -> bool:
        """Keep gas behind natural and third Hatchery progress."""
        townhalls = getattr(self.bot, "townhalls", None)
        try:
            if hasattr(townhalls, "amount"):
                base_count = int(getattr(townhalls, "amount", 1) or 1)
            else:
                base_count = len(list(townhalls)) if townhalls else 1
        except (TypeError, ValueError):
            base_count = 1

        already_pending = getattr(self.bot, "already_pending", lambda _: 0)
        pending_hatch = int(already_pending(UnitTypeId.HATCHERY) or 0)

        if base_count < 2 and pending_hatch == 0:
            return True
        if base_count < 3 and extractor_count + pending >= 1:
            return True
        return False

    async def _build_extractor(self) -> None:
        """Build extractor on nearest available geyser."""
        if not hasattr(self.bot, "townhalls"):
            return

        townhalls = self.bot.townhalls.ready
        if not townhalls:
            return

        # Find geyser without extractor
        for th in townhalls:
            geysers = self.bot.vespene_geyser.closer_than(10, th)
            for geyser in geysers:
                # Check if already has extractor
                has_extractor = any(
                    e.distance_to(geyser) < 1 for e in self.bot.gas_buildings
                )
                if has_extractor:
                    continue

                # Build extractor
                workers = self.bot.workers.closer_than(20, geyser)
                if workers:
                    worker = workers.closest_to(geyser)
                    try:
                        result = self.bot.do(worker.build_gas(geyser))
                        if hasattr(result, "__await__"):
                            await result
                        return
                    except Exception as e:
                        logger.error(f"Gas build failed: {e}")
                        continue

    def get_saturation_status(self) -> Dict[str, int]:
        """
        Get current resource saturation status.

        Returns:
            Dict with saturation info per base
        """
        result = {
            "total_workers": 0,
            "mineral_workers": 0,
            "gas_workers": 0,
            "over_saturated_bases": 0,
            "under_saturated_bases": 0,
        }

        if not hasattr(self.bot, "townhalls"):
            return result

        townhalls = self.bot.townhalls.ready
        extractors = (
            self.bot.gas_buildings.ready if hasattr(self.bot, "gas_buildings") else []
        )

        for th in townhalls:
            assigned = th.assigned_harvesters
            ideal = th.ideal_harvesters
            result["mineral_workers"] += assigned

            if assigned > ideal + 2:
                result["over_saturated_bases"] += 1
            elif assigned < ideal - 2:
                result["under_saturated_bases"] += 1

        for extractor in extractors:
            result["gas_workers"] += extractor.assigned_harvesters

        result["total_workers"] = result["mineral_workers"] + result["gas_workers"]

        return result

    def get_income_rate(self) -> Dict[str, float]:
        """
        Get estimated income rate.

        Returns:
            Dict with mineral and gas income per update cycle
        """
        if not self.income_history:
            return {"minerals": 0.0, "gas": 0.0}

        recent = (
            self.income_history[-5:]
            if len(self.income_history) >= 5
            else self.income_history
        )
        avg_mineral = sum(h["mineral_income"] for h in recent) / len(recent)
        avg_gas = sum(h["gas_income"] for h in recent) / len(recent)

        return {
            "minerals": avg_mineral,
            "gas": avg_gas,
        }

    def should_prioritize_gas(self) -> bool:
        """
        Determine if gas collection should be prioritized.

        Returns:
            True if gas is more needed than minerals
        """
        minerals = getattr(self.bot, "minerals", 0)
        gas = getattr(self.bot, "vespene", 0)

        # If gas is low and minerals are high, prioritize gas
        if minerals > 500 and gas < 200:
            return True

        # If planning to build gas-heavy units
        # Check for tech buildings
        if hasattr(self.bot, "structures"):
            has_spire = (
                self.bot.structures(UnitTypeId.SPIRE).exists
                if hasattr(UnitTypeId, "SPIRE")
                else False
            )
            has_hydra_den = (
                self.bot.structures.filter(
                    lambda s: hasattr(s, "type_id")
                    and getattr(s.type_id, "name", "") == "HYDRALISKDEN"
                ).exists
                if hasattr(self.bot, "structures")
                else False
            )

            if (has_spire or has_hydra_den) and gas < 300:
                return True
