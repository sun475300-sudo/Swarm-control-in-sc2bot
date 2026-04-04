"""
Large-Scale Unit Combination Test Runner
Simulates unit combinations and generates detailed results
"""

import json
import os
import time
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class UnitType:
    name: str
    hp: int
    damage: int
    speed: int
    cost: int
    attacks: List[str]


ZERG_UNITS = {
    "Zergling": UnitType(
        "Zergling", hp=35, damage=5, speed=10, cost=25, attacks=["ground"]
    ),
    "Baneling": UnitType(
        "Baneling", hp=30, damage=35, speed=8, cost=25, attacks=["ground"]
    ),
    "Roach": UnitType("Roach", hp=145, damage=12, speed=6, cost=50, attacks=["ground"]),
    "Hydralisk": UnitType(
        "Hydralisk", hp=90, damage=12, speed=7, cost=100, attacks=["ground", "air"]
    ),
    "Mutalisk": UnitType(
        "Mutalisk", hp=120, damage=9, speed=9, cost=100, attacks=["air"]
    ),
    "Corruptor": UnitType(
        "Corruptor", hp=190, damage=14, speed=6, cost=150, attacks=["air"]
    ),
    "BroodLord": UnitType(
        "BroodLord", hp=300, damage=20, speed=4, cost=250, attacks=["air"]
    ),
    "Ultralisk": UnitType(
        "Ultralisk", hp=500, damage=25, speed=5, cost=300, attacks=["ground"]
    ),
    "Queen": UnitType(
        "Queen", hp=200, damage=10, speed=5, cost=150, attacks=["ground", "air"]
    ),
    "Viper": UnitType("Viper", hp=150, damage=15, speed=6, cost=150, attacks=["air"]),
    "Infestor": UnitType("Infestor", hp=90, damage=0, speed=5, cost=150, attacks=[]),
    "Lurker": UnitType(
        "Lurker", hp=200, damage=20, speed=5, cost=150, attacks=["ground"]
    ),
}

ENEMY_UNITS = {
    "Marine": UnitType("Marine", hp=45, damage=6, speed=5, cost=50, attacks=["ground"]),
    "Marauder": UnitType(
        "Marauder", hp=125, damage=10, speed=5, cost=75, attacks=["ground"]
    ),
    "Tank": UnitType("Tank", hp=150, damage=30, speed=3, cost=150, attacks=["ground"]),
    "Thor": UnitType(
        "Thor", hp=350, damage=40, speed=3, cost=300, attacks=["ground", "air"]
    ),
    "Medivac": UnitType("Medivac", hp=150, damage=0, speed=8, cost=100, attacks=[]),
    "Battlecruiser": UnitType(
        "Battlecruiser", hp=500, damage=50, speed=4, cost=400, attacks=["ground", "air"]
    ),
    "Zealot": UnitType(
        "Zealot", hp=100, damage=8, speed=6, cost=50, attacks=["ground"]
    ),
    "Stalker": UnitType(
        "Stalker", hp=80, damage=10, speed=6, cost=80, attacks=["ground", "air"]
    ),
    "Immortal": UnitType(
        "Immortal", hp=200, damage=20, speed=5, cost=150, attacks=["ground"]
    ),
    "VoidRay": UnitType(
        "VoidRay", hp=150, damage=15, speed=7, cost=100, attacks=["air"]
    ),
}


@dataclass
class TestResult:
    scenario: str
    player_combo: str
    enemy_combo: str
    player_units: List[str]
    enemy_units: List[str]
    wins: int
    losses: int
    win_rate: float
    avg_duration: float
    details: Dict[str, Any] = field(default_factory=dict)


def calculate_combat_power(units: List[str]) -> float:
    total_power = 0
    for unit_name in units:
        if unit_name in ZERG_UNITS:
            u = ZERG_UNITS[unit_name]
        elif unit_name in ENEMY_UNITS:
            u = ENEMY_UNITS[unit_name]
        else:
            continue
        total_power += (u.hp * 0.3 + u.damage * 0.5 + u.speed * 0.2) * 10
    return total_power


def calculate_synergy(players: List[str], enemies: List[str]) -> Dict[str, float]:
    player_power = calculate_combat_power(players)
    enemy_power = calculate_combat_power(enemies)

    base_win_rate = player_power / (player_power + enemy_power + 100) * 100

    synergy_bonus = 0
    if "Zergling" in players and "Baneling" in players:
        synergy_bonus += 10
    if "Roach" in players and "Hydralisk" in players:
        synergy_bonus += 8
    if "Mutalisk" in players and "Corruptor" in players:
        synergy_bonus += 12
    if "Ultralisk" in players and "BroodLord" in players:
        synergy_bonus += 15

    counter_bonus = 0
    air_units = [
        u for u in players if u in ZERG_UNITS and "air" in ZERG_UNITS[u].attacks
    ]
    ground_enemies = [
        u for u in enemies if u in ENEMY_UNITS and "ground" in ENEMY_UNITS[u].attacks
    ]
    if air_units and ground_enemies:
        counter_bonus += 5

    return {
        "base_win_rate": base_win_rate,
        "synergy_bonus": synergy_bonus,
        "counter_bonus": counter_bonus,
        "final_win_rate": min(100, base_win_rate + synergy_bonus + counter_bonus),
        "player_power": player_power,
        "enemy_power": enemy_power,
    }


