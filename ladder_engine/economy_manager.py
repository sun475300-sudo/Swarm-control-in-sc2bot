"""
Phase 364: Economy Manager
Economic optimization for Zerg: drone saturation, gas timing, expand timing,
income tracking, spending efficiency, and bank management.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class BaseInfo:
    location_tag: int
    mineral_patches: int = 8
    geysers: int = 2
    assigned_workers: int = 0
    active_geysers: int = 0
    workers_on_gas: int = 0

    @property
    def ideal_workers(self) -> int:
        """Ideal worker count: 2 per mineral patch + 3 per active geyser."""
        return self.mineral_patches * 2 + self.active_geysers * 3

    @property
    def is_saturated(self) -> bool:
        return self.assigned_workers >= self.ideal_workers

    @property
    def over_saturation(self) -> int:
        return max(0, self.assigned_workers - self.ideal_workers)


@dataclass
class EconomySnapshot:
    game_time: float
    minerals: int
    vespene: int
    mineral_income: float    # per minute
    vespene_income: float    # per minute
    worker_count: int
    base_count: int
    spending_efficiency: float   # resources spent / resources collected


class EconomyManager:
    """Manages Zerg economic decisions and tracks efficiency metrics."""

    # Constants
    MINERALS_PER_EXPAND = 300
    GAS_TIMING_SUPPLY_ZVT = 18
    GAS_TIMING_SUPPLY_ZVP = 17
    GAS_TIMING_SUPPLY_ZVZ = 18
    BANK_WARNING_MINERALS = 400
    BANK_WARNING_VESPENE = 200
    MAX_WORKERS_PER_BASE = 22  # includes over-saturation buffer

    def __init__(self):
        self.bases: List[BaseInfo] = []
        self._history: List[EconomySnapshot] = []
        self._total_collected_minerals: float = 0.0
        self._total_collected_vespene: float = 0.0
        self._total_spent_minerals: float = 0.0
        self._total_spent_vespene: float = 0.0

    # ------------------------------------------------------------------
    # Base registration
    # ------------------------------------------------------------------

    def register_base(self, location_tag: int, mineral_patches: int = 8, geysers: int = 2):
        self.bases.append(BaseInfo(location_tag, mineral_patches, geysers))

    def remove_base(self, location_tag: int):
        self.bases = [b for b in self.bases if b.location_tag != location_tag]

    # ------------------------------------------------------------------
    # Worker distribution
    # ------------------------------------------------------------------

    def optimal_worker_distribution(
        self,
        total_workers: int
    ) -> Dict[int, int]:
        """
        Return a mapping of {base_tag: worker_count} for optimal saturation.
        Fills bases in order until all workers are assigned.
        """
        distribution: Dict[int, int] = {b.location_tag: 0 for b in self.bases}
        remaining = total_workers

        # First pass: fill to ideal saturation
        for base in self.bases:
            alloc = min(remaining, base.ideal_workers)
            distribution[base.location_tag] = alloc
            remaining -= alloc
            if remaining <= 0:
                break

        # Second pass: distribute excess to bases with room
        if remaining > 0:
            for base in self.bases:
                extra = min(remaining, self.MAX_WORKERS_PER_BASE - distribution[base.location_tag])
                if extra > 0:
                    distribution[base.location_tag] += extra
                    remaining -= extra
                if remaining <= 0:
                    break

        return distribution

    def mineral_saturation_check(self) -> List[Tuple[int, int]]:
        """
        Return list of (base_tag, deficit) for under-saturated bases.
        Positive deficit = needs more workers.
        """
        results = []
        for base in self.bases:
            deficit = base.ideal_workers - base.assigned_workers
            if deficit > 0:
                results.append((base.location_tag, deficit))
        return results

    def transfer_workers_recommendation(
        self,
        worker_count: int
    ) -> Optional[Tuple[int, int, int]]:
        """
        Suggest (from_base_tag, to_base_tag, count) for worker transfer.
        Returns None if no transfer is beneficial.
        """
        over_saturated = [b for b in self.bases if b.over_saturation > 0]
        under_saturated = [b for b in self.bases if b.assigned_workers < b.ideal_workers]
        if not over_saturated or not under_saturated:
            return None
        src = max(over_saturated, key=lambda b: b.over_saturation)
        dst = min(under_saturated, key=lambda b: b.ideal_workers - b.assigned_workers)
        count = min(src.over_saturation, dst.ideal_workers - dst.assigned_workers)
        return (src.location_tag, dst.location_tag, count)

    # ------------------------------------------------------------------
    # Gas timing
    # ------------------------------------------------------------------

    def gas_timing_calculator(
        self,
        opponent_race: str,
        supply_used: int,
        has_pool: bool,
        has_lair: bool
    ) -> bool:
        """
        Return True when it is the right time to start taking gas.
        """
        if not has_pool:
            return False

        thresholds = {
            "Terran":  self.GAS_TIMING_SUPPLY_ZVT,
            "Protoss": self.GAS_TIMING_SUPPLY_ZVP,
            "Zerg":    self.GAS_TIMING_SUPPLY_ZVZ,
        }
        threshold = thresholds.get(opponent_race, 18)

        # Take gas earlier when heading toward lair
        if has_lair:
            return True

        return supply_used >= threshold

    # ------------------------------------------------------------------
    # Expand timing
    # ------------------------------------------------------------------

    def expand_timing(
        self,
        minerals: int,
        worker_count: int,
        base_count: int,
        army_supply: int,
        opponent_aggression: float = 0.0
    ) -> bool:
        """
        Return True when expanding is economically justified.
        opponent_aggression: 0.0 = passive, 1.0 = all-in.
        """
        if opponent_aggression > 0.7:
            return False  # Don't expand under pressure

        # Saturation-based trigger: if bases are near-saturated, expand
        total_ideal = sum(b.ideal_workers for b in self.bases)
        if worker_count >= total_ideal * 0.85 and minerals >= self.MINERALS_PER_EXPAND:
            return True

        # Mineral bank trigger
        if minerals >= self.BANK_WARNING_MINERALS and base_count < 3:
            return True

        return False

    # ------------------------------------------------------------------
    # Income and efficiency tracking
    # ------------------------------------------------------------------

    def record_snapshot(
        self,
        game_time: float,
        minerals: int,
        vespene: int,
        mineral_income: float,
        vespene_income: float,
        worker_count: int,
        base_count: int,
        minerals_spent: float = 0.0,
        vespene_spent: float = 0.0,
    ):
        self._total_collected_minerals += mineral_income * (1 / 60)
        self._total_collected_vespene += vespene_income * (1 / 60)
        self._total_spent_minerals += minerals_spent
        self._total_spent_vespene += vespene_spent

        total_collected = self._total_collected_minerals + self._total_collected_vespene
        total_spent = self._total_spent_minerals + self._total_spent_vespene
        efficiency = total_spent / max(total_collected, 1.0)

        snap = EconomySnapshot(
            game_time=game_time,
            minerals=minerals,
            vespene=vespene,
            mineral_income=mineral_income,
            vespene_income=vespene_income,
            worker_count=worker_count,
            base_count=base_count,
            spending_efficiency=min(efficiency, 1.0),
        )
        self._history.append(snap)
        return snap

    def bank_management(self, minerals: int, vespene: int) -> Dict[str, str]:
        """Return advisories for high resource banks."""
        advisories: Dict[str, str] = {}
        if minerals > self.BANK_WARNING_MINERALS:
            advisories["minerals"] = (
                f"High mineral bank ({minerals}): spend on drones, units, or expand."
            )
        if vespene > self.BANK_WARNING_VESPENE:
            advisories["vespene"] = (
                f"High vespene bank ({vespene}): invest in upgrades or tech units."
            )
        return advisories

    def spending_efficiency_report(self) -> Dict[str, float]:
        """Return the latest spending efficiency metrics."""
        if not self._history:
            return {"spending_efficiency": 0.0, "samples": 0}
        latest = self._history[-1]
        return {
            "spending_efficiency": round(latest.spending_efficiency, 4),
            "mineral_income": latest.mineral_income,
            "vespene_income": latest.vespene_income,
            "samples": len(self._history),
        }
