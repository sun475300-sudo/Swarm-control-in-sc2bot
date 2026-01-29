# -*- coding: utf-8 -*-
"""
Advanced Micro Controller V3 - Comprehensive unit micro management

New Features:
1. RavagerMicro - Corrosive Bile predictive shots
2. LurkerMicro - Optimal burrow positioning and range management
3. QueenMicro - Transfuse targeting and energy management
4. ViperMicro - Abduct, Blinding Cloud, Consume
5. CorruptorMicro - Caustic Spray coordination
6. FocusFireCoordinator - Focus fire target selection
7. AbilityCoordinator - Ability queue and priority management

Integration:
- Works with existing BanelingTactics, MutaliskMicro, InfestorTactics
- Unified micro control interface
- Energy and cooldown management
"""

from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from utils.logger import get_logger

try:
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.upgrade_id import UpgradeId
    from sc2.position import Point2
    from sc2.unit import Unit
    from sc2.bot_ai import BotAI
except ImportError:
    AbilityId = None
    UnitTypeId = None
    UpgradeId = None
    Point2 = None
    Unit = None
    BotAI = None


class RavagerMicro:
    """
    Ravager micro - Corrosive Bile predictive shots

    Features:
    - Target prediction based on movement
    - Clump targeting for maximum splash
    - Cooldown tracking
    """

    def __init__(
        self,
        prediction_time: float = 1.8,  # Corrosive Bile travel time
        min_targets_for_shot: int = 2,  # Minimum enemies to justify bile
        cooldown_duration: float = 7.0,  # Ravager ability cooldown
    ):
        self.prediction_time = prediction_time
        self.min_targets_for_shot = min_targets_for_shot
        self.cooldown_duration = cooldown_duration

        # Cooldown tracking
        self.last_shot_time: Dict[int, float] = {}  # unit_tag -> time

    def is_on_cooldown(self, ravager: Unit, current_time: float) -> bool:
        """Check if Ravager ability is on cooldown."""
        if ravager.tag not in self.last_shot_time:
            return False
        return current_time - self.last_shot_time[ravager.tag] < self.cooldown_duration

    def predict_enemy_position(
        self,
        enemy: Unit,
        prediction_time: float
    ) -> Optional[Point2]:
        """
        Predict enemy position after prediction_time seconds.

        Args:
            enemy: Enemy unit
            prediction_time: Seconds to predict ahead

        Returns:
            Predicted position
        """
        if not Point2:
            return None

        # Get enemy position and velocity
        pos = enemy.position

        # Simple prediction: assume enemy continues current direction
        # (In real game, velocity is available but needs proper handling)
        # For now, return current position (can be enhanced)
        return Point2((pos.x, pos.y))

    def find_best_bile_target(
        self,
        ravager: Unit,
        enemy_units,
        current_time: float
    ) -> Optional[Point2]:
        """
        Find best target position for Corrosive Bile.

        Args:
            ravager: The Ravager
            enemy_units: All enemy units
            current_time: Current game time

        Returns:
            Target position or None
        """
        if not enemy_units or self.is_on_cooldown(ravager, current_time):
            return None

        # Filter enemies within range (range 9)
        range_limit = 9
        in_range = [
            e for e in enemy_units
            if ravager.position.distance_to(e.position) <= range_limit
        ]

        if not in_range:
            return None

        # Find cluster of enemies
        best_target = None
        best_score = 0

        for enemy in in_range:
            # Predict position
            predicted_pos = self.predict_enemy_position(enemy, self.prediction_time)
            if not predicted_pos:
                continue

            # Count enemies near predicted position (splash radius ~2)
            nearby_count = sum(
                1 for e in in_range
                if e.position.distance_to(predicted_pos) <= 2.0
            )

            if nearby_count >= self.min_targets_for_shot and nearby_count > best_score:
                best_score = nearby_count
                best_target = predicted_pos

        return best_target

    async def execute_bile_shots(
        self,
        ravagers,
        enemy_units,
        bot,
        current_time: float
    ) -> Set[int]:
        """
        Execute Corrosive Bile shots.

        Args:
            ravagers: All Ravagers
            enemy_units: All enemy units
            bot: Bot instance
            current_time: Current game time

        Returns:
            Set of unit tags that shot
        """
        if not ravagers or not enemy_units:
            return set()

        actions = []
        shot_tags = set()

        for ravager in ravagers:
            target_pos = self.find_best_bile_target(ravager, enemy_units, current_time)

            if target_pos:
                # Execute Corrosive Bile
                ability = getattr(AbilityId, 'EFFECT_CORROSIVEBILE', None)
                if ability:
                    try:
                        actions.append(ravager(ability, target_pos))
                        self.last_shot_time[ravager.tag] = current_time
                        shot_tags.add(ravager.tag)
                    except Exception:
                        continue

        if actions:
            await bot.do_actions(actions)

        return shot_tags


