"""
Wicked Zerg - Battle Simulation
Phase 150: Python Parallel (Multiprocessing)
"""

import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np


@dataclass
class BattleUnit:
    unit_type: int
    health: float
    damage: float
    armor: float
    pos_x: float
    pos_y: float


def calculate_swarm_damage(count: int) -> int:
    return count * 5


def swarm_formation(
    center_x: float, center_y: float, count: int, radius: float
) -> List[Tuple[float, float]]:
    angles = np.linspace(0, 2 * np.pi, count, endpoint=False)
    x = center_x + radius * np.cos(angles)
    y = center_y + radius * np.sin(angles)
    return list(zip(x, y))


def unit_strength(health: float, damage: float, armor: float) -> float:
    effective = damage * health / 100
    return effective * (1 - armor * 0.01)


def battle_outcome(
    attackers: List[Tuple[float, float, float]],
    defenders: List[Tuple[float, float, float]],
) -> bool:
    attack_power = sum(unit_strength(h, d, a) for h, d, a in attackers)
    defense_power = sum(unit_strength(h, d, a) for h, d, a in defenders)
    return attack_power > defense_power


def process_unit_batch(units: List[BattleUnit]) -> float:
    return sum(unit_strength(u.health, u.damage, u.armor) for u in units)


def parallel_strength_calculation(units: List[BattleUnit], n_workers: int = 4) -> float:
    chunk_size = len(units) // n_workers
    chunks = [units[i : i + chunk_size] for i in range(0, len(units), chunk_size)]

    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        results = list(executor.map(process_unit_batch, chunks))

    return sum(results)


if __name__ == "__main__":
    print("Battle Simulation Initialized - Python Parallel")
