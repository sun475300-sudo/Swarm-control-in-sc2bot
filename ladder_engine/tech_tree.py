"""
Phase 366: Tech Tree Optimizer
Upgrade priority system for Zerg, with tech node dependencies and
dynamic priority calculation based on army composition and opponent tech.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum


class UpgradeStatus(Enum):
    LOCKED = "locked"
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


@dataclass
class TechNode:
    name: str
    mineral_cost: int
    vespene_cost: int
    research_time: float  # seconds
    required_building: str
    prerequisites: List[str] = field(default_factory=list)
    status: UpgradeStatus = UpgradeStatus.LOCKED
    base_priority: float = 0.5  # 0.0 - 1.0

    def is_researchable(
        self, available_buildings: Set[str], completed: Set[str]
    ) -> bool:
        if self.status != UpgradeStatus.AVAILABLE:
            return False
        if self.required_building not in available_buildings:
            return False
        return all(p in completed for p in self.prerequisites)

    def __repr__(self):
        return f"TechNode({self.name}, {self.status.value}, p={self.base_priority:.2f})"


def _build_zerg_tech_nodes() -> Dict[str, TechNode]:
    """Define the Zerg upgrade tree."""
    nodes: Dict[str, TechNode] = {}

    def add(name, minerals, vespene, time, building, prereqs=None, priority=0.5):
        nodes[name] = TechNode(
            name=name,
            mineral_cost=minerals,
            vespene_cost=vespene,
            research_time=time,
            required_building=building,
            prerequisites=prereqs or [],
            status=UpgradeStatus.LOCKED,
            base_priority=priority,
        )

    # Movement / basic
    add("metabolic_boost", 100, 100, 110, "SpawningPool", priority=0.90)
    add("adrenal_glands", 200, 200, 130, "SpawningPool", ["metabolic_boost"], 0.70)
    add("pneumatized_carapace", 100, 100, 100, "SpawningPool", priority=0.55)

    # Ground carapace upgrades (tier 1-3)
    add("ground_carapace_1", 150, 150, 160, "EvolutionChamber", priority=0.80)
    add(
        "ground_carapace_2",
        225,
        225,
        190,
        "EvolutionChamber",
        ["ground_carapace_1", "Lair"],
        0.70,
    )
    add(
        "ground_carapace_3",
        300,
        300,
        220,
        "EvolutionChamber",
        ["ground_carapace_2", "Hive"],
        0.60,
    )

    # Melee attack upgrades
    add("melee_attacks_1", 100, 100, 160, "EvolutionChamber", priority=0.75)
    add(
        "melee_attacks_2",
        150,
        150,
        190,
        "EvolutionChamber",
        ["melee_attacks_1", "Lair"],
        0.65,
    )
    add(
        "melee_attacks_3",
        200,
        200,
        220,
        "EvolutionChamber",
        ["melee_attacks_2", "Hive"],
        0.55,
    )

    # Missile (ranged) attack upgrades
    add("missile_attacks_1", 100, 100, 160, "EvolutionChamber", priority=0.72)
    add(
        "missile_attacks_2",
        150,
        150,
        190,
        "EvolutionChamber",
        ["missile_attacks_1", "Lair"],
        0.62,
    )
    add(
        "missile_attacks_3",
        200,
        200,
        220,
        "EvolutionChamber",
        ["missile_attacks_2", "Hive"],
        0.52,
    )

    # Roach / Ravager
    add("glial_reconstitution", 100, 100, 110, "RoachWarren", priority=0.78)
    add("tunneling_claws", 150, 150, 110, "RoachWarren", priority=0.45)

    # Hydralisk
    add("grooved_spines", 100, 100, 100, "HydraliskDen", priority=0.80)
    add("muscular_augments", 100, 100, 100, "HydraliskDen", priority=0.75)

    # Zerg flyer (mutalisk / corruptor)
    add("flyer_attacks_1", 100, 100, 160, "Spire", priority=0.70)
    add("flyer_carapace_1", 150, 150, 160, "Spire", priority=0.65)

    # Infestor / Viper
    add("pathogen_glands", 150, 150, 110, "InfestationPit", priority=0.60)
    add("neural_parasite", 150, 150, 110, "InfestationPit", priority=0.50)

    return nodes


class TechTree:
    """Manages Zerg upgrade nodes and their status."""

    def __init__(self):
        self.nodes: Dict[str, TechNode] = _build_zerg_tech_nodes()

    def unlock(self, node_name: str):
        if node_name in self.nodes:
            self.nodes[node_name].status = UpgradeStatus.AVAILABLE

    def start_research(self, node_name: str):
        if node_name in self.nodes:
            self.nodes[node_name].status = UpgradeStatus.IN_PROGRESS

    def complete_research(self, node_name: str):
        if node_name in self.nodes:
            self.nodes[node_name].status = UpgradeStatus.COMPLETE

    def get_completed(self) -> Set[str]:
        return {
            n for n, node in self.nodes.items() if node.status == UpgradeStatus.COMPLETE
        }

    def get_available(self, buildings: Set[str]) -> List[TechNode]:
        completed = self.get_completed()
        return [
            node
            for node in self.nodes.values()
            if node.is_researchable(buildings, completed)
        ]


class UpgradePlanner:
    """Calculates upgrade priorities for the current game context."""

    def __init__(self, tech_tree: TechTree):
        self.tech_tree = tech_tree

    def _army_modifier(self, upgrade: str, army_comp: Dict[str, int]) -> float:
        """Adjust priority based on what units the bot is fielding."""
        modifiers = {
            "metabolic_boost": army_comp.get("Zergling", 0) * 0.05,
            "melee_attacks_1": army_comp.get("Zergling", 0) * 0.03,
            "ground_carapace_1": (
                army_comp.get("Zergling", 0) + army_comp.get("Roach", 0)
            )
            * 0.02,
            "glial_reconstitution": army_comp.get("Roach", 0) * 0.04,
            "grooved_spines": army_comp.get("Hydralisk", 0) * 0.05,
            "muscular_augments": army_comp.get("Hydralisk", 0) * 0.04,
            "missile_attacks_1": army_comp.get("Hydralisk", 0) * 0.03,
        }
        return min(modifiers.get(upgrade, 0.0), 0.3)

    def _opponent_modifier(self, upgrade: str, opponent_units: Dict[str, int]) -> float:
        """Adjust priority to counter observed opponent units."""
        bio_count = opponent_units.get("Marine", 0) + opponent_units.get("Marauder", 0)
        mech_count = opponent_units.get("Tank", 0) + opponent_units.get("Hellion", 0)
        air_count = opponent_units.get("VikingFighter", 0) + opponent_units.get(
            "Phoenix", 0
        )

        mods = {
            "ground_carapace_1": bio_count * 0.02,
            "missile_attacks_1": mech_count * 0.02,
            "flyer_attacks_1": air_count * 0.04,
            "flyer_carapace_1": air_count * 0.03,
        }
        return min(mods.get(upgrade, 0.0), 0.25)

    def prioritize(
        self,
        available_buildings: Set[str],
        army_comp: Dict[str, int],
        opponent_units: Dict[str, int],
        minerals: int,
        vespene: int,
    ) -> List[TechNode]:
        """
        Return available upgrades sorted by adjusted priority (highest first).
        Filters out upgrades the bot cannot afford.
        """
        candidates = self.tech_tree.get_available(available_buildings)
        scored: List[tuple] = []

        for node in candidates:
            if node.mineral_cost > minerals or node.vespene_cost > vespene:
                continue
            score = (
                node.base_priority
                + self._army_modifier(node.name, army_comp)
                + self._opponent_modifier(node.name, opponent_units)
            )
            scored.append((score, node))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [node for _, node in scored]

    def top_upgrade(
        self,
        available_buildings: Set[str],
        army_comp: Dict[str, int],
        opponent_units: Dict[str, int],
        minerals: int,
        vespene: int,
    ) -> Optional[TechNode]:
        """Return single highest-priority affordable upgrade."""
        ranked = self.prioritize(
            available_buildings, army_comp, opponent_units, minerals, vespene
        )
        return ranked[0] if ranked else None