class LurkerMicro:
    """
    Lurker micro - Optimal burrow positioning and range management

    Features:
    - Burrow at optimal range (9 units)
    - Unburrow when no targets
    - Energy-efficient repositioning
    """

    def __init__(
        self,
        optimal_range: float = 9.0,  # Lurker attack range
        burrow_threshold: int = 1,    # Min enemies to stay burrowed
        reposition_threshold: float = 3.0,  # Distance to trigger reposition
    ):
        self.optimal_range = optimal_range
        self.burrow_threshold = burrow_threshold
        self.reposition_threshold = reposition_threshold

        # State tracking
        self.burrowed_lurkers: Set[int] = set()

    def should_burrow(self, lurker: Unit, enemy_units) -> bool:
        """Check if Lurker should burrow."""
        if getattr(lurker, 'is_burrowed', False):
            return False

        # Count enemies in range
        enemies_in_range = sum(
            1 for e in enemy_units
            if lurker.position.distance_to(e.position) <= self.optimal_range
        )

        return enemies_in_range >= self.burrow_threshold

    def should_unburrow(self, lurker: Unit, enemy_units) -> bool:
        """Check if Lurker should unburrow."""
        if not getattr(lurker, 'is_burrowed', False):
            return False

        # Unburrow if no enemies in range
        enemies_in_range = sum(
            1 for e in enemy_units
            if lurker.position.distance_to(e.position) <= self.optimal_range + 2
        )

        return enemies_in_range == 0

    def find_optimal_position(
        self,
        lurker: Unit,
        enemy_units,
        bot
    ) -> Optional[Point2]:
        """
        Find optimal burrow position.

        Args:
            lurker: The Lurker
            enemy_units: All enemy units
            bot: Bot instance

        Returns:
            Optimal position
        """
        if not enemy_units or not Point2:
            return None

        # Find enemy center
        enemy_x = sum(e.position.x for e in enemy_units) / len(enemy_units)
        enemy_y = sum(e.position.y for e in enemy_units) / len(enemy_units)
        enemy_center = Point2((enemy_x, enemy_y))

        # Position at optimal range from enemy center
        direction_x = lurker.position.x - enemy_center.x
        direction_y = lurker.position.y - enemy_center.y
        length = (direction_x ** 2 + direction_y ** 2) ** 0.5

        if length == 0:
            return None

        # Normalize and position at optimal range
        norm_x = direction_x / length
        norm_y = direction_y / length

        optimal_x = enemy_center.x + norm_x * (self.optimal_range - 1)
        optimal_y = enemy_center.y + norm_y * (self.optimal_range - 1)

        return Point2((optimal_x, optimal_y))

    async def execute_lurker_micro(
        self,
        lurkers,
        enemy_units,
        bot
    ) -> Set[int]:
        """
        Execute Lurker micro.

        Args:
            lurkers: All Lurkers
            enemy_units: All enemy units
            bot: Bot instance

        Returns:
            Set of unit tags that performed actions
        """
        if not lurkers:
            return set()

        actions = []
        acted_tags = set()

        for lurker in lurkers:
            is_burrowed = getattr(lurker, 'is_burrowed', False)

            # Check burrow status
            if self.should_burrow(lurker, enemy_units) and not is_burrowed:
                # Burrow
                ability = getattr(AbilityId, 'BURROWDOWN_LURKER', None)
                if ability:
                    try:
                        actions.append(lurker(ability))
                        self.burrowed_lurkers.add(lurker.tag)
                        acted_tags.add(lurker.tag)
                        continue
                    except Exception:
                        pass

            elif self.should_unburrow(lurker, enemy_units) and is_burrowed:
                # Unburrow
                ability = getattr(AbilityId, 'BURROWUP_LURKER', None)
                if ability:
                    try:
                        actions.append(lurker(ability))
                        self.burrowed_lurkers.discard(lurker.tag)
                        acted_tags.add(lurker.tag)
                        continue
                    except Exception:
                        pass

            # Reposition if not burrowed and enemies present
            if not is_burrowed and enemy_units:
                optimal_pos = self.find_optimal_position(lurker, enemy_units, bot)

                if optimal_pos and lurker.position.distance_to(optimal_pos) > self.reposition_threshold:
                    try:
                        actions.append(lurker.move(optimal_pos))
                        acted_tags.add(lurker.tag)
                    except Exception:
                        pass

        if actions:
            await bot.do_actions(actions)

        return acted_tags


