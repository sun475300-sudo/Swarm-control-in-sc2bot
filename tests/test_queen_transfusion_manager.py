"""
Unit Tests for Queen Transfusion Manager

Tests the smart transfusion priority system.
"""

from unittest.mock import MagicMock, Mock

import pytest

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    pytest.skip("sc2 library not available", allow_module_level=True)


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
        # Handle unit-like objects with position attribute
        if (
            hasattr(other, "position")
            and hasattr(other.position, "x")
            and isinstance(other.position.x, (int, float))
        ):
            ox, oy = other.position.x, other.position.y
        # Handle Point2-like objects with numeric x/y
        elif hasattr(other, "x") and isinstance(other.x, (int, float)):
            ox, oy = other.x, other.y
        else:
            return 5  # Default distance
        return ((unit.position.x - ox) ** 2 + (unit.position.y - oy) ** 2) ** 0.5

    unit.distance_to = distance_to
    return unit


class TestQueenTransfusionManager:
    """Test suite for Queen Transfusion Manager"""

    def setup_method(self):
        """Setup before each test"""
        try:
            from wicked_zerg_challenger.economy.queen_transfusion_manager import (
                QueenTransfusionManager,
            )

            self.bot = MockBot()
            self.manager = QueenTransfusionManager(self.bot)
        except ImportError:
            pytest.skip("QueenTransfusionManager not available")

    def test_priority_ordering(self):
        """Test that priority map is correctly ordered"""
        from wicked_zerg_challenger.economy.queen_transfusion_manager import (
            QueenTransfusionManager,
        )

        # Ultralisk should have highest priority
        assert (
            QueenTransfusionManager.HEAL_PRIORITY[UnitTypeId.ULTRALISK]
            > QueenTransfusionManager.HEAL_PRIORITY[UnitTypeId.ZERGLING]
        )

        # Broodlord should have higher priority than Mutalisk
        assert (
            QueenTransfusionManager.HEAL_PRIORITY[UnitTypeId.BROODLORD]
            > QueenTransfusionManager.HEAL_PRIORITY[UnitTypeId.MUTALISK]
        )

    def test_cannot_heal_blacklist(self):
        """Test that blacklisted units cannot be healed"""
        from wicked_zerg_challenger.economy.queen_transfusion_manager import (
            QueenTransfusionManager,
        )

        # Banelings should not be healable
        assert UnitTypeId.BANELING in QueenTransfusionManager.CANNOT_HEAL

        # Broodlings should not be healable
        assert UnitTypeId.BROODLING in QueenTransfusionManager.CANNOT_HEAL

    def test_valid_transfusion_target_hp_threshold(self):
        """Test HP threshold for transfusion"""
        queen = create_mock_unit(
            UnitTypeId.QUEEN, health_pct=1.0, health_max=200, tag=1
        )
        # Use realistic health_max (145 for Roach) so overheal check passes
        # hp_missing = 145 * 0.5 = 72.5, overheal threshold = 125 * 0.5 = 62.5
        target_low_hp = create_mock_unit(
            UnitTypeId.ROACH, health_pct=0.5, health_max=145, tag=2
        )
        target_high_hp = create_mock_unit(
            UnitTypeId.ROACH, health_pct=0.7, health_max=145, tag=3
        )

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
        queen = create_mock_unit(
            UnitTypeId.QUEEN, health_pct=1.0, health_max=200, position=(0, 0), tag=1
        )
        target_close = create_mock_unit(
            UnitTypeId.ROACH, health_pct=0.5, health_max=145, position=(5, 0), tag=2
        )
        target_far = create_mock_unit(
            UnitTypeId.ROACH, health_pct=0.5, health_max=145, position=(50, 0), tag=3
        )

        # Close target should be valid (distance=5 <= 7)
        assert self.manager._is_valid_transfusion_target(target_close, queen) == True

        # Far target should be invalid (distance=50 > 7 range)
        assert self.manager._is_valid_transfusion_target(target_far, queen) == False

    def test_statistics_tracking(self):
        """Test that statistics are properly tracked"""
        target = create_mock_unit(
            UnitTypeId.ULTRALISK, health_pct=0.3, health_max=500, tag=1
        )

        initial_count = self.manager.transfusions_performed

        self.manager._record_transfusion(target)

        # Count should increment
        assert self.manager.transfusions_performed == initial_count + 1

        # Unit type should be tracked
        assert UnitTypeId.ULTRALISK in self.manager.transfusions_per_unit_type

    def test_best_target_selection(self):
        """Test that best target is selected by priority"""
        queen = create_mock_unit(
            UnitTypeId.QUEEN, health_pct=1.0, health_max=200, tag=1
        )

        # Create multiple damaged units with realistic health_max
        # Ultralisk: 500 HP, Zergling: 35 HP, Roach: 145 HP
        ultra = create_mock_unit(
            UnitTypeId.ULTRALISK, health_pct=0.5, health_max=500, tag=2
        )
        zergling = create_mock_unit(
            UnitTypeId.ZERGLING, health_pct=0.3, health_max=145, tag=3
        )
        roach = create_mock_unit(
            UnitTypeId.ROACH, health_pct=0.4, health_max=145, tag=4
        )

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

    # ===== Edge cases added during PR #215 cleanup =====

    def test_overheal_guard_rejects_nearly_full_target(self):
        """
        Transfusion restores 125 HP; we shouldn't waste it on a target
        that's only missing a tiny amount (<50% effectiveness threshold).
        """
        queen = create_mock_unit(
            UnitTypeId.QUEEN, health_pct=1.0, health_max=200, tag=1
        )
        # Roach: 145 max HP. At 58% (~84 HP), it would qualify on the
        # health_percentage check but it's only missing ~61 HP, which is
        # under TRANSFUSION_HP_RESTORE * 0.5 = 62.5 → reject.
        almost_full = create_mock_unit(
            UnitTypeId.ROACH, health_pct=0.58, health_max=145, tag=2
        )
        assert (
            self.manager._is_valid_transfusion_target(almost_full, queen) is False
        ), "Should reject target where transfusion would be <50% effective"

    def test_zergling_never_eligible_due_to_low_max_hp(self):
        """
        Implicit consequence of the overheal guard: zerglings have only
        35 max HP, so even a 1-HP zergling can't accept 62.5+ HP of
        transfusion. This is intentional — but we want regression
        coverage so it's not silently flipped by future tuning.
        """
        queen = create_mock_unit(
            UnitTypeId.QUEEN, health_pct=1.0, health_max=200, tag=1
        )
        nearly_dead = create_mock_unit(
            UnitTypeId.ZERGLING, health_pct=0.05, health_max=35, tag=2
        )
        assert (
            self.manager._is_valid_transfusion_target(nearly_dead, queen) is False
        ), "Zergling cannot accept enough HP for transfusion to be efficient"

    def test_critical_hp_beats_priority_in_tiebreak(self):
        """
        Sort key: (-priority, -critical_flag, health_pct). When two units
        share priority, the one under TRANSFUSION_CRITICAL_HP must be
        chosen first. We use two roaches (same priority, same max HP).
        """
        queen = create_mock_unit(
            UnitTypeId.QUEEN, health_pct=1.0, health_max=200, position=(0, 0), tag=1
        )
        # 25% HP → under TRANSFUSION_CRITICAL_HP (0.3)
        critical = create_mock_unit(
            UnitTypeId.ROACH,
            health_pct=0.25,
            health_max=145,
            position=(1, 0),
            tag=2,
        )
        # 45% HP → above critical but still valid (below 0.6 threshold)
        damaged = create_mock_unit(
            UnitTypeId.ROACH,
            health_pct=0.45,
            health_max=145,
            position=(1, 0),
            tag=3,
        )

        class MockUnits:
            def __iter__(self):
                return iter([damaged, critical])  # critical second on purpose

        best = self.manager._find_best_transfusion_target(queen, MockUnits())
        assert best is critical, "Critical-HP target should beat higher-HP peer"

    def test_targeted_set_blocks_double_heal(self):
        """
        Once a queen targets a unit this iteration, the next queen's
        target selection must skip it. Guarantees we don't burn two
        queens' energy on the same low-HP target.
        """
        queen = create_mock_unit(
            UnitTypeId.QUEEN, health_pct=1.0, health_max=200, position=(0, 0), tag=1
        )
        target = create_mock_unit(
            UnitTypeId.ROACH, health_pct=0.3, health_max=145, position=(1, 0), tag=99
        )

        class MockUnits:
            def __iter__(self):
                return iter([target])

        # First lookup: target available
        first = self.manager._find_best_transfusion_target(queen, MockUnits())
        assert first is target

        # Mark it as targeted, then re-query
        self.manager._targeted_this_iter.add(target.tag)
        second = self.manager._find_best_transfusion_target(queen, MockUnits())
        assert second is None, "Already-targeted unit must not be re-selected"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
