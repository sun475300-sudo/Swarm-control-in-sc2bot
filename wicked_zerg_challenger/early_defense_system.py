"""
Early Defense System

Purpose: Counter early rushes and improve initial survival rate
- Maximize survival rate between 1-3 minutes
- Detect early rushes and respond immediately
- Manage initial unit production priority
"""

import logging
from typing import Set

try:
    from config.constants import (
        EARLY_GAME_END_SECONDS,
        ENEMY_DETECT_RADIUS,
        MAX_WORKER_DEFENSE,
        PROXY_DEFENSE_WORKERS,
        PROXY_DETECT_RADIUS,
    )
except ImportError:
    EARLY_GAME_END_SECONDS = 180.0
    ENEMY_DETECT_RADIUS = 20.0
    PROXY_DETECT_RADIUS = 40.0
    PROXY_DEFENSE_WORKERS = 6
    MAX_WORKER_DEFENSE = 6

logger = logging.getLogger("EarlyDefenseSystem")
try:
    from sc2.bot_ai import BotAI
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.upgrade_id import UpgradeId
    from sc2.position import Point2
except ImportError:

    class BotAI:
        pass

    class UnitTypeId:
        pass

    class AbilityId:
        pass

    class UpgradeId:
        pass

    class Point2:
        pass