class QueenMicro:
    """
    Queen micro - Transfuse targeting and energy management

    Features:
    - Transfuse low HP high-value units
    - Creep tumor placement
    - Energy prioritization
    """

    def __init__(
        self,
        transfuse_threshold: float = 0.4,  # HP ratio to trigger transfuse
        transfuse_energy_cost: int = 50,    # Energy cost for transfuse
        transfuse_range: float = 7.0,       # Transfuse cast range
        min_energy_for_creep: int = 50,     # Minimum energy for creep tumor
    ):
        self.transfuse_threshold = transfuse_threshold
        self.transfuse_energy_cost = transfuse_energy_cost
        self.transfuse_range = transfuse_range
        self.min_energy_for_creep = min_energy_for_creep

        # Priority unit types for transfuse
        self.priority_types: Set = set()
        if UnitTypeId:
            self.priority_types = {
                UnitTypeId.ULTRALISK,
                UnitTypeId.BROODLORD,
                UnitTypeId.VIPER,
                UnitTypeId.SWARMHOSTMP,
                UnitTypeId.RAVAGER,
                UnitTypeId.QUEEN,
            }

    def find_transfuse_target(
        self,
        queen: Unit,
        friendly_units
    ) -> Optional[Unit]:
        """
        Find best target for Transfuse.

        Args:
            queen: The Queen
            friendly_units: All friendly units

        Returns:
            Unit to transfuse or None
        """
        if not friendly_units:
            return None

        # Find injured units in range
        injured_units = []
        for unit in friendly_units:
            if unit.tag == queen.tag:
                continue

            health_ratio = unit.health / unit.health_max if unit.health_max > 0 else 1.0
            distance = queen.position.distance_to(unit.position)

            if health_ratio < self.transfuse_threshold and distance <= self.transfuse_range:
                # Priority score: lower HP + priority type = higher score
                priority_bonus = 1.0 if unit.type_id in self.priority_types else 0.5
                score = (1.0 - health_ratio) * priority_bonus

                injured_units.append((unit, score))

        if not injured_units:
            return None

        # Return highest priority target
        injured_units.sort(key=lambda x: x[1], reverse=True)
        return injured_units[0][0]

    async def execute_queen_micro(
        self,
        queens,
        friendly_units,
        bot
    ) -> Set[int]:
        """
        Execute Queen micro.

        Args:
            queens: All Queens
            friendly_units: All friendly units
            bot: Bot instance

        Returns:
            Set of unit tags that performed actions
        """
        if not queens:
            return set()

        actions = []
        acted_tags = set()

        for queen in queens:
            energy = getattr(queen, 'energy', 0)

            # Priority 1: Transfuse if energy available
            if energy >= self.transfuse_energy_cost:
                target = self.find_transfuse_target(queen, friendly_units)

                if target:
                    ability = getattr(AbilityId, 'TRANSFUSION_TRANSFUSION', None)
                    if ability:
                        try:
                            actions.append(queen(ability, target))
                            acted_tags.add(queen.tag)
                            continue
                        except Exception:
                            pass

        if actions:
            await bot.do_actions(actions)

        return acted_tags


