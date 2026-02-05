"""
Queen Transfusion Manager - Smart Priority-Based Healing System

Provides intelligent transfusion targeting for queens, prioritizing high-value units
and optimizing healing efficiency in combat situations.
"""

from typing import TYPE_CHECKING, Dict, Optional
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.units import Units
from sc2.unit import Unit

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI

from wicked_zerg_challenger.utils.logger import get_logger


class QueenTransfusionManager:
    """Smart Transfusion system with priority targeting"""

    # Priority map (higher = more important to heal)
    # Prioritizes units by cost and strategic value
    HEAL_PRIORITY: Dict[UnitTypeId, int] = {
        UnitTypeId.ULTRALISK: 100,      # 300M/200G - Most expensive ground unit
        UnitTypeId.BROODLORD: 90,       # 150M/150G/2S - Critical air support
        UnitTypeId.VIPER: 85,           # 100M/200G/3S - Spellcaster, high value
        UnitTypeId.SWARMHOSTMP: 80,     # 100M/75G - Locust spawner
        UnitTypeId.RAVAGER: 75,         # 100M/75G - Important siege unit
        UnitTypeId.LURKERMP: 70,        # 50M/100G/1S - Hidden damage dealer
        UnitTypeId.ROACH: 65,           # 75M/25G - Core army unit
        UnitTypeId.HYDRALISK: 60,       # 100M/50G - Anti-air backbone
        UnitTypeId.QUEEN: 55,           # 150M - Other queens (preserve macro)
        UnitTypeId.MUTALISK: 50,        # 100M/100G - Harassment unit
        UnitTypeId.CORRUPTOR: 50,       # 150M/100G - Air superiority
        UnitTypeId.INFESTOR: 45,        # 100M/150G - Spellcaster (but fragile)
        UnitTypeId.ZERGLING: 30,        # 25M - Cheap, easily replaced
    }

    # Units that cannot be healed (suicide units, temporary, etc.)
    CANNOT_HEAL = {
        UnitTypeId.BANELING,            # Suicide unit
        UnitTypeId.BANELINGCOCOON,      # Morphing state
        UnitTypeId.BROODLING,           # Temporary unit (timed life)
        UnitTypeId.LOCUSTMP,            # Locust (temporary)
        UnitTypeId.LOCUSTMPFLYING,      # Flying locust (temporary)
        UnitTypeId.CHANGELING,          # Scout (expendable)
        UnitTypeId.CHANGELINGMARINE,    # Changeling form
        UnitTypeId.CHANGELINGZEALOT,    # Changeling form
        UnitTypeId.CHANGELINGZERGLING,  # Changeling form
        UnitTypeId.EGG,                 # Not a combat unit
        UnitTypeId.LARVA,               # Not a combat unit
        UnitTypeId.OVERLORD,            # No combat value (unless carrying)
        UnitTypeId.OVERSEER,            # Detector, but low priority
    }

    # Transfusion ability constants
    TRANSFUSION_ENERGY_COST = 50
    TRANSFUSION_RANGE = 7
    TRANSFUSION_HP_THRESHOLD = 0.6   # Heal units below 60% HP
    TRANSFUSION_CRITICAL_HP = 0.3    # Critical health (prioritize further)
    TRANSFUSION_HP_RESTORE = 125     # HP restored by transfusion

    def __init__(self, bot: "BotAI"):
        self.bot = bot
        self.logger = get_logger("TransfusionManager")

        # Statistics tracking
        self.transfusions_performed = 0
        self.transfusions_per_unit_type: Dict[UnitTypeId, int] = {}
        self.hp_healed_total = 0

    async def execute_transfusions(self, queens: Units, damaged_units: Units, iteration: int) -> None:
        """
        Execute smart transfusions on priority targets

        Args:
            queens: Available queens with energy
            damaged_units: Friendly units that are damaged
            iteration: Current game iteration
        """
        if not queens or not damaged_units:
            return

        # Filter queens with sufficient energy
        available_queens = queens.filter(
            lambda q: q.energy >= self.TRANSFUSION_ENERGY_COST and q.is_idle
        )

        if not available_queens:
            return

        # Perform transfusions
        for queen in available_queens:
            target = self._find_best_transfusion_target(queen, damaged_units)

            if target:
                # Execute transfusion
                self.bot.do(queen(AbilityId.TRANSFUSION_TRANSFUSION, target))

                # Track statistics
                self._record_transfusion(target)

                # Log significant transfusions (high-value units or critical HP)
                if target.health_percentage < self.TRANSFUSION_CRITICAL_HP or \
                   self.HEAL_PRIORITY.get(target.type_id, 0) >= 70:
                    self.logger.info(
                        f"[{int(self.bot.time)}s] Transfusion: {target.type_id.name} "
                        f"at {target.health_percentage:.0%} HP "
                        f"(Priority: {self.HEAL_PRIORITY.get(target.type_id, 0)})"
                    )

    def _find_best_transfusion_target(self, queen: Unit, damaged_units: Units) -> Optional[Unit]:
        """
        Find the best target for transfusion based on priority, health, and range

        Args:
            queen: The queen performing the transfusion
            damaged_units: Pool of damaged friendly units

        Returns:
            Best unit to heal, or None if no valid target
        """
        # Filter valid targets
        valid_targets = [
            u for u in damaged_units
            if self._is_valid_transfusion_target(u, queen)
        ]

        if not valid_targets:
            return None

        # Sort by priority (desc), critical health status, then health percentage (asc)
        valid_targets.sort(
            key=lambda u: (
                -self.HEAL_PRIORITY.get(u.type_id, 0),           # Higher priority first
                -int(u.health_percentage < self.TRANSFUSION_CRITICAL_HP),  # Critical HP first
                u.health_percentage                               # Lower HP first
            )
        )

        return valid_targets[0]

    def _is_valid_transfusion_target(self, unit: Unit, queen: Unit) -> bool:
        """
        Check if a unit is a valid transfusion target

        Args:
            unit: Potential heal target
            queen: Queen performing transfusion

        Returns:
            True if valid target, False otherwise
        """
        # Cannot heal blacklisted units
        if unit.type_id in self.CANNOT_HEAL:
            return False

        # Must be damaged enough to warrant healing
        if unit.health_percentage >= self.TRANSFUSION_HP_THRESHOLD:
            return False

        # Must be biological
        if not unit.is_biological:
            return False

        # Must be alive and not morphing
        if not unit.is_ready:
            return False

        # Must be within range
        if queen.distance_to(unit) > self.TRANSFUSION_RANGE:
            return False

        # Don't overheal - check if transfusion would be wasted
        hp_missing = unit.health_max - unit.health
        if hp_missing < self.TRANSFUSION_HP_RESTORE * 0.5:  # Don't heal if <50% effectiveness
            return False

        return True

    def _record_transfusion(self, target: Unit) -> None:
        """Record transfusion statistics"""
        self.transfusions_performed += 1

        unit_type = target.type_id
        self.transfusions_per_unit_type[unit_type] = \
            self.transfusions_per_unit_type.get(unit_type, 0) + 1

        # Estimate HP healed (min of missing HP and transfusion amount)
        hp_missing = target.health_max - target.health
        hp_restored = min(hp_missing, self.TRANSFUSION_HP_RESTORE)
        self.hp_healed_total += hp_restored

    def get_statistics(self) -> Dict[str, any]:
        """
        Get transfusion statistics

        Returns:
            Dictionary containing transfusion stats
        """
        return {
            "total_transfusions": self.transfusions_performed,
            "total_hp_healed": self.hp_healed_total,
            "transfusions_by_unit": dict(self.transfusions_per_unit_type),
            "avg_hp_per_transfusion": (
                self.hp_healed_total / self.transfusions_performed
                if self.transfusions_performed > 0 else 0
            )
        }

    def log_statistics(self, iteration: int) -> None:
        """Log transfusion statistics (call periodically)"""
        if self.transfusions_performed > 0 and iteration % 2200 == 0:  # Every 100 seconds
            stats = self.get_statistics()
            self.logger.info(
                f"[TRANSFUSION STATS] "
                f"Total: {stats['total_transfusions']}, "
                f"HP Healed: {stats['total_hp_healed']:.0f}, "
                f"Avg: {stats['avg_hp_per_transfusion']:.1f} HP/cast"
            )

            # Log top 3 healed unit types
            if stats['transfusions_by_unit']:
                top_healed = sorted(
                    stats['transfusions_by_unit'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:3]
                self.logger.info(
                    f"[TRANSFUSION] Top healed: " +
                    ", ".join(f"{ut.name}: {count}" for ut, count in top_healed)
                )
