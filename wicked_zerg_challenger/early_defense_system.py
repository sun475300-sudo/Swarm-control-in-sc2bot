"""
Early Defense System

Purpose: Counter early rushes and improve initial survival rate
- Maximize survival rate between 1-3 minutes
- Detect early rushes and respond immediately
- Manage initial unit production priority
"""

from typing import Optional, Set
try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
    from sc2.position import Point2
except ImportError:
    class BotAI:
        pass
    class UnitTypeId:
        pass
    class AbilityId:
        pass
    class Point2:
        pass


class EarlyDefenseSystem:
    """
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
        self.early_game_threshold = 180.0  # 3 minutes = 180 seconds
        self.early_rush_detected = False
        self.pool_started = False
        self.queen_started = False
        self.emergency_mode = False
        self.last_enemy_check = 0

        # Early threat detection
        self.early_threats: Set = set()

    async def execute(self, iteration: int) -> None:
        """
        Execute early defense logic every step
        """
        # Disable early defense after 3 minutes
        if self.bot.time > self.early_game_threshold:
            return

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
        if not self.queen_started and self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready:
            await self._produce_first_queen()

        # 5. Emergency defense mode (If enemy detected)
        if self.emergency_mode or self.early_threats:
            await self._emergency_defense()

    async def _detect_early_threats(self) -> None:
        """
        Detect early enemy units and alert
        """
        # Check if enemy units are near our base
        if not self.bot.enemy_units:
            return

        main_base = self.bot.townhalls.first if self.bot.townhalls else None
        if not main_base:
            return

        # Check for enemies within 20 distance of main base
        nearby_enemies = self.bot.enemy_units.closer_than(20, main_base.position)

        if nearby_enemies:
            self.early_rush_detected = True
            self.emergency_mode = True
            self.early_threats = set(nearby_enemies.tags)

            print(f"[EARLY_DEFENSE] [WARNING] Early rush detected! {nearby_enemies.amount} enemies found (Game Time: {int(self.bot.time)}s)")
            print(f"[EARLY_DEFENSE] Emergency Defense Mode ACTIVATED!")

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
            if tech_coordinator and not tech_coordinator.is_planned(UnitTypeId.SPAWNINGPOOL):
                target_pos = main_base.position.towards(self.bot.game_info.map_center, 5)
                PRIORITY_DEFENSE = 85  # High priority for early defense
                tech_coordinator.request_structure(
                    UnitTypeId.SPAWNINGPOOL,
                    target_pos,
                    PRIORITY_DEFENSE,
                    "EarlyDefenseSystem"
                )
                self.pool_started = True
                print(f"[EARLY_DEFENSE] [OK] Spawning Pool requested via TechCoordinator (Game Time: {int(self.bot.time)}s)")
            elif not tech_coordinator:
                print(f"[EARLY_DEFENSE] [WARNING] TechCoordinator not available")
        except Exception as e:
            print(f"[EARLY_DEFENSE] Failed to request Pool construction: {e}")

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
            (target_zerglings - current_zerglings - pending_zerglings + 1) // 2,  # 2 per egg
            self.bot.minerals // 50
        )

        for larva in self.bot.larva[:larvae_for_lings]:
            if self.bot.minerals >= 50:
                larva.train(UnitTypeId.ZERGLING)

        if larvae_for_lings > 0:
            print(f"[EARLY_DEFENSE] Producing {larvae_for_lings * 2} Zerglings (Target: {target_zerglings})")

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
                hatchery.train(UnitTypeId.QUEEN)
                self.queen_started = True
                print(f"[EARLY_DEFENSE] [OK] Started First Queen Production (Game Time: {int(self.bot.time)}s)")
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
            print(f"[EARLY_DEFENSE] Early threat cleared. Returning to normal mode.")
            return

        # Closest enemy
        closest_enemy = enemy_units.closest_to(main_base)

        # All Zerglings defend
        zerglings = self.bot.units(UnitTypeId.ZERGLING)
        if zerglings:
            for ling in zerglings:
                if ling.is_idle or ling.is_moving:
                    ling.attack(closest_enemy.position)

        # Worker Defense (Only if enemy is very close)
        if closest_enemy.distance_to(main_base) < 10:
            defending_workers = min(6, len(self.bot.workers))  # Max 6 workers
            workers_to_defend = self.bot.workers.closest_n_units(closest_enemy.position, defending_workers)

            for worker in workers_to_defend:
                # ★ CRITICAL: Ensure workers don't go further than 12 distance from base ★
                if worker.distance_to(main_base) > 12:
                    # Return if too far
                    worker.gather(self.bot.mineral_field.closest_to(main_base))
                    continue

                # Attack only if enemy is near (within 15)
                if (worker.is_idle or worker.is_gathering) and closest_enemy.distance_to(main_base) < 10:
                    worker.attack(closest_enemy.position)

            print(f"[EARLY_DEFENSE] ⚔️ Deployed {defending_workers} workers for defense!")

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
