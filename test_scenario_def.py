"""
Custom Test Scenario Definition System
Allows users to define custom test scenarios with unit combinations
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ScenarioType(Enum):
    RUSH_DEFENSE = "rush_defense"
    MACRO_BATTLE = "macro_battle"
    HARASSMENT = "harassment"
    ECONOMY_TECH = "economy_tech"
    TEAM_FIGHT = "team_fight"
    DEFENSIVE = "defensive"
    CUSTOM = "custom"


class DifficultyLevel(Enum):
    EASY = 1
    MEDIUM = 2
    HARD = 3
    EXTREME = 4


@dataclass
class UnitConfig:
    unit_type: str
    count: int
    upgrades: List[str] = field(default_factory=list)
    position: str = "default"


@dataclass
class ScenarioConfig:
    name: str
    description: str
    scenario_type: str
    player_units: List[UnitConfig]
    enemy_units: List[UnitConfig]
    map_name: str = "AI Arena"
    difficulty: int = 2
    time_limit_seconds: int = 600
    win_conditions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestScenario:
    id: str
    config: ScenarioConfig
    created_at: str
    updated_at: str
    version: str = "1.0"
    enabled: bool = True
    tags: List[str] = field(default_factory=list)


class ScenarioDefinitionManager:
    def __init__(self, scenarios_dir: str = "test_scenarios"):
        self.scenarios_dir = Path(scenarios_dir)
        self.scenarios_dir.mkdir(exist_ok=True)
        self.scenarios: Dict[str, TestScenario] = {}
        self._load_all_scenarios()

    def _load_all_scenarios(self) -> None:
        for f in self.scenarios_dir.glob("*.json"):
            self._load_scenario(f)

    def _load_scenario(self, path: Path) -> Optional[TestScenario]:
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return TestScenario(
                id=data["id"],
                config=ScenarioConfig(**data["config"]),
                created_at=data.get("created_at", datetime.now().isoformat()),
                updated_at=data.get("updated_at", datetime.now().isoformat()),
                version=data.get("version", "1.0"),
                enabled=data.get("enabled", True),
                tags=data.get("tags", []),
            )
        except Exception as e:
            print(f"[WARN] Failed to load {path}: {e}")
            return None

    def create_scenario(self, config: ScenarioConfig) -> TestScenario:
        scenario_id = f"scenario_{len(self.scenarios) + 1:04d}"
        now = datetime.now().isoformat()

        scenario = TestScenario(
            id=scenario_id, config=config, created_at=now, updated_at=now
        )

        self.scenarios[scenario_id] = scenario
        self._save_scenario(scenario)
        return scenario

    def _save_scenario(self, scenario: TestScenario) -> None:
        path = self.scenarios_dir / f"{scenario.id}.json"
        data = {
            "id": scenario.id,
            "config": asdict(scenario.config),
            "created_at": scenario.created_at,
            "updated_at": scenario.updated_at,
            "version": scenario.version,
            "enabled": scenario.enabled,
            "tags": scenario.tags,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def update_scenario(self, scenario_id: str, config: ScenarioConfig) -> bool:
        if scenario_id in self.scenarios:
            self.scenarios[scenario_id].config = config
            self.scenarios[scenario_id].updated_at = datetime.now().isoformat()
            self._save_scenario(self.scenarios[scenario_id])
            return True
        return False

    def delete_scenario(self, scenario_id: str) -> bool:
        if scenario_id in self.scenarios:
            path = self.scenarios_dir / f"{scenario_id}.json"
            if path.exists():
                path.unlink()
            del self.scenarios[scenario_id]
            return True
        return False

    def get_scenario(self, scenario_id: str) -> Optional[TestScenario]:
        return self.scenarios.get(scenario_id)

    def list_scenarios(
        self, scenario_type: str = None, enabled_only: bool = False
    ) -> List[TestScenario]:
        results = list(self.scenarios.values())

        if scenario_type:
            results = [s for s in results if s.config.scenario_type == scenario_type]
        if enabled_only:
            results = [s for s in results if s.enabled]

        return sorted(results, key=lambda s: s.created_at, reverse=True)

    def export_scenario(self, scenario_id: str) -> Dict[str, Any]:
        scenario = self.scenarios.get(scenario_id)
        if not scenario:
            return {"error": "Scenario not found"}
        return asdict(scenario)

    def import_scenario(self, data: Dict[str, Any]) -> TestScenario:
        config = ScenarioConfig(**data["config"])
        scenario = TestScenario(
            id=data.get("id", f"scenario_{len(self.scenarios) + 1:04d}"),
            config=config,
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=datetime.now().isoformat(),
            version=data.get("version", "1.0"),
            tags=data.get("tags", []),
        )
        self.scenarios[scenario.id] = scenario
        self._save_scenario(scenario)
        return scenario

    def generate_test_code(self, scenario_id: str) -> str:
        scenario = self.scenarios.get(scenario_id)
        if not scenario:
            return "# Scenario not found"

        config = scenario.config
        player_units = [
            f'UnitConfig("{u.unit_type}", {u.count})' for u in config.player_units
        ]
        enemy_units = [
            f'UnitConfig("{u.unit_type}", {u.count})' for u in config.enemy_units
        ]

        return f'''"""
