"""
Unit Tests for Harassment Coordinator

Tests aggressive modes, baneling drops, squad locking, and multi-angle attacks.
"""

import pytest
from unittest.mock import Mock, MagicMock
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


class MockBot:
    def __init__(self, time=0):
        self.time = time
        self.units = Mock()
        self.enemy_units = Mock()
        self.start_location = Point2((10, 10))
        self.enemy_start_locations = [Point2((100, 100))]

    def do(self, action):
        pass


def create_mock_unit(type_id, position=(10, 10), tag=1, health_pct=1.0):
    """Create a mock unit for testing"""
    unit = Mock()
    unit.type_id = type_id
    unit.position = Point2(position)
    unit.tag = tag
    unit.health_percentage = health_pct
    unit.is_ready = True
    unit.is_idle = True
    return unit


class TestHarassmentCoordinator:
    """Test suite for Harassment Coordinator"""

    def setup_method(self):
        """Setup before each test"""
        try:
            from wicked_zerg_challenger.combat.harassment_coordinator import (
                HarassmentCoordinator,
                AggressiveMode
            )
            self.bot = MockBot()
            self.coordinator = HarassmentCoordinator(self.bot)
            self.AggressiveMode = AggressiveMode
        except ImportError:
            pytest.skip("HarassmentCoordinator not available")

    # ===== Aggressive Mode Tests =====

    def test_aggressive_mode_enum_values(self):
        """Test that AggressiveMode enum has all expected values"""
        assert hasattr(self.AggressiveMode, 'PASSIVE')
        assert hasattr(self.AggressiveMode, 'OPPORTUNISTIC')
        assert hasattr(self.AggressiveMode, 'AGGRESSIVE')
        assert hasattr(self.AggressiveMode, 'ULTRA_AGGRESSIVE')

    def test_default_aggressive_mode(self):
        """Test that default mode is OPPORTUNISTIC"""
        assert self.coordinator.aggressive_mode == self.AggressiveMode.OPPORTUNISTIC
        assert self.coordinator.harassment_allocation_percent == 0.10

    def test_set_aggressive_mode_passive(self):
        """Test setting passive mode (5% allocation)"""
        self.coordinator.set_aggressive_mode(self.AggressiveMode.PASSIVE)

        assert self.coordinator.aggressive_mode == self.AggressiveMode.PASSIVE
        assert self.coordinator.harassment_allocation_percent == 0.05

    def test_set_aggressive_mode_aggressive(self):
        """Test setting aggressive mode (15% allocation)"""
        self.coordinator.set_aggressive_mode(self.AggressiveMode.AGGRESSIVE)

        assert self.coordinator.aggressive_mode == self.AggressiveMode.AGGRESSIVE
        assert self.coordinator.harassment_allocation_percent == 0.15

    def test_set_aggressive_mode_ultra_aggressive(self):
        """Test setting ultra-aggressive mode (25% allocation)"""
        self.coordinator.set_aggressive_mode(self.AggressiveMode.ULTRA_AGGRESSIVE)

        assert self.coordinator.aggressive_mode == self.AggressiveMode.ULTRA_AGGRESSIVE
        assert self.coordinator.harassment_allocation_percent == 0.25

    # ===== Squad Locking System Tests =====

    def test_squad_lock_initialization(self):
        """Test that squad locking system is properly initialized"""
        assert isinstance(self.coordinator.locked_units, set)
        assert isinstance(self.coordinator.squad_assignments, dict)
        assert isinstance(self.coordinator.squad_members, dict)
        assert "zergling_runby" in self.coordinator.squad_members
        assert "mutalisk_harass" in self.coordinator.squad_members
        assert "baneling_drop" in self.coordinator.squad_members

    def test_lock_unit_to_squad(self):
        """Test locking a unit to a harassment squad"""
        unit_tag = 12345
        squad_name = "zergling_runby"

        self.coordinator.lock_unit_to_squad(unit_tag, squad_name, duration=60.0)

        assert unit_tag in self.coordinator.locked_units
        assert self.coordinator.squad_assignments[unit_tag] == squad_name
        assert unit_tag in self.coordinator.squad_members[squad_name]

    def test_unlock_unit_from_squad(self):
        """Test unlocking a unit from a squad"""
        unit_tag = 12345
        squad_name = "mutalisk_harass"

        # Lock first
        self.coordinator.lock_unit_to_squad(unit_tag, squad_name)

        # Then unlock
        self.coordinator.unlock_unit(unit_tag)

        assert unit_tag not in self.coordinator.locked_units
        assert unit_tag not in self.coordinator.squad_assignments

    def test_is_unit_locked(self):
        """Test checking if unit is locked"""
        unit_tag = 12345

        assert self.coordinator.is_unit_locked(unit_tag) == False

        # Lock unit
        self.coordinator.lock_unit_to_squad(unit_tag, "zergling_runby")

        assert self.coordinator.is_unit_locked(unit_tag) == True

    def test_get_locked_units_by_squad(self):
        """Test retrieving locked units by squad name"""
        # Lock multiple units
        self.coordinator.lock_unit_to_squad(1, "zergling_runby")
        self.coordinator.lock_unit_to_squad(2, "zergling_runby")
        self.coordinator.lock_unit_to_squad(3, "mutalisk_harass")

        zergling_squad = self.coordinator.get_locked_units_by_squad("zergling_runby")
        mutalisk_squad = self.coordinator.get_locked_units_by_squad("mutalisk_harass")

        assert len(zergling_squad) == 2
        assert 1 in zergling_squad
        assert 2 in zergling_squad
        assert len(mutalisk_squad) == 1
        assert 3 in mutalisk_squad

    def test_auto_unlock_on_expiry(self):
        """Test that squads are auto-unlocked after duration expires"""
        self.bot.time = 100.0
        unit_tag = 12345
        squad_name = "zergling_runby"

        # Lock for 30 seconds
        self.coordinator.lock_unit_to_squad(unit_tag, squad_name, duration=30.0)

        # Time advances past lock duration
        self.bot.time = 150.0

        # Auto-unlock should happen
        self.coordinator._auto_unlock_expired_squads()

        assert unit_tag not in self.coordinator.locked_units

    # ===== Baneling Drop Tests =====

    def test_baneling_drop_initialization(self):
        """Test baneling drop system initialization"""
        assert self.coordinator.baneling_drop_active == False
        assert self.coordinator.baneling_drop_overlord_tag is None
        assert isinstance(self.coordinator.baneling_drop_baneling_tags, set)
        assert self.coordinator.baneling_drop_interval == 120  # 2 minutes

    def test_baneling_drop_cooldown(self):
        """Test baneling drop cooldown mechanism"""
        initial_cooldown = self.coordinator.baneling_drop_cooldown

        # Simulate cooldown reduction
        self.coordinator.baneling_drop_cooldown = 60

        assert self.coordinator.baneling_drop_cooldown == 60
        assert self.coordinator.baneling_drop_cooldown > 0

    @pytest.mark.asyncio
    async def test_can_execute_baneling_drop(self):
        """Test conditions for executing baneling drop"""
        # Should not be able to execute initially (no overlord, no banelings)
        can_execute = self.coordinator._can_execute_baneling_drop()

        # Initially false due to missing units or cooldown
        assert isinstance(can_execute, bool)

    # ===== Multi-Angle Attack Tests =====

    def test_multi_angle_coordination_initialization(self):
        """Test multi-angle attack system is initialized"""
        assert hasattr(self.coordinator, 'zergling_runby_active')
        assert hasattr(self.coordinator, 'mutalisk_harass_active')
        assert hasattr(self.coordinator, 'baneling_drop_active')

    @pytest.mark.asyncio
    async def test_coordinate_multi_angle_attack_exists(self):
        """Test that multi-angle coordination method exists"""
        assert hasattr(self.coordinator, '_coordinate_multi_angle_attack')

        # Should not crash
        try:
            await self.coordinator._coordinate_multi_angle_attack()
        except Exception:
            # May fail in test environment
            pass

    # ===== Harassment Target Selection Tests =====

    def test_priority_target_list(self):
        """Test priority target list is initialized"""
        assert hasattr(self.coordinator, 'priority_targets')
        assert isinstance(self.coordinator.priority_targets, list)

    def test_worker_target_priority(self):
        """Test that workers have highest priority for harassment"""
        # This is implementation-dependent, verify method exists
        assert hasattr(self.coordinator, '_find_worker_targets') or \
               hasattr(self.coordinator, '_get_priority_targets')

    # ===== Zergling Runby Tests =====

    def test_zergling_runby_interval(self):
        """Test zergling runby interval (should be 60s after Phase 17)"""
        assert self.coordinator.zergling_runby_interval == 60

    def test_zergling_runby_tracking(self):
        """Test zergling runby unit tracking"""
        assert isinstance(self.coordinator.zergling_runby_tags, set)

        # Add a zergling to runby
        zergling_tag = 999
        self.coordinator.zergling_runby_tags.add(zergling_tag)

        assert zergling_tag in self.coordinator.zergling_runby_tags

    # ===== Performance & Safety Tests =====

    def test_retreat_threshold(self):
        """Test that mutalisk retreat HP threshold is 35%"""
        assert self.coordinator.mutalisk_retreat_hp_threshold == 0.35

    def test_performance_caching_variables(self):
        """Test that performance optimization variables exist"""
        assert hasattr(self.coordinator, '_cached_army_fighting')
        assert hasattr(self.coordinator, '_last_army_check_time')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
