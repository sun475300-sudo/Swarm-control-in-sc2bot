import logging
from typing import Any, Dict, Optional, Tuple

from sc2.ids.unit_typeid import UnitTypeId

logger = logging.getLogger("TechCoordinator")


class TechCoordinator:
    """
    Centralized coordinator for tech building requests.
    Resolves conflicts between multiple managers (Strategy vs Macro vs BuildOrder)
    by enforcing a priority system.
    """

    # Priority Constants
    PRIORITY_CRITICAL = 100  # Emergency defense (Spine/Spore)
    PRIORITY_STRATEGY = 75  # Aggressive Strategies (e.g. Rush Roach Warren)
    PRIORITY_BUILD_ORDER = 50  # Standard Build Order
    PRIORITY_MACRO = 25  # ProductionResilience / Auto-Tech
    MULTI_INSTANCE_STRUCTURES = {
        UnitTypeId.SPINECRAWLER,
        UnitTypeId.SPORECRAWLER,
        UnitTypeId.EVOLUTIONCHAMBER,
        UnitTypeId.HATCHERY,
    }

    def __init__(self, bot):
        self.bot = bot
        # Format: {UnitTypeId: (priority, location_or_near, request_frame, requester_name)}
        self.pending_requests: Dict[UnitTypeId, Tuple[int, Any, int, str]] = {}
        self.last_build_frame = 0

    def request_structure(
        self,
        structure_type: UnitTypeId,
        location: Any,
        priority: int,
        requester_name: str = "Unknown",
        requester: Optional[str] = None,
    ) -> bool:
        """
        Request to build a structure.
        Returns True if request is accepted (queued), False if rejected (lower priority).
        """
        if requester is not None:
            requester_name = requester

        # If we already have a request for this type
        if structure_type in self.pending_requests:
            current_priority = self.pending_requests[structure_type][0]

            # Reject if new request is lower or equal priority
            if priority <= current_priority:
                return False

            # Override if new request is higher priority
            logger.debug(
                "Overriding %s request from %s (P%s) with %s (P%s)",
                structure_type,
                self.pending_requests[structure_type][3],
                current_priority,
                requester_name,
                priority,
            )

        self.pending_requests[structure_type] = (
            priority,
            location,
            self.bot.iteration,
            requester_name,
        )
        return True

    def is_planned(self, structure_type: UnitTypeId) -> bool:
        """Check if a structure is already planned."""
        return (
            structure_type in self.pending_requests
            or self.bot.already_pending(structure_type) > 0
        )

    async def update(self):
        """
        Execute the highest priority requests.
        Should be called once per frame in BotStepIntegration.
        """
        # 1. Cleanup invalid requests or completed ones
        to_remove = []
        for stype in self.pending_requests:
            # If already started building (pending > 0), remove request
            if self.bot.already_pending(stype) > 0:
                to_remove.append(stype)
            # If we have the structure ready, remove request
            elif self.bot.structures(stype).ready.exists:
                # Exception: multi-instance structures are valid even when one
                # already exists. Hatchery requests must not be dropped because
                # the starting Hatchery is ready.
                if stype not in self.MULTI_INSTANCE_STRUCTURES:
                    to_remove.append(stype)

        for stype in to_remove:
            del self.pending_requests[stype]

        opening_hatch_active = self._is_opening_hatch_request_active()
        opening_natural_reserve_active = self._is_opening_natural_reserve_active()
        expansion_recovery_active = self._is_expansion_recovery_reserve_active()
        hatch_reserve_active = (
            opening_hatch_active
            or opening_natural_reserve_active
            or expansion_recovery_active
        )
        if hatch_reserve_active and UnitTypeId.HATCHERY not in self.pending_requests:
            return
        if hatch_reserve_active and not self.bot.can_afford(UnitTypeId.HATCHERY):
            return

        # 2. Process requests by priority (High -> Low)
        # Sort requests by priority descending
        sorted_requests = sorted(
            self.pending_requests.items(),
            key=lambda x: self._effective_priority(x[0], x[1][0], hatch_reserve_active),
            reverse=True,
        )

        for stype, (priority, location, frame, requester) in sorted_requests:
            if stype == UnitTypeId.EXTRACTOR and self._should_delay_extractor():
                continue

            # Check resources
            if not self.bot.can_afford(stype):
                continue

            # Check worker availability
            if not self.bot.workers.exists:
                continue

            # Check dependencies (e.g. Lair for Spire) - rudimentary check
            # SC2 `can_afford` checks resources but not tech requirements fully?
            # Actually bot.build checks tech tree usually? No, we need to check manually sometimes.
            # For now, rely on requester to only request valid tech.

            # Execute Build
            try:
                # Use Placement Helper if available for Spines/Spores
                built = False
                if stype == UnitTypeId.HATCHERY:
                    worker = self.bot.workers.closest_to(location)
                    if not worker:
                        continue
                    action = worker.build(UnitTypeId.HATCHERY, location)
                    if hasattr(self.bot, "do"):
                        self.bot.do(action)
                    built = True
                elif stype in [UnitTypeId.SPINECRAWLER, UnitTypeId.SPORECRAWLER]:
                    if (
                        hasattr(self.bot, "placement_helper")
                        and self.bot.placement_helper
                    ):
                        built = await self.bot.placement_helper.build_structure_safely(
                            stype, location
                        )

                if not built:
                    await self.bot.build(stype, near=location)

                logger.info(f"Executing {stype.name} for {requester} (P{priority})")

                # Remove from queue immediately to avoid double build in same frame
                # (Though async build might take a moment to register pending)
                del self.pending_requests[stype]

                # Limit to 1 tech building per frame to avoid blocking movement?
                # Maybe unnecessary, but safer.
                break

            except Exception as e:
                logger.error(f"Failed to build {stype}: {e}")

    def _effective_priority(
        self, structure_type: UnitTypeId, priority: int, opening_hatch_active: bool
    ) -> int:
        if opening_hatch_active and structure_type == UnitTypeId.HATCHERY:
            return priority + 1000
        return priority

    def _should_delay_extractor(self) -> bool:
        """Delay gas requests until expansion minerals are protected."""
        base_count = self._ready_base_count()

        already_pending = getattr(self.bot, "already_pending", lambda _: 0)
        pending_hatch = int(already_pending(UnitTypeId.HATCHERY) or 0)
        pending_gas = int(already_pending(UnitTypeId.EXTRACTOR) or 0)

        try:
            gas_structures = self.bot.structures(UnitTypeId.EXTRACTOR)
            gas_count = int(getattr(gas_structures, "amount", 0) or 0)
        except (AttributeError, TypeError, ValueError):
            gas_count = 0

        if base_count < 2 and pending_hatch == 0:
            return True
        if base_count < 3 and gas_count + pending_gas >= 1:
            return True
        return False

    def _is_opening_hatch_request_active(self) -> bool:
        if UnitTypeId.HATCHERY not in self.pending_requests:
            return False
        try:
            game_time = float(getattr(self.bot, "time", 0.0) or 0.0)
        except (TypeError, ValueError):
            game_time = 0.0
        if game_time >= 120.0:
            return False

        if self._ready_base_count() >= 2:
            return False

        blackboard = getattr(self.bot, "blackboard", None)
        threat = getattr(blackboard, "threat", None)
        if threat is not None and getattr(threat, "is_rushing", False):
            return False

        return True

    def _is_opening_natural_reserve_active(self) -> bool:
        if UnitTypeId.HATCHERY in self.pending_requests:
            return False

        try:
            game_time = float(getattr(self.bot, "time", 0.0) or 0.0)
        except (TypeError, ValueError):
            game_time = 0.0
        if not 38.0 <= game_time < 120.0:
            return False

        if self._ready_base_count() >= 2:
            return False
        if self._pending_hatchery_count() > 0:
            return False
        if self._has_active_base_threat() or self._blackboard_has_serious_base_threat():
            return False

        workers = getattr(self.bot, "workers", None)
        try:
            worker_count = int(getattr(workers, "amount", 0) or 0)
        except (TypeError, ValueError):
            worker_count = 0

        return worker_count >= 15

    def _is_expansion_recovery_reserve_active(self) -> bool:
        if UnitTypeId.HATCHERY in self.pending_requests:
            return True

        try:
            game_time = float(getattr(self.bot, "time", 0.0) or 0.0)
        except (TypeError, ValueError):
            return False
        if game_time < 120.0:
            return False

        ready_bases = self._ready_base_count()
        pending_hatch = self._pending_hatchery_count()

        if ready_bases >= 4:
            return False

        if self._has_active_base_threat() or self._blackboard_has_serious_base_threat():
            return False

        if pending_hatch > 0:
            return ready_bases < 2

        if ready_bases < 3:
            return True

        return ready_bases == 3 and game_time >= 360.0

    def _ready_base_count(self) -> int:
        townhalls = getattr(self.bot, "townhalls", None)
        ready = getattr(townhalls, "ready", None) if townhalls is not None else None

        for source in (ready, townhalls):
            if not source:
                continue
            amount = getattr(source, "amount", None)
            if isinstance(amount, (int, float)):
                return int(amount)
            if amount is not None:
                continue
            try:
                return len(list(source))
            except TypeError:
                pass
        return 1

    def _pending_hatchery_count(self) -> int:
        already_pending = getattr(self.bot, "already_pending", None)
        if not callable(already_pending):
            return 0
        try:
            return int(already_pending(UnitTypeId.HATCHERY) or 0)
        except (TypeError, ValueError):
            return 0

    def _has_active_base_threat(self, min_enemies: int = 4) -> bool:
        enemy_units = getattr(self.bot, "enemy_units", None)
        townhalls = getattr(self.bot, "townhalls", None)
        if enemy_units is None or townhalls is None:
            return False

        try:
            bases = list(townhalls)
        except TypeError:
            first_base = getattr(townhalls, "first", None)
            bases = [first_base] if first_base else []

        for base in bases:
            if not base:
                continue
            try:
                nearby = enemy_units.closer_than(12, base)
            except Exception:
                continue
            amount = getattr(nearby, "amount", 0)
            if isinstance(amount, (int, float)) and amount >= min_enemies:
                return True
            try:
                if len(nearby) >= min_enemies:
                    return True
            except TypeError:
                pass
        return False

    def _blackboard_has_serious_base_threat(self, min_enemies: int = 4) -> bool:
        blackboard = getattr(self.bot, "blackboard", None)
        threat = getattr(blackboard, "threat", None) if blackboard else None
        if threat is None:
            return False

        try:
            enemy_near_base = int(getattr(threat, "enemy_units_near_base", 0) or 0)
        except (TypeError, ValueError):
            enemy_near_base = 0
        if enemy_near_base >= min_enemies:
            return True

        try:
            enemy_supply = float(getattr(threat, "enemy_army_supply", 0.0) or 0.0)
        except (TypeError, ValueError):
            enemy_supply = 0.0
        threat_level = getattr(threat, "level", None)
        try:
            from game_state_blackboard import ThreatLevel
        except ImportError:
            ThreatLevel = None
        if ThreatLevel is not None and threat_level is not None:
            try:
                if threat_level >= ThreatLevel.CRITICAL and enemy_supply >= 6.0:
                    return True
            except TypeError:
                pass

        return False
