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
        expansion_recovery_active = self._is_expansion_recovery_reserve_active()
        hatch_reserve_active = opening_hatch_active or expansion_recovery_active
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

    def _is_opening_hatch_request_active(self) -> bool:
        if UnitTypeId.HATCHERY not in self.pending_requests:
            return False
        try:
            game_time = float(getattr(self.bot, "time", 0.0) or 0.0)
        except (TypeError, ValueError):
            game_time = 0.0
        if game_time >= 120.0:
            return False

        townhalls = getattr(self.bot, "townhalls", None)
        if townhalls is not None:
            try:
                if int(getattr(townhalls, "amount", 1) or 1) >= 2:
                    return False
            except (TypeError, ValueError):
                pass

        blackboard = getattr(self.bot, "blackboard", None)
        threat = getattr(blackboard, "threat", None)
        if threat is not None and getattr(threat, "is_rushing", False) is True:
            return False

        return True

    def _is_expansion_recovery_reserve_active(self) -> bool:
        if UnitTypeId.HATCHERY in self.pending_requests:
            return True

        try:
            game_time = float(getattr(self.bot, "time", 0.0) or 0.0)
        except (TypeError, ValueError):
            return False
        if game_time < 120.0:
            return False

        townhalls = getattr(self.bot, "townhalls", None)
        try:
            base_count = int(getattr(townhalls, "amount", 1) or 1)
        except (TypeError, ValueError):
            base_count = 1
        if base_count >= 4:
            return False

        try:
            if self.bot.already_pending(UnitTypeId.HATCHERY) > 0:
                return False
        except (AttributeError, TypeError, ValueError):
            return False

        blackboard = getattr(self.bot, "blackboard", None)
        threat = getattr(blackboard, "threat", None)
        if threat is not None and getattr(threat, "is_rushing", False) is True:
            return False

        return True