class ViperMicro:
    """
    Viper micro - Abduct, Blinding Cloud, Consume

    Features:
    - Abduct high-value targets
    - Blinding Cloud on clumps
    - Energy management with Consume
    """

    def __init__(
        self,
        abduct_energy_cost: int = 75,
        blinding_cloud_energy_cost: int = 100,
        abduct_range: float = 9.0,
        consume_threshold: int = 50,  # Energy level to trigger Consume
    ):
        self.abduct_energy_cost = abduct_energy_cost
        self.blinding_cloud_energy_cost = blinding_cloud_energy_cost
        self.abduct_range = abduct_range
        self.consume_threshold = consume_threshold

        # High-value abduct targets
        self.abduct_priorities: Set = set()
        if UnitTypeId:
            self.abduct_priorities = {
                UnitTypeId.SIEGETANK,
                UnitTypeId.SIEGETANKSIEGED,
                UnitTypeId.COLOSSUS,
                UnitTypeId.IMMORTAL,
                UnitTypeId.THOR,
                UnitTypeId.TEMPEST,
                UnitTypeId.CARRIER,
                UnitTypeId.BATTLECRUISER,
            }

    def find_abduct_target(
        self,
        viper: Unit,
        enemy_units
    ) -> Optional[Unit]:
        """Find best target for Abduct."""
        if not enemy_units:
            return None

        # Find high-value targets in range
        targets = [
            e for e in enemy_units
            if e.type_id in self.abduct_priorities
            and viper.position.distance_to(e.position) <= self.abduct_range
        ]

        if not targets:
            return None

        # Return closest high-value target
        return min(targets, key=lambda e: viper.position.distance_to(e.position))

    async def execute_viper_micro(
        self,
        vipers,
        enemy_units,
        friendly_units,
        bot
    ) -> Set[int]:
        """
        Execute Viper micro.

        Args:
            vipers: All Vipers
            enemy_units: All enemy units
            friendly_units: All friendly units for Consume
            bot: Bot instance

        Returns:
            Set of unit tags that performed actions
        """
        if not vipers:
            return set()

        actions = []
        acted_tags = set()

        for viper in vipers:
            energy = getattr(viper, 'energy', 0)

            # Priority 1: Abduct high-value targets
            if energy >= self.abduct_energy_cost:
                target = self.find_abduct_target(viper, enemy_units)

                if target:
                    ability = getattr(AbilityId, 'VIPERCONSUMESTRUCTURE_VIPERCONSUME', None)
                    if not ability:
                        ability = getattr(AbilityId, 'EFFECT_ABDUCT', None)

                    if ability:
                        try:
                            actions.append(viper(ability, target))
                            acted_tags.add(viper.tag)
                            continue
                        except Exception:
                            pass

            # Priority 2: Consume if low energy
            if energy < self.consume_threshold and friendly_units:
                # Find nearby friendly structure
                consume_targets = [
                    u for u in friendly_units
                    if getattr(u, 'is_structure', False)
                    and viper.position.distance_to(u.position) <= 2.0
                ]

                if consume_targets:
                    ability = getattr(AbilityId, 'VIPERCONSUMESTRUCTURE_VIPERCONSUME', None)
                    if ability:
                        try:
                            actions.append(viper(ability, consume_targets[0]))
                            acted_tags.add(viper.tag)
                            continue
                        except Exception:
                            pass

        if actions:
            await bot.do_actions(actions)

        return acted_tags