Auto-generated test for scenario: {scenario_id}
Generated: {datetime.now().isoformat()}
"""

def test_{scenario_id}():
    """Test {config.name}"""
    config = {{
        "scenario_type": "{config.scenario_type}",
        "player_units": [{", ".join(player_units)}],
        "enemy_units": [{", ".join(enemy_units)}],
        "map": "{config.map_name}",
        "difficulty": {config.difficulty},
        "time_limit": {config.time_limit_seconds}
    }}
    
    # Test implementation
    print(f"Running: {config.name}")
    print(f"Description: {config.description}")
    
    return config


if __name__ == "__main__":
    test_{scenario_id}()
'''


def create_default_scenarios(manager: ScenarioDefinitionManager) -> None:
    defaults = [
        ScenarioConfig(
            name="Zergling Rush Defense",
            description="Defend against early zergling rush",
            scenario_type=ScenarioType.RUSH_DEFENSE.value,
            player_units=[UnitConfig("Drone", 12), UnitConfig("Zergling", 6)],
            enemy_units=[UnitConfig("Zergling", 24)],
            difficulty=2,
        ),
        ScenarioConfig(
            name="Roach Hydralisk Macro",
            description="Macro battle with roach hydralisk composition",
            scenario_type=ScenarioType.MACRO_BATTLE.value,
            player_units=[UnitConfig("Roach", 20), UnitConfig("Hydralisk", 15)],
            enemy_units=[UnitConfig("Marine", 40), UnitConfig("Marauder", 10)],
            difficulty=3,
        ),
        ScenarioConfig(
            name="Mutalisk Harassment",
            description="Harass enemy economy with mutalisks",
            scenario_type=ScenarioType.HARASSMENT.value,
            player_units=[UnitConfig("Mutalisk", 12)],
            enemy_units=[UnitConfig("Probe", 20), UnitConfig("Pylon", 3)],
            difficulty=2,
        ),
        ScenarioConfig(
            name="Ultralisk BroodLord Push",
            description="Late game ultra broodlord push",
            scenario_type=ScenarioType.TEAM_FIGHT.value,
            player_units=[UnitConfig("Ultralisk", 8), UnitConfig("BroodLord", 6)],
            enemy_units=[UnitConfig("Thor", 4), UnitConfig("Battlecruiser", 2)],
            difficulty=4,
        ),
    ]

    for config in defaults:
        manager.create_scenario(config)


if __name__ == "__main__":
    manager = ScenarioDefinitionManager()
    create_default_scenarios(manager)

    print(f"[ScenarioManager] Created {len(manager.scenarios)} default scenarios:")
    for sid, s in manager.scenarios.items():
        print(f"  - {sid}: {s.config.name} ({s.config.scenario_type})")