def run_unit_combo_test(
    scenario: str,
    player_units: List[str],
    enemy_units: List[str],
    iterations: int = 100,
) -> TestResult:
    wins = 0
    losses = 0
    total_duration = 0

    synergy = calculate_synergy(player_units, enemy_units)

    for i in range(iterations):
        start = time.time()

        roll = random.random() * 100
        if roll < synergy["final_win_rate"]:
            wins += 1
        else:
            losses += 1

        total_duration += (time.time() - start) * 1000

    win_rate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
    avg_duration = total_duration / iterations

    return TestResult(
        scenario=scenario,
        player_combo="+".join(player_units),
        enemy_combo="+".join(enemy_units),
        player_units=player_units,
        enemy_units=enemy_units,
        wins=wins,
        losses=losses,
        win_rate=win_rate,
        avg_duration=avg_duration,
        details={"synergy": synergy, "iterations": iterations},
    )


def run_all_combinations() -> List[TestResult]:
    scenarios = [
        {
            "name": "rush_defense",
            "player_units": ["Zergling", "Baneling"],
            "enemy_units": ["Zergling", "Zergling", "Zergling"],
        },
        {
            "name": "macro_battle",
            "player_units": ["Roach", "Hydralisk"],
            "enemy_units": ["Marine", "Marauder", "Marine", "Marauder"],
        },
        {
            "name": "harassment",
            "player_units": ["Mutalisk", "Mutalisk", "Mutalisk"],
            "enemy_units": ["Probe", "Probe", "Probe", "Pylon"],
        },
        {
            "name": "team_fight",
            "player_units": ["Ultralisk", "BroodLord"],
            "enemy_units": ["Thor", "Thor", "Battlecruiser"],
        },
        {
            "name": "mid_game",
            "player_units": ["Roach", "Hydralisk", "Mutalisk"],
            "enemy_units": ["Marine", "Marauder", "Tank"],
        },
        {
            "name": "defensive",
            "player_units": ["Queen", "Roach", "Roach"],
            "enemy_units": ["Zealot", "Zealot", "Stalker"],
        },
        {
            "name": "tech_push",
            "player_units": ["Viper", "BroodLord", "Ultralisk"],
            "enemy_units": ["Immortal", "VoidRay", "VoidRay"],
        },
    ]

    results = []
    for scenario in scenarios:
        result = run_unit_combo_test(
            scenario["name"], scenario["player_units"], scenario["enemy_units"]
        )
        results.append(result)

    return results


def print_results(results: List[TestResult]) -> None:
    print("\n" + "=" * 80)
    print("UNIT COMBINATION TEST RESULTS - DETAILED ANALYSIS")
    print("=" * 80)

    print(
        f"\n{'Scenario':<15} {'Player Combo':<25} {'Enemy Combo':<20} {'Win Rate':>10} {'W/L':>8}"
    )
    print("-" * 80)

    for r in results:
        print(
            f"{r.scenario:<15} {r.player_combo:<25} {r.enemy_combo:<20} {r.win_rate:>8.1f}% {r.wins}/{r.losses}"
        )

    print("\n" + "=" * 80)
    print("SYNERGY ANALYSIS")
    print("=" * 80)

    for r in results:
        synergy = r.details.get("synergy", {})
        print(f"\n[{r.player_combo} vs {r.enemy_combo}]")
        print(f"  Base Win Rate: {synergy.get('base_win_rate', 0):.1f}%")
        print(f"  Synergy Bonus: +{synergy.get('synergy_bonus', 0):.1f}%")
        print(f"  Counter Bonus: +{synergy.get('counter_bonus', 0):.1f}%")
        print(f"  Final Win Rate: {synergy.get('final_win_rate', 0):.1f}%")
        print(f"  Player Power: {synergy.get('player_power', 0):.0f}")
        print(f"  Enemy Power: {synergy.get('enemy_power', 0):.0f}")


def save_results(
    results: List[TestResult], output_file: str = "test_results.json"
) -> None:
    data = {
        "timestamp": datetime.now().isoformat(),
        "total_scenarios": len(results),
        "results": [
            {
                "scenario": r.scenario,
                "player_combo": r.player_combo,
                "enemy_combo": r.enemy_combo,
                "player_units": r.player_units,
                "enemy_units": r.enemy_units,
                "wins": r.wins,
                "losses": r.losses,
                "win_rate": r.win_rate,
                "avg_duration_ms": r.avg_duration,
                "details": r.details,
            }
            for r in results
        ],
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n[Results saved to {output_file}]")


if __name__ == "__main__":
    print("[UnitComboTest] Running large-scale unit combination tests...")
    results = run_all_combinations()
    print_results(results)
    save_results(results)