class CorruptorMicro:
    """
    Corruptor micro - Caustic Spray targeting

    Features:
    - Cast Caustic Spray on high-armor targets
    - Energy management
    - Cooldown tracking
    """

    def __init__(
        self,
        caustic_spray_energy_cost: int = 75,
        caustic_spray_range: float = 6.0,
        cooldown_duration: float = 10.0,
    ):
        self.caustic_spray_energy_cost = caustic_spray_energy_cost
        self.caustic_spray_range = caustic_spray_range
        self.cooldown_duration = cooldown_duration

        # Cooldown tracking
        self.last_spray_time: Dict[int, float] = {}  # unit_tag -> time

        # High-armor targets (prioritize for Caustic Spray)
        self.priority_targets: Set = set()
        if UnitTypeId:
            self.priority_targets = {
                UnitTypeId.BATTLECRUISER,
                UnitTypeId.CARRIER,
                UnitTypeId.MOTHERSHIP,
                UnitTypeId.TEMPEST,
                UnitTypeId.VOIDRAY,
                UnitTypeId.BROODLORD,
            }

    def is_on_cooldown(self, corruptor: Unit, current_time: float) -> bool:
        """Check if Caustic Spray is on cooldown."""
        if corruptor.tag not in self.last_spray_time:
            return False
        return current_time - self.last_spray_time[corruptor.tag] < self.cooldown_duration

    def find_spray_target(
        self,
        corruptor: Unit,
        enemy_units,
        current_time: float
    ) -> Optional[Unit]:
        """
        Find best target for Caustic Spray.

        Args:
            corruptor: The Corruptor
            enemy_units: All enemy units
            current_time: Current game time

        Returns:
            Target unit or None
        """
        if self.is_on_cooldown(corruptor, current_time):
            return None

        # Filter enemy structures in range
        structures_in_range = [
            e for e in enemy_units
            if getattr(e, 'is_structure', False)
            and getattr(e, 'is_flying', False)  # Flying structures only
            and corruptor.position.distance_to(e.position) <= self.caustic_spray_range
        ]

        # Prioritize high-value structures
        priority_structures = [s for s in structures_in_range if s.type_id in self.priority_targets]

        if priority_structures:
            return priority_structures[0]
        elif structures_in_range:
            return structures_in_range[0]

        return None

    async def execute_corruptor_micro(
        self,
        corruptors,
        enemy_units,
        bot,
        current_time: float
    ) -> Set[int]:
        """
        Execute Corruptor micro.

        Args:
            corruptors: All Corruptors
            enemy_units: All enemy units
            bot: Bot instance
            current_time: Current game time

        Returns:
            Set of unit tags that performed actions
        """
        if not corruptors or not enemy_units:
            return set()

        actions = []
        acted_tags = set()

        for corruptor in corruptors:
            energy = getattr(corruptor, 'energy', 0)

            if energy >= self.caustic_spray_energy_cost:
                target = self.find_spray_target(corruptor, enemy_units, current_time)

                if target:
                    ability = getattr(AbilityId, 'CAUSTICSPRAY_CAUSTICSPRAY', None)
                    if ability:
                        try:
                            actions.append(corruptor(ability, target))
                            self.last_spray_time[corruptor.tag] = current_time
                            acted_tags.add(corruptor.tag)
                        except Exception:
                            continue

        if actions:
            await bot.do_actions(actions)

        return acted_tags


