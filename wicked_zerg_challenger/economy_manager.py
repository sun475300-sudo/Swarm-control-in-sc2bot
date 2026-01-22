# -*- coding: utf-8 -*-
"""
Economy Manager - deterministic worker production with macro hatcheries.
"""

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:  # Fallbacks for tooling environments

    class UnitTypeId:
        DRONE = "DRONE"
        OVERLORD = "OVERLORD"
        HATCHERY = "HATCHERY"


from local_training.economy_combat_balancer import EconomyCombatBalancer


class EconomyManager:
    """
    Manages economy and larva production.

    Features:
    - Dynamic drone production based on base count
    - Auto supply management
    - Macro hatchery construction when resources stockpile
    - Prevents resource banking by expanding production capacity
    """

    def __init__(self, bot):
        self.bot = bot
        self.balancer = EconomyCombatBalancer(bot)
        # Resource thresholds for macro hatchery
        self.macro_hatchery_mineral_threshold = 1500  # Build macro hatch if minerals > 1500
        self.macro_hatchery_larva_threshold = 3  # and average larva per base < 3
        self.last_macro_hatch_check = 0
        self.macro_hatch_check_interval = 50  # Check every 50 frames

    async def on_step(self, iteration: int) -> None:
        if not hasattr(self.bot, "larva"):
            return

        await self._train_overlord_if_needed()
        await self._train_drone_if_needed()

        # Distribute workers to gas (every 22 frames = ~1 second)
        if iteration % 22 == 0:
            await self._distribute_workers_to_gas()

        # Redistribute mineral workers between bases (every 44 frames = ~2 seconds)
        if iteration % 44 == 0:
            await self._redistribute_mineral_workers()

        # Check for expansion needs when resources depleting (every 66 frames = ~3 seconds)
        if iteration % 66 == 0:
            await self._check_expansion_on_depletion()

        # Check for macro hatchery needs periodically
        if iteration - self.last_macro_hatch_check >= self.macro_hatch_check_interval:
            self.last_macro_hatch_check = iteration
            await self._build_macro_hatchery_if_needed()

    async def _train_overlord_if_needed(self) -> None:
        if not hasattr(self.bot, "supply_left"):
            return

        if self.bot.supply_left >= 2:
            return

        if not self.bot.can_afford(UnitTypeId.OVERLORD):
            return

        larva_unit = self._get_first_larva()
        if not larva_unit:
            return

        try:
            await self.bot.do(larva_unit.train(UnitTypeId.OVERLORD))
        except Exception:
            return

    async def _train_drone_if_needed(self) -> None:
        # === Emergency Mode Check ===
        # 비상 모드에서는 최소 드론만 유지 (12기)
        strategy = getattr(self.bot, "strategy_manager", None)
        if strategy and getattr(strategy, "emergency_active", False):
            worker_count = 0
            if hasattr(self.bot, "workers"):
                workers = self.bot.workers
                worker_count = workers.amount if hasattr(workers, "amount") else len(list(workers))

            if worker_count >= 12:
                # 비상 모드 + 최소 드론 확보 → 드론 생산 중단
                return

        if not self.balancer.should_train_drone():
            return

        if hasattr(self.bot, "supply_left") and self.bot.supply_left <= 0:
            return

        if not self.bot.can_afford(UnitTypeId.DRONE):
            return

        larva_unit = self._get_first_larva()
        if not larva_unit:
            return

        try:
            await self.bot.do(larva_unit.train(UnitTypeId.DRONE))
        except Exception as e:
            game_time = getattr(self.bot, "time", 0.0)
            print(f"[ECONOMY_WARN] [{int(game_time)}s] Drone train failed: {e}")
            return

    async def _distribute_workers_to_gas(self) -> None:
        """
        Distribute workers to extractors.

        Ensures each extractor has 3 workers for optimal gas mining.
        """
        if not hasattr(self.bot, "gas_buildings"):
            return

        extractors = self.bot.gas_buildings.ready
        if not extractors:
            return

        if not hasattr(self.bot, "workers") or not self.bot.workers:
            return

        for extractor in extractors:
            # Check how many workers are assigned
            assigned_workers = extractor.assigned_harvesters
            ideal_workers = extractor.ideal_harvesters  # Usually 3

            if assigned_workers < ideal_workers:
                # Find idle or mineral-mining workers nearby
                workers_needed = ideal_workers - assigned_workers

                try:
                    # Get workers that are gathering minerals (not gas)
                    available_workers = self.bot.workers.filter(
                        lambda w: (
                            w.is_gathering and
                            not w.is_carrying_vespene and
                            w.distance_to(extractor) < 20
                        )
                    )

                    if not available_workers:
                        # Try idle workers
                        available_workers = self.bot.workers.filter(
                            lambda w: w.is_idle and w.distance_to(extractor) < 20
                        )

                    if available_workers:
                        # Assign closest workers to extractor
                        for _ in range(min(workers_needed, len(available_workers))):
                            worker = available_workers.closest_to(extractor)
                            if worker:
                                await self.bot.do(worker.gather(extractor))
                                available_workers = available_workers.filter(
                                    lambda w: w.tag != worker.tag
                                )
                except Exception:
                    continue

    async def _build_macro_hatchery_if_needed(self) -> None:
        """
        Build macro hatchery when resources are stockpiling.

        Conditions:
        - Minerals > threshold
        - Average larva per base < threshold
        - Have at least 2 bases
        - Not already building a hatchery
        """
        if not hasattr(self.bot, "minerals") or not hasattr(self.bot, "townhalls"):
            return

        # Check resource conditions
        minerals = self.bot.minerals
        if minerals < self.macro_hatchery_mineral_threshold:
            return

        # Check base count
        townhalls = self.bot.townhalls.ready
        if not townhalls or townhalls.amount < 2:
            return

        # Check larva availability
        total_larva = len(self.bot.larva) if hasattr(self.bot, "larva") else 0
        avg_larva_per_base = total_larva / max(1, townhalls.amount)

        if avg_larva_per_base >= self.macro_hatchery_larva_threshold:
            return  # Have enough larva production

        # Check if already building hatchery
        if hasattr(self.bot, "already_pending"):
            pending = self.bot.already_pending(UnitTypeId.HATCHERY)
            if pending > 0:
                return

        # Don't build if can't afford
        if not self.bot.can_afford(UnitTypeId.HATCHERY):
            return

        # Find safe build location near main base
        if not hasattr(self.bot, "start_location"):
            return

        main_base = townhalls.first
        build_location = await self._find_macro_hatch_location(main_base)

        if build_location:
            try:
                # Build macro hatchery
                worker = None
                if hasattr(self.bot, "workers") and self.bot.workers:
                    worker = self.bot.workers.closest_to(build_location)

                if worker:
                    await self.bot.do(
                        worker.build(UnitTypeId.HATCHERY, build_location)
                    )
            except Exception:
                pass

    async def _find_macro_hatch_location(self, main_base):
        """Find safe location for macro hatchery near main base."""
        if not hasattr(self.bot, "can_place"):
            return None

        try:
            # Try positions around main base at distance 8-12
            import math

            for angle in range(0, 360, 45):
                for distance in [8, 10, 12]:
                    rad = math.radians(angle)
                    x_offset = distance * math.cos(rad)
                    y_offset = distance * math.sin(rad)

                    try:
                        # Create Point2 if available
                        if hasattr(main_base.position, "__add__"):
                            test_pos = main_base.position.offset(
                                (x_offset, y_offset)
                            )
                        else:
                            continue

                        # Check if we can place hatchery there
                        if await self.bot.can_place(UnitTypeId.HATCHERY, test_pos):
                            return test_pos
                    except Exception:
                        continue

        except Exception:
            pass

        return None

    async def _redistribute_mineral_workers(self) -> None:
        """
        Redistribute mineral workers between bases.

        - Move workers from over-saturated bases to under-saturated ones
        - Move workers from DEPLETED bases to other bases
        - Detect bases with low/no mineral patches
        - Keep only gas workers at depleted bases with extractors
        - Optimal: 16 workers per base for minerals (2 per patch)
        """
        if not hasattr(self.bot, "townhalls") or not hasattr(self.bot, "workers"):
            return

        townhalls = self.bot.townhalls.ready
        if not townhalls or townhalls.amount < 2:
            return  # Need at least 2 bases

        workers = self.bot.workers
        if not workers:
            return

        try:
            # First: Check for DEPLETED bases (no mineral patches or < 3 patches)
            depleted_bases = []
            active_bases = []

            for th in townhalls:
                # Count mineral patches near this base
                nearby_minerals = self.bot.mineral_field.closer_than(10, th)
                mineral_count = nearby_minerals.amount if hasattr(nearby_minerals, 'amount') else len(list(nearby_minerals))

                # Count total minerals remaining
                total_minerals = sum(m.mineral_contents for m in nearby_minerals) if nearby_minerals else 0

                if mineral_count < 3 or total_minerals < 500:
                    # Base is depleted - move workers out
                    depleted_bases.append(th)
                else:
                    active_bases.append(th)

            # Move workers from depleted bases to active bases
            for depleted_th in depleted_bases:
                if not active_bases:
                    break

                # Get mineral workers at this depleted base (not gas workers)
                nearby_workers = workers.filter(
                    lambda w: (w.distance_to(depleted_th) < 15 and
                              w.is_gathering and
                              not w.is_carrying_vespene and
                              not any(e.distance_to(w) < 3 for e in self.bot.gas_buildings))
                )

                if not nearby_workers:
                    continue

                # Find best target base (closest active base with capacity)
                best_target = None
                best_deficit = 0
                for active_th in active_bases:
                    assigned = active_th.assigned_harvesters
                    ideal = active_th.ideal_harvesters
                    deficit = ideal - assigned
                    if deficit > best_deficit:
                        best_deficit = deficit
                        best_target = active_th

                if not best_target:
                    # All bases full - use closest
                    best_target = min(active_bases, key=lambda th: th.distance_to(depleted_th))

                # Move workers to target base
                workers_moved = 0
                for worker in nearby_workers:
                    if workers_moved >= 5:  # Max 5 at a time to avoid micro issues
                        break

                    minerals = self.bot.mineral_field.closer_than(10, best_target)
                    if minerals:
                        try:
                            await self.bot.do(worker.gather(minerals.closest_to(best_target)))
                            workers_moved += 1
                        except Exception:
                            continue

                if workers_moved > 0:
                    game_time = getattr(self.bot, "time", 0)
                    print(f"[ECONOMY] [{int(game_time)}s] Moved {workers_moved} workers from depleted base")

            # Second: Normal redistribution for over/under-saturated bases
            over_saturated = []
            under_saturated = []

            for th in active_bases:  # Only check active bases
                assigned = th.assigned_harvesters
                ideal = th.ideal_harvesters  # Usually 16 for minerals

                if assigned > ideal + 2:  # Over by more than 2
                    over_saturated.append((th, assigned - ideal))
                elif assigned < ideal - 2:  # Under by more than 2
                    under_saturated.append((th, ideal - assigned))

            # Move workers from over-saturated to under-saturated
            for over_th, excess in over_saturated:
                if not under_saturated:
                    break

                # Get workers near this townhall
                nearby_workers = workers.filter(
                    lambda w: w.distance_to(over_th) < 15 and w.is_gathering
                )

                for under_th, deficit in under_saturated[:]:
                    if excess <= 0 or deficit <= 0:
                        continue

                    # Move workers
                    workers_to_move = min(excess, deficit, 3)  # Max 3 at a time
                    for _ in range(workers_to_move):
                        if not nearby_workers:
                            break

                        worker = nearby_workers.furthest_to(over_th)
                        if worker:
                            # Find mineral field near target base
                            minerals = self.bot.mineral_field.closer_than(10, under_th)
                            if minerals:
                                await self.bot.do(worker.gather(minerals.closest_to(under_th)))
                                nearby_workers = nearby_workers.filter(
                                    lambda w: w.tag != worker.tag
                                )
                                excess -= 1
                                deficit -= 1

                    # Update under-saturated list
                    if deficit <= 0:
                        under_saturated.remove((under_th, deficit))

        except Exception:
            pass

    def _get_first_larva(self):
        larva = getattr(self.bot, "larva", None)
        if not larva:
            return None
        if hasattr(larva, "first"):
            return larva.first
        try:
            return next(iter(larva))
        except Exception:
            return None

    async def _check_expansion_on_depletion(self) -> None:
        """
        Check if we need to expand due to resource depletion.

        Triggers expansion if:
        - Total remaining minerals across bases < threshold
        - Worker saturation is high but income is dropping
        - No expansion currently pending
        """
        if not hasattr(self.bot, "townhalls") or not hasattr(self.bot, "mineral_field"):
            return

        townhalls = self.bot.townhalls.ready
        if not townhalls:
            return

        try:
            # Calculate total remaining minerals across all bases
            total_remaining_minerals = 0
            depleted_base_count = 0

            for th in townhalls:
                nearby_minerals = self.bot.mineral_field.closer_than(10, th)
                base_minerals = sum(m.mineral_contents for m in nearby_minerals) if nearby_minerals else 0
                total_remaining_minerals += base_minerals

                if base_minerals < 500:  # Less than 500 minerals = depleted
                    depleted_base_count += 1

            # Calculate threshold based on worker count
            worker_count = self.bot.workers.amount if hasattr(self.bot, "workers") else 0
            # Need ~1500 minerals per 16 workers for decent income
            mineral_threshold_per_worker = 100
            expansion_threshold = worker_count * mineral_threshold_per_worker

            # Check if we need to expand
            should_expand = False
            expand_reason = ""

            # Reason 1: Total minerals running low
            if total_remaining_minerals < expansion_threshold and total_remaining_minerals < 5000:
                should_expand = True
                expand_reason = f"low minerals ({int(total_remaining_minerals)} remaining)"

            # Reason 2: Multiple depleted bases
            if depleted_base_count >= townhalls.amount // 2 and townhalls.amount > 1:
                should_expand = True
                expand_reason = f"{depleted_base_count}/{townhalls.amount} bases depleted"

            # Reason 3: High worker count but low base count
            # Optimal: ~16 workers per base
            optimal_bases = max(1, worker_count // 16)
            if townhalls.amount < optimal_bases:
                should_expand = True
                expand_reason = f"need more bases for {worker_count} workers"

            if not should_expand:
                return

            # Check if already expanding
            if self.bot.already_pending(UnitTypeId.HATCHERY) > 0:
                return

            # Check if we can afford expansion
            if not self.bot.can_afford(UnitTypeId.HATCHERY):
                return

            # Try to expand
            if hasattr(self.bot, "expand_now"):
                try:
                    await self.bot.expand_now()
                    game_time = getattr(self.bot, "time", 0)
                    print(f"[ECONOMY] [{int(game_time)}s] Expanding due to {expand_reason}")
                except Exception:
                    pass
            elif hasattr(self.bot, "get_next_expansion"):
                try:
                    next_pos = await self.bot.get_next_expansion()
                    if next_pos:
                        await self.bot.build(UnitTypeId.HATCHERY, near=next_pos)
                        game_time = getattr(self.bot, "time", 0)
                        print(f"[ECONOMY] [{int(game_time)}s] Expanding due to {expand_reason}")
                except Exception:
                    pass

        except Exception:
            pass