class EarlyDefenseSystem:
    """
    Early Defense System (0-3 minutes)

    Key Features:
    1. Detect early enemy units and alert
    2. Emergency Zergling production
    3. Worker defense/evacuation
    4. Queen production priority
    5. Spawning Pool construction priority
    """

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.early_game_threshold = EARLY_GAME_END_SECONDS
        self.early_rush_detected = False
        self.pool_started = False
        self.queen_started = False
        self.emergency_mode = False
        self.last_enemy_check = 0

        # Early threat detection
        self.early_threats: Set = set()
        self.proxy_structure_tags: Set = set()
        self.proxy_response_active = False
        self._proxy_spines_requested = 0
        self._proxy_worker_tags: Set = set()
        self._pulled_worker_tags: Set = set()
        self._workers_pulled: bool = False

        # FIX C3: Initialize missing attributes
        self._zergling_speed_researched = False
        self._spine_crawler_built = False
        self._spine_crawler_ordered = False

    async def on_step(self, iteration: int) -> None:
        """Alias for execute() — called by bot_step_integration."""
        await self.execute(iteration)

    def reset(self) -> None:
        """Reset state between training episodes."""
        self.early_rush_detected = False
        self.pool_started = False
        self.queen_started = False
        self.emergency_mode = False
        self.last_enemy_check = 0
        self.early_threats = set()
        self.proxy_structure_tags = set()
        self.proxy_response_active = False
        self._proxy_spines_requested = 0
        self._proxy_worker_tags = set()
        self._pulled_worker_tags = set()
        self._workers_pulled = False
        self._zergling_speed_researched = False
        self._spine_crawler_built = False
        self._spine_crawler_ordered = False

    async def execute(self, iteration: int) -> None:
        """
        Execute early defense logic every step
        """
        # Disable early defense after 3 minutes
        if self.bot.time > self.early_game_threshold:
            return

        await self._detect_proxy_structure_rush()
        if self.proxy_response_active:
            await self._proxy_structure_response()

        # 1. Detect early enemy units (Check every 0.5s)
        if self.bot.time - self.last_enemy_check > 0.5:
            await self._detect_early_threats()
            self.last_enemy_check = self.bot.time

        # 2. Priority Spawning Pool construction (After 12 drones)
        if not self.pool_started and self.bot.supply_used >= 12:
            await self._build_early_pool()

        # 3. Early Zergling production
        if self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready:
            await self._produce_early_zerglings()

        # 4. Queen priority production
        if (
            not self.queen_started
            and self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready
        ):
            await self._produce_first_queen()

        # 5. Zergling speed research ASAP (FIX: was never called)
        await self._research_zergling_speed_early()

        # 6. Early spine crawler at ~2 minutes (FIX: was never called)
        if self.bot.time >= 120.0:
            await self._build_early_spine_crawler()

        # 7. Emergency defense mode (If enemy detected)
        if self.emergency_mode or self.early_threats:
            await self._emergency_defense()

    async def _detect_early_threats(self) -> None:
        """
        Detect early enemy units and alert
        """
        # Check if enemy units are near our base
        if not self.bot.enemy_units:
            if self.early_rush_detected and not self.proxy_response_active:
                self.early_rush_detected = False
                self.emergency_mode = False
                self.early_threats = set()
                logger.info(
                    "[*] Early rush threat cleared (no visible enemies) — returning to normal mode [*]"
                )
            return

        main_base = self.bot.townhalls.first if self.bot.townhalls else None
        if not main_base:
            return

        nearby_enemies = self.bot.enemy_units.closer_than(
            ENEMY_DETECT_RADIUS, main_base.position
        )

        if nearby_enemies:
            self.early_rush_detected = True
            self.emergency_mode = True
            self.early_threats = set(nearby_enemies.tags)

            logger.warning(
                f"[WARNING] Early rush detected! {nearby_enemies.amount} enemies found (Game Time: {int(self.bot.time)}s)"
            )
            logger.info(f"Emergency Defense Mode ACTIVATED!")
        else:
            # Reset flags when threat has cleared
            if self.early_rush_detected and not self.proxy_response_active:
                self.early_rush_detected = False
                self.emergency_mode = False
                self.early_threats = set()
                logger.info(
                    "[*] Early rush threat cleared — returning to normal mode [*]"
                )

    async def _detect_proxy_structure_rush(self) -> None:
        """Detect proxy Barracks or cannon rush structures near our base."""
        if float(getattr(self.bot, "time", 0.0) or 0.0) > 150.0:
            if self.proxy_response_active:
                self._clear_proxy_response_if_destroyed()
            return

        main_base = self._main_base()
        if not main_base:
            return

        proxy_names = {"BARRACKS", "PHOTONCANNON", "BUNKER", "PYLON"}
        nearby_structures = []
        for structure in getattr(self.bot, "enemy_structures", []) or []:
            name = self._type_name(structure)
            if name not in proxy_names:
                continue
            try:
                distance = structure.distance_to(main_base)
            except Exception:
                position = getattr(structure, "position", None)
                distance = position.distance_to(main_base) if position else 999.0
            if distance <= 40.0:
                nearby_structures.append(structure)

        if not nearby_structures:
            self._clear_proxy_response_if_destroyed()
            return

        self.proxy_response_active = True
        self.emergency_mode = True
        self.early_rush_detected = True
        self.proxy_structure_tags = {
            getattr(structure, "tag", id(structure)) for structure in nearby_structures
        }
        self._publish_proxy_response_flags(True)
        logger.warning(
            f"[PROXY DEFENSE] Proxy structure rush detected at {int(self.bot.time)}s"
        )

    async def _proxy_structure_response(self) -> None:
        """Execute the Sprint 5.1 proxy/cannon immediate response."""
        targets = self._current_proxy_structures()
        if not targets:
            self._clear_proxy_response_if_destroyed()
            return

        target = min(targets, key=lambda s: self._distance_to_main(s))
        await self._request_proxy_spines()
        self._pull_workers_to_proxy(target, desired_count=6)
        self._train_all_larva_as_zerglings()

    async def _request_proxy_spines(self) -> None:
        if self._proxy_spines_requested >= 2:
            return

        main_base = self._main_base()
        if not main_base:
            return

        target_pos = getattr(main_base, "position", main_base)
        map_center = getattr(getattr(self.bot, "game_info", None), "map_center", None)
        if hasattr(target_pos, "towards") and map_center is not None:
            target_pos = target_pos.towards(map_center, 8)

        tech_coordinator = getattr(self.bot, "tech_coordinator", None)
        if tech_coordinator and hasattr(tech_coordinator, "request_structure"):
            while self._proxy_spines_requested < 2:
                tech_coordinator.request_structure(
                    UnitTypeId.SPINECRAWLER,
                    target_pos,
                    95,
                    "EarlyDefenseSystem-Proxy",
                )
                self._proxy_spines_requested += 1
            return

        if not hasattr(self.bot, "find_placement") or not getattr(
            self.bot, "workers", None
        ):
            return

        try:
            location = await self.bot.find_placement(
                UnitTypeId.SPINECRAWLER,
                target_pos,
                max_distance=8,
                placement_step=2,
            )
        except Exception:
            location = None
        if not location:
            return

        worker = self._closest_worker(location)
        if worker:
            self.bot.do(worker.build(UnitTypeId.SPINECRAWLER, location))
            self._proxy_spines_requested += 1

    def _pull_workers_to_proxy(self, target, desired_count: int = 6) -> None:
        workers = getattr(self.bot, "workers", None)
        if not workers:
            return

        if hasattr(workers, "closest_n_units"):
            pulled = workers.closest_n_units(
                getattr(target, "position", target), desired_count
            )
        else:
            worker_list = list(workers)
            pulled = sorted(worker_list, key=lambda w: w.distance_to(target))[
                :desired_count
            ]

        for worker in pulled:
            try:
                self.bot.do(worker.attack(target))
                self._proxy_worker_tags.add(worker.tag)
            except Exception:
                continue

    def _train_all_larva_as_zerglings(self) -> None:
        larvae = list(getattr(self.bot, "larva", []) or [])
        if not larvae or getattr(self.bot, "minerals", 0) < 50:
            return

        max_larvae = min(len(larvae), int(getattr(self.bot, "minerals", 0) // 50))
        for larva in larvae[:max_larvae]:
            try:
                self.bot.do(larva.train(UnitTypeId.ZERGLING))
            except Exception:
                continue

    def _current_proxy_structures(self):
        if not self.proxy_structure_tags:
            return []
        current = []
        for structure in getattr(self.bot, "enemy_structures", []) or []:
            tag = getattr(structure, "tag", id(structure))
            if tag in self.proxy_structure_tags:
                current.append(structure)
        return current

    def _clear_proxy_response_if_destroyed(self) -> None:
        if not self.proxy_response_active:
            return
        if self._current_proxy_structures():
            return

        self.proxy_response_active = False
        self.proxy_structure_tags.clear()
        self._proxy_worker_tags.clear()
        if not self.early_threats:
            self.emergency_mode = False
        self._publish_proxy_response_flags(False)
        logger.info("Proxy structures cleared. Early defense returning to normal.")

    def _publish_proxy_response_flags(self, active: bool) -> None:
        blackboard = getattr(self.bot, "blackboard", None)
        if not blackboard or not hasattr(blackboard, "set"):
            return
        blackboard.set("proxy_structure_rush", active)
        blackboard.set("cheese_detected", active)
        blackboard.set("enemy_aggression", active)
        blackboard.set("worker_pull_requested", active)
        blackboard.set("spend_larva_on_army", active)
        blackboard.set("drone_production_policy", "HALT" if active else "NORMAL")
        if active:
            blackboard.set("urgent_spine_count", 2)
            blackboard.set("urgent_spine_all_bases", True)

    def _main_base(self):
        townhalls = getattr(self.bot, "townhalls", None)
        if not townhalls:
            return None
        first = getattr(townhalls, "first", None)
        if first is not None:
            return first
        try:
            return list(townhalls)[0]
        except Exception:
            return None

    def _closest_worker(self, position):
        workers = getattr(self.bot, "workers", None)
        if not workers:
            return None
        if hasattr(workers, "closest_to"):
            return workers.closest_to(position)
        try:
            return min(workers, key=lambda worker: worker.distance_to(position))
        except Exception:
            return None

    def _distance_to_main(self, obj) -> float:
        main_base = self._main_base()
        if not main_base:
            return 999.0
        try:
            return obj.distance_to(main_base)
        except Exception:
            position = getattr(obj, "position", None)
            return position.distance_to(main_base) if position else 999.0

    @staticmethod
    def _type_name(unit_or_structure) -> str:
        return getattr(getattr(unit_or_structure, "type_id", None), "name", "").upper()

    async def _build_early_pool(self) -> None:
        """
        Build Spawning Pool early (12 Pool)
        """
        # Skip if Pool exists or is under construction
        if self.bot.structures(UnitTypeId.SPAWNINGPOOL):
            self.pool_started = True
            return

        if self.bot.already_pending(UnitTypeId.SPAWNINGPOOL) > 0:
            self.pool_started = True
            return

        # Check resources
        if self.bot.minerals < 200:
            return

        # Check workers
        if not self.bot.workers:
            return

        # Select build location (Near main base)
        main_base = self.bot.townhalls.first if self.bot.townhalls else None
        if not main_base:
            return

        # Pool 건설 via TechCoordinator
        try:
            tech_coordinator = getattr(self.bot, "tech_coordinator", None)
            if tech_coordinator and not tech_coordinator.is_planned(
                UnitTypeId.SPAWNINGPOOL
            ):
                target_pos = main_base.position.towards(
                    self.bot.game_info.map_center, 5
                )
                PRIORITY_DEFENSE = 85  # High priority for early defense
                tech_coordinator.request_structure(
                    UnitTypeId.SPAWNINGPOOL,
                    target_pos,
                    PRIORITY_DEFENSE,
                    "EarlyDefenseSystem",
                )
                self.pool_started = True
                logger.info(
                    f"[OK] Spawning Pool requested via TechCoordinator (Game Time: {int(self.bot.time)}s)"
                )
            elif not tech_coordinator:
                logger.warning(f"[WARNING] TechCoordinator not available")
        except Exception as e:
            logger.error(f"Failed to request Pool construction: {e}")

    async def _produce_early_zerglings(self) -> None:
        """
        Produce early Zerglings (Target: 6+)
        """
        # Goal: Initial 6 Zerglings
        target_zerglings = 6

        # 12 if emergency mode
        if self.emergency_mode:
            target_zerglings = 12

        current_zerglings = self.bot.units(UnitTypeId.ZERGLING).amount
        pending_zerglings = self.bot.already_pending(UnitTypeId.ZERGLING)

        if current_zerglings + pending_zerglings >= target_zerglings:
            return

        # Check Larva
        if not self.bot.larva:
            return

        # Check Resources
        if self.bot.minerals < 50:
            return

        # Produce Zerglings (As many as possible)
        larvae_for_lings = min(
            len(self.bot.larva),
            (target_zerglings - current_zerglings - pending_zerglings + 1)
            // 2,  # 2 per egg
            self.bot.minerals // 50,
        )

        for larva in self.bot.larva[:larvae_for_lings]:
            if self.bot.minerals >= 50:
                self.bot.do(larva.train(UnitTypeId.ZERGLING))

        if larvae_for_lings > 0:
            logger.info(
                f"Producing {larvae_for_lings * 2} Zerglings (Target: {target_zerglings})"
            )

    async def _produce_first_queen(self) -> None:
        """

        Priority First Queen production
        """
        # Skip if Queen exists
        if self.bot.units(UnitTypeId.QUEEN).amount >= 1:
            self.queen_started = True
            return

        if self.bot.already_pending(UnitTypeId.QUEEN) > 0:
            self.queen_started = True
            return

        # Check Hatchery
        if not self.bot.townhalls.ready:
            return

        # Check Resources
        if self.bot.minerals < 150:
            return

        # Produce Queen
        for hatchery in self.bot.townhalls.ready.idle:
            if self.bot.can_afford(UnitTypeId.QUEEN):
                self.bot.do(hatchery.train(UnitTypeId.QUEEN))
                self.queen_started = True
                logger.info(
                    f"[OK] Started First Queen Production (Game Time: {int(self.bot.time)}s)"
                )
                break

    async def _emergency_defense(self) -> None:
        """

        Emergency Defense Mode
        - Mobilize workers for defense
        - Zerglings assemble
        """
        if not self.early_threats:
            return

        main_base = self.bot.townhalls.first if self.bot.townhalls else None
        if not main_base:
            return

        # Re-check enemy units
        enemy_units = self.bot.enemy_units.filter(lambda u: u.tag in self.early_threats)
        if not enemy_units:
            # Threat cleared
            self.early_threats.clear()
            self.emergency_mode = False
            logger.info(f"Early threat cleared. Returning to normal mode.")
            return

        # Closest enemy
        closest_enemy = enemy_units.closest_to(main_base)

        # All Zerglings defend
        zerglings = self.bot.units(UnitTypeId.ZERGLING)
        if zerglings:
            idle_or_moving = zerglings.filter(lambda u: u.is_idle or u.is_moving)
            if idle_or_moving:
                idle_or_moving.attack(closest_enemy.position)

        # Worker Defense (Only if enemy is very close)
        if closest_enemy.distance_to(main_base) < 10:
            defending_workers = min(6, len(self.bot.workers))  # Max 6 workers
            workers_to_defend = self.bot.workers.closest_n_units(
                closest_enemy.position, defending_workers
            )

            for worker in workers_to_defend:
                # * CRITICAL: Ensure workers don't go further than 12 distance from base *
                if worker.distance_to(main_base) > 12:
                    # Return if too far
                    if self.bot.mineral_field:
                        self.bot.do(
                            worker.gather(self.bot.mineral_field.closest_to(main_base))
                        )
                    else:
                        self.bot.do(worker.move(main_base.position))
                    continue

                # Attack only if enemy is near (within 15)
                if (
                    worker.is_idle or worker.is_gathering
                ) and closest_enemy.distance_to(main_base) < 10:
                    self.bot.do(worker.attack(closest_enemy.position))

            logger.info(f"[FIGHT] Deployed {defending_workers} workers for defense!")

    def get_status(self) -> str:
        """
        Return current early defense status
        """
        if self.bot.time > self.early_game_threshold:
            return "Early Defense Complete"

        status_parts = []

        if self.emergency_mode:
            status_parts.append("[!] Emergency Mode")
        else:
            status_parts.append("[OK] Normal")

        if self.pool_started:
            status_parts.append("Pool: [OK]")
        else:
            status_parts.append("Pool: [X]")

        if self.queen_started:
            status_parts.append("Queen: [OK]")
        else:
            status_parts.append("Queen: [X]")

        ling_count = self.bot.units(UnitTypeId.ZERGLING).amount
        status_parts.append(f"Lings: {ling_count}")

        return " | ".join(status_parts)

    # =============================================
    # * FIX 4: Zergling Speed Upgrade ASAP *
    # =============================================
    async def _research_zergling_speed_early(self) -> None:
        """
        Research Metabolic Boost as soon as spawning pool + 100 gas is available.
        This makes early zerglings much more effective for defense.
        """
        if self._zergling_speed_researched:
            return

        # Check if already done or pending
        zergling_speed = getattr(UpgradeId, "ZERGLINGMOVEMENTSPEED", None)
        if not zergling_speed:
            return

        if hasattr(self.bot, "already_pending_upgrade"):
            if self.bot.already_pending_upgrade(zergling_speed) > 0:
                self._zergling_speed_researched = True
                return

        # Check if pool is ready and idle
        pools = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready
        if not pools.exists:
            return

        pool = pools.first
        if hasattr(pool, "is_idle") and not pool.is_idle:
            return

        # Need 100 gas
        if self.bot.vespene < 100:
            return

        # Research it
        try:
            self.bot.do(pool.research(zergling_speed))
            self._zergling_speed_researched = True
            logger.info(
                f"[*][*][*] Zergling Speed (Metabolic Boost) researched at {int(self.bot.time)}s! [*][*][*]"
            )
        except Exception as e:
            logger.error(f"Zergling speed research failed: {e}")

    # =============================================
    # * FIX 3: Early Spine Crawler (2 minutes) *
    # =============================================
    async def _build_early_spine_crawler(self) -> None:
        """
        Build a spine crawler near natural at 2 minutes for early defense.
        Spine crawler provides 25 DPS and 300 HP - crucial before roaches arrive.
        """
        # Already built or ordered
        if self._spine_crawler_built or self._spine_crawler_ordered:
            # Check if order completed
            spines = self.bot.structures(UnitTypeId.SPINECRAWLER)
            if spines.exists or self.bot.already_pending(UnitTypeId.SPINECRAWLER) > 0:
                self._spine_crawler_built = True
            return

        # Need spawning pool ready (spine crawler requires pool)
        if not self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready:
            return

        # Need resources (100 minerals)
        if self.bot.minerals < 100:
            return

        # Need workers
        if not self.bot.workers:
            return

        # Find location - near natural expansion or main base
        main_base = None
        if self.bot.townhalls:
            main_base = self.bot.townhalls.first
        if not main_base:
            return

        # Build between main and natural (defensive position)
        try:
            # Position towards map center (where enemies approach)
            build_pos = main_base.position.towards(self.bot.game_info.map_center, 8)

            tech_coordinator = getattr(self.bot, "tech_coordinator", None)
            if tech_coordinator:
                if not tech_coordinator.is_planned(UnitTypeId.SPINECRAWLER):
                    tech_coordinator.request_structure(
                        UnitTypeId.SPINECRAWLER,
                        build_pos,
                        80,  # High priority
                        "EarlyDefenseSystem",
                    )
                    self._spine_crawler_ordered = True
                    logger.info(
                        f"[*] Spine Crawler ordered at {int(self.bot.time)}s (early defense) [*]"
                    )
            else:
                location = await self.bot.find_placement(
                    UnitTypeId.SPINECRAWLER,
                    build_pos,
                    max_distance=10,
                    placement_step=2,
                )
                if location:
                    worker = self.bot.workers.closest_to(location)
                    if worker:
                        self.bot.do(worker.build(UnitTypeId.SPINECRAWLER, location))
                        self._spine_crawler_ordered = True
                        logger.info(
                            f"[*] Spine Crawler building at {int(self.bot.time)}s (early defense) [*]"
                        )
        except Exception as e:
            logger.error(f"Spine crawler build failed: {e}")

    # =============================================
    # * FIX 5: Worker Pull Defense *
    # =============================================
    async def _worker_pull_defense(self) -> None:
        """
        Pull 4-6 workers to fight when attacked early with more than 4 enemy units
        and we have fewer than 6 army units. Workers + zerglings can hold early rushes.
        """
        if not self.bot.townhalls:
            return
        main_base = self.bot.townhalls.first
        if not main_base:
            return

        # Count our army units (zerglings + queens + roaches)
        army_types = {UnitTypeId.ZERGLING, UnitTypeId.QUEEN, UnitTypeId.ROACH}
        our_army = 0
        for unit_type in army_types:
            our_army += self.bot.units(unit_type).amount

        # Count nearby enemies
        enemy_units = getattr(self.bot, "enemy_units", None)
        if not enemy_units:
            return
        nearby_enemies = enemy_units.closer_than(15, main_base.position)
        if not nearby_enemies:
            return

        enemy_count = nearby_enemies.amount

        # Only pull workers if:
        # - More than 3 enemy units nearby
        # - We have fewer than 6 army units
        # - We have workers to pull
        if enemy_count > 3 and our_army < 6 and self.bot.workers.amount > 6:
            # Pull 4-6 workers based on enemy count
            workers_to_pull = min(6, max(4, enemy_count))
            workers_to_pull = min(
                workers_to_pull, self.bot.workers.amount - 4
            )  # Keep at least 4 mining

            if workers_to_pull <= 0:
                return

            closest_enemy = nearby_enemies.closest_to(main_base)
            pulled = self.bot.workers.closest_n_units(
                closest_enemy.position, workers_to_pull
            )

            for worker in pulled:
                self.bot.do(worker.attack(closest_enemy.position))
                self._pulled_worker_tags.add(worker.tag)

            self._workers_pulled = True
            logger.info(
                f"[*] WORKER PULL: {workers_to_pull} workers defending vs {enemy_count} enemies! (army: {our_army}) [*]"
            )

    async def _return_pulled_workers(self) -> None:
        """
        Return pulled workers to mining after threat is gone.
        """
        if not self._pulled_worker_tags:
            self._workers_pulled = False
            return

        main_base = None
        if self.bot.townhalls:
            main_base = self.bot.townhalls.first
        if not main_base:
            self._workers_pulled = False
            self._pulled_worker_tags.clear()
            return

        returned = 0
        for worker in self.bot.workers:
            if worker.tag in self._pulled_worker_tags:
                if self.bot.mineral_field:
                    self.bot.do(
                        worker.gather(self.bot.mineral_field.closest_to(main_base))
                    )
                else:
                    self.bot.do(worker.move(main_base.position))
                returned += 1

        if returned > 0:
            logger.info(f"[*] {returned} workers returned to mining [*]")

        self._pulled_worker_tags.clear()
        self._workers_pulled = False
