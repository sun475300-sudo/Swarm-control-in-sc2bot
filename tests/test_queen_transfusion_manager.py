"""
Unit Tests for Queen Transfusion Manager

Tests the smart transfusion priority system.
"""

import pytest
from unittest.mock import Mock, MagicMock
from sc2.ids.unit_typeid import UnitTypeId


# Mock imports for testing
class MockBot:
    def __init__(self):
        self.time = 0
        self.units = Mock()
        self.enemy_units = Mock()

    def do(self, action):
        pass


def create_mock_unit(type_id, health_pct=1.0, health_max=100, position=(10, 10), tag=1):
    """Create a mock unit for testing"""
    unit = Mock()
    unit.type_id = type_id
    unit.health_percentage = health_pct
    unit.health = health_pct * health_max
    unit.health_max = health_max
    unit.position = Mock(x=position[0], y=position[1])
    unit.tag = tag
    unit.is_biological = True
    unit.is_ready = True

    def distance_to(other):
        if hasattr(other, 'x'):
            return abs(unit.position.x - other.x) + abs(unit.position.y - other.y)
        return 5  # Default distance

    unit.distance_to = distance_to
    return unit


class TestQueenTransfusionManager:
    """Test suite for Queen Transfusion Manager"""

    def setup_method(self):
        """Setup before each test"""
        try:
            from wicked_zerg_challenger.economy.queen_transfusion_manager import QueenTransfusionManager
            self.bot = MockBot()
            self.manager = QueenTransfusionManager(self.bot)
        except ImportError:
            pytest.skip("QueenTransfusionManager not available")

    def test_priority_ordering(self):
        """Test that priority map is correctly ordered"""
        from wicked_zerg_challenger.economy.queen_transfusion_manager import QueenTransfusionManager

        # Ultralisk should have highest priority
        assert QueenTransfusionManager.HEAL_PRIORITY[UnitTypeId.ULTRALISK] > \
               QueenTransfusionManager.HEAL_PRIORITY[UnitTypeId.ZERGLING]

        # Broodlord should have higher priority than Mutalisk
        assert QueenTransfusionManager.HEAL_PRIORITY[UnitTypeId.BROODLORD] > \
               QueenTransfusionManager.HEAL_PRIORITY[UnitTypeId.MUTALISK]

    def test_cannot_heal_blacklist(self):
        """Test that blacklisted units cannot be healed"""
        from wicked_zerg_challenger.economy.queen_transfusion_manager import QueenTransfusionManager

        # Banelings should not be healable
        assert UnitTypeId.BANELING in QueenTransfusionManager.CANNOT_HEAL

        # Broodlings should not be healable
        assert UnitTypeId.BROODLING in QueenTransfusionManager.CANNOT_HEAL

    def test_valid_transfusion_target_hp_threshold(self):
        """Test HP threshold for transfusion"""
        queen = create_mock_unit(UnitTypeId.QUEEN, health_pct=1.0, tag=1)
        target_low_hp = create_mock_unit(UnitTypeId.ROACH, health_pct=0.5, tag=2)
        target_high_hp = create_mock_unit(UnitTypeId.ROACH, health_pct=0.7, tag=3)

        # 50% HP should be valid (below 60% threshold)
        assert self.manager._is_valid_transfusion_target(target_low_hp, queen) == True

        # 70% HP should be invalid (above 60% threshold)
        assert self.manager._is_valid_transfusion_target(target_high_hp, queen) == False

    def test_blacklisted_unit_not_valid(self):
        """Test that blacklisted units are not valid targets"""
        queen = create_mock_unit(UnitTypeId.QUEEN, health_pct=1.0, tag=1)
        baneling = create_mock_unit(UnitTypeId.BANELING, health_pct=0.3, tag=2)

        # Baneling should not be valid even at low HP
        assert self.manager._is_valid_transfusion_target(baneling, queen) == False

    def test_range_check(self):
        """Test that range is properly checked"""
        queen = create_mock_unit(UnitTypeId.QUEEN, health_pct=1.0, position=(0, 0), tag=1)
        target_close = create_mock_unit(UnitTypeId.ROACH, health_pct=0.5, position=(5, 0), tag=2)
        target_far = create_mock_unit(UnitTypeId.ROACH, health_pct=0.5, position=(50, 0), tag=3)

        # Close target should be valid
        assert self.manager._is_valid_transfusion_target(target_close, queen) == True

        # Far target should be invalid (> 7 range)
        assert self.manager._is_valid_transfusion_target(target_far, queen) == False

    def test_statistics_tracking(self):
        """Test that statistics are properly tracked"""
        target = create_mock_unit(UnitTypeId.ULTRALISK, health_pct=0.3, health_max=500, tag=1)

        initial_count = self.manager.transfusions_performed

        self.manager._record_transfusion(target)

        # Count should increment
        assert self.manager.transfusions_performed == initial_count + 1

        # Unit type should be tracked
        assert UnitTypeId.ULTRALISK in self.manager.transfusions_per_unit_type

    def test_best_target_selection(self):
        """Test that best target is selected by priority"""
        queen = create_mock_unit(UnitTypeId.QUEEN, health_pct=1.0, tag=1)

        # Create multiple damaged units
        ultra = create_mock_unit(UnitTypeId.ULTRALISK, health_pct=0.5, tag=2)
        zergling = create_mock_unit(UnitTypeId.ZERGLING, health_pct=0.3, tag=3)
        roach = create_mock_unit(UnitTypeId.ROACH, health_pct=0.4, tag=4)

        class MockUnits:
            def __iter__(self):
                return iter([ultra, zergling, roach])

        damaged_units = MockUnits()

        # Should select Ultralisk (highest priority)
        best = self.manager._find_best_transfusion_target(queen, damaged_units)

        assert best == ultra  # Ultralisk should be selected despite higher HP

    def test_get_statistics(self):
        """Test statistics reporting"""
        stats = self.manager.get_statistics()

        assert "total_transfusions" in stats
        assert "total_hp_healed" in stats
        assert "transfusions_by_unit" in stats
        assert "avg_hp_per_transfusion" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
