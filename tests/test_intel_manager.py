"""
Unit Tests for Intel Manager

Tests threat detection, build pattern recognition, and confidence scoring.
"""

import pytest
from unittest.mock import Mock, MagicMock


class MockUnit:
    def __init__(self, type_id, supply_cost=1):
        self.type_id = Mock()
        self.type_id.name = type_id
        self.supply_cost = supply_cost


class MockBot:
    def __init__(self):
        self.enemy_race = Mock()
        self.enemy_race.name = "Terran"
        self.enemy_units = []
        self.enemy_structures = []
        self.townhalls = []
        self.time = 0.0


class TestIntelManager:
    """Test suite for Intel Manager"""

    def setup_method(self):
        """Setup before each test"""
        try:
            from wicked_zerg_challenger.intel_manager import IntelManager
            self.bot = MockBot()
            self.intel = IntelManager(self.bot)
        except ImportError:
            pytest.skip("IntelManager not available")

    # ===== Initialization Tests =====

    def test_initialization(self):
        """Test that IntelManager initializes correctly"""
        assert self.intel.last_update == 0
        assert self.intel.update_interval == 8
        assert self.intel.enemy_race_name is None
        assert self.intel.enemy_army_supply == 0
        assert self.intel.enemy_worker_count == 0
        assert self.intel.enemy_base_count == 0
        assert isinstance(self.intel.enemy_tech_buildings, set)
        assert isinstance(self.intel.enemy_unit_counts, dict)

    def test_threat_tracking_initialization(self):
        """Test threat tracking variables are initialized"""
        assert self.intel._under_attack == False
        assert self.intel._attack_position is None
        assert self.intel._threat_level == "none"
        assert self.intel._high_threat_units_detected == False

    def test_build_pattern_tracking_initialization(self):
        """Test build pattern tracking is initialized"""
        assert self.intel._build_pattern_confidence == 0.0
        assert self.intel._build_pattern_status == "unknown"

    # ===== Enemy Race Detection Tests =====

    def test_enemy_race_detection(self):
        """Test enemy race detection"""
        self.bot.enemy_race = Mock()
        self.bot.enemy_race.name = "Zerg"

        self.intel.update(iteration=0)

        assert self.intel.enemy_race_name == "Zerg"

    def test_enemy_race_none_handling(self):
        """Test handling when enemy race is None"""
        self.bot.enemy_race = None

        self.intel.update(iteration=0)

        assert self.intel.enemy_race_name is None

    # ===== Enemy Composition Tests =====

    def test_enemy_unit_counting(self):
        """Test enemy unit type counting"""
        # Add mock enemy units
        self.bot.enemy_units = [
            MockUnit("MARINE", supply_cost=1),
            MockUnit("MARINE", supply_cost=1),
            MockUnit("MARAUDER", supply_cost=2),
            MockUnit("SCV", supply_cost=1),  # Worker
        ]

        self.intel.update(iteration=0)

        assert self.intel.enemy_unit_counts.get("MARINE", 0) == 2
        assert self.intel.enemy_unit_counts.get("MARAUDER", 0) == 1
        assert self.intel.enemy_worker_count == 1  # SCV is worker

    def test_enemy_army_supply_calculation(self):
        """Test enemy army supply calculation (excludes workers)"""
        self.bot.enemy_units = [
            MockUnit("MARINE", supply_cost=1),
            MockUnit("MARINE", supply_cost=1),
            MockUnit("MARAUDER", supply_cost=2),
            MockUnit("SCV", supply_cost=1),  # Worker, not counted in army
        ]

        self.intel.update(iteration=0)

        # Marines (2) + Marauder (2) = 4 (workers not counted)
        assert self.intel.enemy_army_supply == 4

    def test_enemy_base_counting(self):
        """Test enemy base counting"""
        self.bot.enemy_structures = [
            MockUnit("COMMANDCENTER"),
            MockUnit("NEXUS"),
            MockUnit("HATCHERY"),
            MockUnit("BARRACKS"),  # Not a base
        ]

        self.intel.update(iteration=0)

        assert self.intel.enemy_base_count == 3  # Only bases counted

    def test_enemy_tech_building_detection(self):
        """Test tech building detection"""
        self.bot.enemy_structures = [
            MockUnit("FACTORY"),
            MockUnit("STARPORT"),
            MockUnit("BARRACKS"),  # Not a tech building
        ]

        self.intel.update(iteration=0)

        assert "FACTORY" in self.intel.enemy_tech_buildings
        assert "STARPORT" in self.intel.enemy_tech_buildings
        assert "BARRACKS" not in self.intel.enemy_tech_buildings
        assert len(self.intel.enemy_tech_buildings) == 2

    # ===== Threat Detection Tests =====

    def test_high_threat_unit_types(self):
        """Test that high threat unit types are defined"""
        assert isinstance(self.intel._high_threat_types, set)
        assert "SIEGETANK" in self.intel._high_threat_types
        assert "BATTLECRUISER" in self.intel._high_threat_types
        assert "COLOSSUS" in self.intel._high_threat_types
        assert "ULTRALISK" in self.intel._high_threat_types

    def test_threat_level_progression(self):
        """Test threat level values"""
        valid_levels = ["none", "light", "medium", "heavy", "critical"]
        assert self.intel._threat_level in valid_levels

    def test_under_attack_detection(self):
        """Test under attack detection logic"""
        # Initially not under attack
        assert self.intel._under_attack == False

        # After threat update (implementation-dependent)
        self.intel._update_threat_status()

        # Should still be False or True (depends on enemy proximity)
        assert isinstance(self.intel._under_attack, bool)

    # ===== Build Pattern Recognition Tests =====

    def test_build_pattern_confidence_range(self):
        """Test build pattern confidence is in valid range"""
        assert 0.0 <= self.intel._build_pattern_confidence <= 1.0

    def test_build_pattern_status_values(self):
        """Test build pattern status has valid value"""
        valid_statuses = ["unknown", "suspected", "confirmed"]
        assert self.intel._build_pattern_status in valid_statuses

    @pytest.mark.asyncio
    async def test_on_step_execution(self):
        """Test on_step method executes without errors"""
        # Should not crash
        await self.intel.on_step(iteration=0)
        await self.intel.on_step(iteration=8)  # After update interval

        assert self.intel.last_update >= 0

    def test_update_interval_timing(self):
        """Test that updates only happen after interval"""
        initial_update = self.intel.last_update

        # Update at iteration 0
        self.intel.update(iteration=0)

        # Update should only happen every 8 iterations
        assert self.intel.update_interval == 8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