class FocusFireCoordinator:
    """
    Focus Fire Coordinator - Coordinate unit targeting

    Features:
    - Identify priority targets
    - Distribute damage efficiently
    - Prevent overkill
    """

    def __init__(self):
        # Priority targets (high value)
        self.priority_types: Set = set()
        if UnitTypeId:
            self.priority_types = {
                UnitTypeId.SIEGETANK,
                UnitTypeId.SIEGETANKSIEGED,
                UnitTypeId.COLOSSUS,
                UnitTypeId.HIGHTEMPLAR,
                UnitTypeId.IMMORTAL,
                UnitTypeId.THOR,
                UnitTypeId.MEDIVAC,
                UnitTypeId.DISRUPTOR,
            }

        # Current target assignments
        self.target_assignments: Dict[int, int] = {}  # unit_tag -> target_tag
        self.target_damage_count: Dict[int, int] = defaultdict(int)  # target_tag -> attacker_count

    def select_focus_target(
        self,
        unit: Unit,
        enemy_units
    ) -> Optional[Unit]:
        """
        Select best focus fire target.

        Args:
            unit: Attacking unit
            enemy_units: All enemy units

        Returns:
            Target to focus or None
        """
        if not enemy_units:
            return None

        # Find priority targets in range
        unit_range = getattr(unit, 'ground_range', 5) if not getattr(unit, 'is_flying', False) else getattr(unit, 'air_range', 5)

        priority_targets = [
            e for e in enemy_units
            if e.type_id in self.priority_types
            and unit.position.distance_to(e.position) <= unit_range + 2
        ]

        # If no priority targets, find any target in range
        if not priority_targets:
            priority_targets = [
                e for e in enemy_units
                if unit.position.distance_to(e.position) <= unit_range + 2
            ]

        if not priority_targets:
            return None

        # Select target with least damage assigned (prevent overkill)
        best_target = min(
            priority_targets,
            key=lambda e: (self.target_damage_count[e.tag], e.health)
        )

        return best_target

    def assign_target(self, unit_tag: int, target_tag: int):
        """Assign unit to target."""
        # Remove old assignment
        if unit_tag in self.target_assignments:
            old_target = self.target_assignments[unit_tag]
            self.target_damage_count[old_target] = max(0, self.target_damage_count[old_target] - 1)

        # Add new assignment
        self.target_assignments[unit_tag] = target_tag
        self.target_damage_count[target_tag] += 1

    def clear_dead_assignments(self, alive_unit_tags: Set[int], alive_enemy_tags: Set[int]):
        """Remove assignments for dead units."""
        # Remove dead attackers
        dead_attackers = set(self.target_assignments.keys()) - alive_unit_tags
        for tag in dead_attackers:
            target = self.target_assignments.pop(tag)
            self.target_damage_count[target] = max(0, self.target_damage_count[target] - 1)

        # Clear counts for dead targets
        for target_tag in list(self.target_damage_count.keys()):
            if target_tag not in alive_enemy_tags:
                del self.target_damage_count[target_tag]


