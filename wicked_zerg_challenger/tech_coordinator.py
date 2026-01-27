from typing import Dict, Optional, Tuple, Any
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2

class TechCoordinator:
    """
    Centralized coordinator for tech building requests.
    Resolves conflicts between multiple managers (Strategy vs Macro vs BuildOrder)
    by enforcing a priority system.
    """
    
    # Priority Constants
    PRIORITY_CRITICAL = 100  # Emergency defense (Spine/Spore)
    PRIORITY_STRATEGY = 75   # Aggressive Strategies (e.g. Rush Roach Warren)
    PRIORITY_BUILD_ORDER = 50 # Standard Build Order
    PRIORITY_MACRO = 25      # ProductionResilience / Auto-Tech

    def __init__(self, bot):
        self.bot = bot
        # Format: {UnitTypeId: (priority, location_or_near, request_frame, requester_name)}
        self.pending_requests: Dict[UnitTypeId, Tuple[int, Any, int, str]] = {}
        self.last_build_frame = 0

    def request_structure(self, 
                          structure_type: UnitTypeId, 
                          location: Any, 
                          priority: int, 
                          requester_name: str = "Unknown") -> bool:
        """
        Request to build a structure.
        Returns True if request is accepted (queued), False if rejected (lower priority).
        """
        # If we already have a request for this type
        if structure_type in self.pending_requests:
            current_priority = self.pending_requests[structure_type][0]
            
            # Reject if new request is lower or equal priority
            if priority <= current_priority:
                return False
                
            # Override if new request is higher priority
            # print(f"[TECH] Overriding {structure_type} request from {self.pending_requests[structure_type][3]} "
            #       f"(P{current_priority}) with {requester_name} (P{priority})")

        self.pending_requests[structure_type] = (priority, location, self.bot.iteration, requester_name)
        return True

    def is_planned(self, structure_type: UnitTypeId) -> bool:
        """Check if a structure is already planned."""
        return structure_type in self.pending_requests or self.bot.already_pending(structure_type) > 0

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
                # Exception: Multiple Spines/Spores/Evos allowed
                if stype not in [UnitTypeId.SPINECRAWLER, UnitTypeId.SPORECRAWLER, UnitTypeId.EVOLUTIONCHAMBER]:
                    to_remove.append(stype)
        
        for stype in to_remove:
            del self.pending_requests[stype]

        # 2. Process requests by priority (High -> Low)
        # Sort requests by priority descending
        sorted_requests = sorted(self.pending_requests.items(), key=lambda x: x[1][0], reverse=True)

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
                if stype in [UnitTypeId.SPINECRAWLER, UnitTypeId.SPORECRAWLER]:
                     if hasattr(self.bot, "placement_helper") and self.bot.placement_helper:
                         built = await self.bot.placement_helper.build_structure_safely(stype, location)

                if not built:
                    await self.bot.build(stype, near=location)
                
                print(f"[TECH] Executing {stype.name} for {requester} (P{priority})")
                
                # Remove from queue immediately to avoid double build in same frame
                # (Though async build might take a moment to register pending)
                del self.pending_requests[stype]
                
                # Limit to 1 tech building per frame to avoid blocking movement?
                # Maybe unnecessary, but safer.
                break 

            except Exception as e:
                print(f"[TECH] Failed to build {stype}: {e}")
