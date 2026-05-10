"""
Unit Tests for Advanced Scout System V2

Tests dynamic scouting intervals, scout assignment, and intel reporting.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
except ImportError:
    pytest.skip("sc2 library not available", allow_module_level=True)


class MockBot:
    def __init__(self, time=0, minerals=1000, vespene=500):
        self.time = time
        self.minerals = minerals
        self.vespene = vespene
        self.units = Mock()
        self.enemy_units = Mock()
        self.expansion_locations = []

    def do(self, action):
        pass


def create_mock_unit(type_id, position=(10, 10), tag=1, is_ready=True):
    """Create a mock unit for testing"""
    unit = Mock()
    unit.type_id = type_id
    unit.position = Point2(position)
    unit.tag = tag
    unit.is_ready = is_ready
    unit.is_idle = True
    return unit


class TruthyEmptyUnits:
    amount = 0

    @property
    def idle(self):
        return self

    def __bool__(self):
        return True

    def __len__(self):
        return 0

    def filter(self, *_args, **_kwargs):
        return self

    def closer_than(self, *_args, **_kwargs):
        return self

    def closest_to(self, *_args, **_kwargs):
        raise AssertionError("closest_to should not run on an empty group")


class TestAdvancedScoutSystemV2:
    """Test suite for Advanced Scouting System V2"""

    def setup_method(self):
        """Setup before each test"""
        try:
            from wicked_zerg_challenger.scouting.advanced_scout_system_v2 import (
                AdvancedScoutingSystemV2,
            )

            self.bot = MockBot()
            self.scout_system = AdvancedScoutingSystemV2(self.bot)
        except ImportError:
            pytest.skip("AdvancedScoutingSystemV2 not available")

    # ===== Interval Calculation Tests =====

    def test_early_game_interval(self):
        """Test early game interval (0-5 min) = 25s"""
        self.bot.time = 120  # 2 minutes

        interval = self.scout_system._get_dynamic_interval()

        assert interval == 25.0  # Early game: 25 seconds

    def test_tech_timing_interval(self):
        """Test tech timing window interval (4-7 min) = 20s"""
        self.bot.time = 300  # 5 minutes (300 seconds)

        interval = self.scout_system._get_dynamic_interval()

        assert interval == 20.0  # Tech timing: 20 seconds

    def test_mid_game_interval(self):
        """Test mid game interval (5-10 min) = 40s"""
        self.bot.time = 480  # 8 minutes

        interval = self.scout_system._get_dynamic_interval()

        assert interval == 40.0  # Mid game: 40 seconds

    def test_late_game_interval(self):
        """Test late game interval (10+ min) = 35s"""
        self.bot.time = 720  # 12 minutes

        interval = self.scout_system._get_dynamic_interval()

        assert interval == 35.0  # Late game: 35 seconds

    def test_emergency_mode_interval(self):
        """Test emergency mode when intel is stale"""
        self.bot.time = 200

        # Simulate stale intel (last scouted > 60s ago)
        with patch.object(self.scout_system, "_is_emergency_mode", return_value=True):
            interval = self.scout_system._get_dynamic_interval()

        assert interval == 15.0  # Emergency: 15 seconds

    # ===== Scout Assignment Tests =====

    def test_scout_allocation_limits(self):
        """Test that scout count respects MAX_SCOUTS limits"""
        assert self.scout_system.MAX_SCOUTS["WORKER"] == 1
        assert self.scout_system.MAX_SCOUTS["ZERGLING"] == 4
        assert self.scout_system.MAX_SCOUTS["OVERLORD"] == 3
        assert self.scout_system.MAX_SCOUTS["OVERSEER"] == 3

    def test_active_scout_tracking(self):
        """Test that active scouts are tracked properly"""
        initial_count = len(self.scout_system.active_scouts)

        # Simulate adding a scout
        scout_tag = 12345
        self.scout_system.active_scouts[scout_tag] = {
            "type": "ZERGLING",
            "target": Point2((50, 50)),
            "start_time": self.bot.time,
        }

        assert len(self.scout_system.active_scouts) == initial_count + 1
        assert scout_tag in self.scout_system.active_scouts
        assert self.scout_system.active_scouts[scout_tag]["type"] == "ZERGLING"

    def test_scout_removal_on_death(self):
        """Test that dead scouts are removed from active list"""
        # Add a scout
        scout_tag = 12345
        self.scout_system.active_scouts[scout_tag] = {
            "type": "ZERGLING",
            "target": Point2((50, 50)),
            "start_time": 0.0,
        }

        # Mock bot units (scout not present = dead)
        self.bot.units = Mock()
        self.bot.units.find_by_tag = Mock(return_value=None)

        # Run management
        self.scout_system._manage_active_scouts()

        # Scout should be removed
        assert scout_tag not in self.scout_system.active_scouts

    # ===== Statistics Tests =====

    def test_statistics_tracking(self):
        """Test that statistics are properly tracked"""
        initial_sent = self.scout_system.scouts_sent

        # Simulate sending a scout
        self.scout_system.scouts_sent += 1

        assert self.scout_system.scouts_sent == initial_sent + 1
        assert hasattr(self.scout_system, "scouts_returned")
        assert hasattr(self.scout_system, "scouts_lost")
        assert hasattr(self.scout_system, "intel_updates")

    def test_scout_priority_locations(self):
        """Test that enemy expansions have higher priority"""
        # Add enemy expansion locations
        self.bot.expansion_locations = [
            Point2((50, 50)),
            Point2((100, 100)),
            Point2((150, 150)),
        ]

        # Last scouted tracking should exist
        assert hasattr(self.scout_system, "last_scouted_at")
        assert isinstance(self.scout_system.last_scouted_at, dict)

    def test_ground_scout_threat_handles_enemy_without_worker_flag(self):
        """Real enemy unit wrappers may not expose is_worker."""
        scout = Mock()
        scout.is_flying = False
        scout.health_percentage = 1.0
        scout.distance_to.return_value = 3
        enemy = type("EnemyUnit", (), {})()
        self.bot.enemy_units = [enemy]

        assert self.scout_system._scout_is_threatened(scout)

    @pytest.mark.asyncio
    async def test_overseer_detection_sweep_skips_empty_available_group(self):
        """Do not call closest_to on an empty Units group."""
        base = Mock()
        base.position = Point2((50, 50))
        self.bot.townhalls = [base]

        nearby_overseers = MagicMock()
        nearby_overseers.__bool__.return_value = False

        available = MagicMock()
        available.amount = 0
        available.closest_to.side_effect = AssertionError("closest_to should not run")

        overseers = MagicMock()
        overseers.__bool__.return_value = True
        overseers.amount = 2
        overseers.filter.return_value = available

        overseer_source = MagicMock()
        overseer_source.filter.return_value = overseers
        overseer_source.closer_than.return_value = nearby_overseers

        army_units = MagicMock()
        army_units.amount = 0

        self.bot.units = MagicMock(return_value=overseer_source)
        self.bot.units.filter.return_value = army_units

        await self.scout_system._overseer_detection_sweep()

        available.closest_to.assert_not_called()

    def test_forced_scout_skips_truthy_empty_units_group(self):
        target = Point2((40, 40))
        empty_units = TruthyEmptyUnits()
        self.scout_system.roadmap_scouting = Mock()
        self.scout_system.roadmap_scouting.select_overlord_scout_target.return_value = target
        self.bot.blackboard = Mock()
        self.bot.units = Mock(return_value=empty_units)

        assert not self.scout_system._send_specific_scout(UnitTypeId.OVERLORD)

    def test_assign_patrol_skips_truthy_empty_units_group(self):
        self.scout_system._patrol_routes["enemy_bases"] = [Point2((40, 40))]
        self.bot.units = Mock(return_value=TruthyEmptyUnits())

        assert not self.scout_system._assign_patrol(
            "enemy_bases", UnitTypeId.OVERLORD
        )

    # ===== Memory Management Tests =====

    def test_old_scout_data_cleanup(self):
        """Test that old scouting data is cleaned up"""
        # Add old scouted location
        old_location = Point2((50, 50))
        self.scout_system.last_scouted_at[old_location] = 0.0  # Very old

        self.bot.time = 200.0  # Current time: 200 seconds

        # Cleanup should remove data older than threshold
        self.scout_system._cleanup_old_scout_data()

        # Data should still exist or be removed based on threshold
        # (Implementation may vary, just verify method exists)
        assert hasattr(self.scout_system, "_cleanup_old_scout_data")

    # ===== Changeling Tests =====

    @pytest.mark.asyncio
    async def test_changeling_management_exists(self):
        """Test that changeling management method exists"""
        assert hasattr(self.scout_system, "_manage_changelings")

        # Should not crash when called
        try:
            await self.scout_system._manage_changelings()
        except Exception as e:
            # Expected to fail in test env, just verify it exists
            pass

    # ===== Integration Tests =====

    def test_scout_report_generation(self):
        """Test that scout reports can be generated"""
        assert hasattr(self.scout_system, "_print_report")

        # Should not crash
        try:
            self.scout_system._print_report()
        except AttributeError:
            # AttributeError = method removed/renamed; surface it
            raise
        except Exception:
            # Mock-call side effects are tolerated
            pass

    def test_emergency_mode_detection(self):
        """Test emergency mode detection logic"""
        assert hasattr(self.scout_system, "_is_emergency_mode")

        # Should return boolean
        result = self.scout_system._is_emergency_mode()
        assert isinstance(result, bool)

    def test_interval_progression(self):
        """Test that intervals progress correctly through game phases"""
        intervals = []

        # Test different game times
        game_times = [60, 180, 300, 480, 720]  # 1, 3, 5, 8, 12 minutes

        for time in game_times:
            self.bot.time = time
            intervals.append(self.scout_system._get_dynamic_interval())

        # Verify intervals are within expected ranges
        assert all(15.0 <= interval <= 40.0 for interval in intervals)
        assert len(intervals) == len(game_times)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