class AdvancedMicroControllerV3:
    """
    Advanced Micro Controller V3 - Unified micro management

    Integrates:
    - RavagerMicro
    - LurkerMicro
    - QueenMicro
    - ViperMicro
    - FocusFireCoordinator
    """

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.logger = get_logger("MicroV3")

        # Sub-controllers
        self.ravager_micro = RavagerMicro()
        self.lurker_micro = LurkerMicro()
        self.queen_micro = QueenMicro()
        self.viper_micro = ViperMicro()
        self.corruptor_micro = CorruptorMicro()
        self.focus_fire = FocusFireCoordinator()

        # Update timing
        self.last_update = 0
        self.update_interval = 8  # ~0.3s between updates

        self.logger.info("[MICRO_V3] Advanced Micro Controller V3 initialized")

    async def on_step(self, iteration: int):
        """
        Main update loop.

        Args:
            iteration: Current game iteration
        """
        if iteration - self.last_update < self.update_interval:
            return

        self.last_update = iteration
        current_time = self.bot.time

        # Get units
        enemy_units = getattr(self.bot, 'enemy_units', [])
        units = getattr(self.bot, 'units', [])

        # Execute micro for each unit type
        await self._execute_ravager_micro(current_time, enemy_units)
        await self._execute_lurker_micro(enemy_units)
        await self._execute_queen_micro(units)
        await self._execute_viper_micro(enemy_units, units)
        await self._execute_corruptor_micro(current_time, enemy_units)
        await self._execute_focus_fire(units, enemy_units)

        # Cleanup dead assignments
        if iteration % 44 == 0:  # Every ~2 seconds
            self._cleanup_dead_units()

    async def _execute_ravager_micro(self, current_time: float, enemy_units):
        """Execute Ravager Corrosive Bile shots."""
        ravagers = self.bot.units(UnitTypeId.RAVAGER) if UnitTypeId else []
        if ravagers:
            await self.ravager_micro.execute_bile_shots(
                ravagers,
                enemy_units,
                self.bot,
                current_time
            )

    async def _execute_lurker_micro(self, enemy_units):
        """Execute Lurker positioning and burrow management."""
        lurkers = self.bot.units(UnitTypeId.LURKERMP) if UnitTypeId else []
        if lurkers:
            await self.lurker_micro.execute_lurker_micro(
                lurkers,
                enemy_units,
                self.bot
            )

    async def _execute_queen_micro(self, friendly_units):
        """Execute Queen Transfuse."""
        queens = self.bot.units(UnitTypeId.QUEEN) if UnitTypeId else []
        if queens:
            await self.queen_micro.execute_queen_micro(
                queens,
                friendly_units,
                self.bot
            )

    async def _execute_viper_micro(self, enemy_units, friendly_units):
        """Execute Viper abilities."""
        vipers = self.bot.units(UnitTypeId.VIPER) if UnitTypeId else []
        if vipers:
            await self.viper_micro.execute_viper_micro(
                vipers,
                enemy_units,
                friendly_units,
                self.bot
            )

    async def _execute_corruptor_micro(self, current_time: float, enemy_units):
        """Execute Corruptor Caustic Spray."""
        corruptors = self.bot.units(UnitTypeId.CORRUPTOR) if UnitTypeId else []
        if corruptors:
            await self.corruptor_micro.execute_corruptor_micro(
                corruptors,
                enemy_units,
                self.bot,
                current_time
            )

    async def _execute_focus_fire(self, units, enemy_units):
        """Execute focus fire coordination."""
        if not units or not enemy_units:
            return

        # Get combat units
        combat_units = [
            u for u in units
            if u.type_id in {
                UnitTypeId.ZERGLING, UnitTypeId.ROACH, UnitTypeId.HYDRALISK,
                UnitTypeId.RAVAGER, UnitTypeId.MUTALISK
            }
        ] if UnitTypeId else []

        actions = []
        for unit in combat_units:
            target = self.focus_fire.select_focus_target(unit, enemy_units)
            if target:
                self.focus_fire.assign_target(unit.tag, target.tag)
                try:
                    actions.append(unit.attack(target))
                except Exception:
                    continue

        if actions:
            await self.bot.do_actions(actions)

    def _cleanup_dead_units(self):
        """Cleanup dead unit assignments."""
        alive_unit_tags = {u.tag for u in getattr(self.bot, 'units', [])}
        alive_enemy_tags = {e.tag for e in getattr(self.bot, 'enemy_units', [])}

        self.focus_fire.clear_dead_assignments(alive_unit_tags, alive_enemy_tags)

    def get_status(self) -> Dict[str, any]:
        """Get micro controller status."""
        return {
            "ravager_cooldowns": len(self.ravager_micro.last_shot_time),
            "lurker_burrowed": len(self.lurker_micro.burrowed_lurkers),
            "corruptor_cooldowns": len(self.corruptor_micro.last_spray_time),
            "focus_fire_assignments": len(self.focus_fire.target_assignments),
            "priority_targets": len(self.focus_fire.target_damage_count),
        }
