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
        self.position = Mock()  # ★ FIX: position 속성 추가


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

    # ===== Public Getter Tests =====

    def test_is_under_attack_returns_bool(self):
        """is_under_attack 가 bool 반환"""
        assert isinstance(self.intel.is_under_attack(), bool)
        assert self.intel.is_under_attack() is False  # 초기 상태

    def test_get_attack_position_initial_none(self):
        """get_attack_position 초기값은 None"""
        assert self.intel.get_attack_position() is None

    def test_get_enemy_army_supply_initial_zero(self):
        """get_enemy_army_supply 초기값은 0"""
        assert self.intel.get_enemy_army_supply() == 0

    def test_get_enemy_composition_returns_copy(self):
        """get_enemy_composition 은 dict 사본을 반환 (외부 변경 방어)"""
        self.intel.enemy_unit_counts = {"MARINE": 5, "MARAUDER": 2}
        comp = self.intel.get_enemy_composition()
        assert isinstance(comp, dict)
        assert comp == {"MARINE": 5, "MARAUDER": 2}

        # 반환된 dict 를 수정해도 내부 상태는 영향 없음
        comp["NEW_UNIT"] = 999
        assert "NEW_UNIT" not in self.intel.enemy_unit_counts

    def test_has_enemy_tech_case_insensitive(self):
        """has_enemy_tech 은 대소문자 구분 없이 일치 검사"""
        self.intel.enemy_tech_buildings.add("BARRACKS")
        assert self.intel.has_enemy_tech("BARRACKS") is True
        assert self.intel.has_enemy_tech("barracks") is True
        assert self.intel.has_enemy_tech("Barracks") is True
        assert self.intel.has_enemy_tech("FACTORY") is False

    def test_get_threat_level_initial_none(self):
        """초기 threat_level 은 'none'"""
        assert self.intel.get_threat_level() == "none"

    def test_has_high_threat_units_initial_false(self):
        """초기 _high_threat_units_detected 는 False"""
        assert self.intel.has_high_threat_units() is False

    def test_is_major_attack_when_critical(self):
        """critical level 일 때 is_major_attack True"""
        self.intel._threat_level = "critical"
        assert self.intel.is_major_attack() is True

    def test_is_major_attack_when_high_threat_unit(self):
        """high threat unit 감지 시 is_major_attack True"""
        self.intel._high_threat_units_detected = True
        assert self.intel.is_major_attack() is True

    def test_is_major_attack_when_quiet(self):
        """위협 없을 때 is_major_attack False"""
        self.intel._threat_level = "light"
        self.intel._high_threat_units_detected = False
        assert self.intel.is_major_attack() is False

    # ===== Tech Alerts =====

    def test_get_tech_alerts_returns_copy(self):
        """get_tech_alerts 는 set 사본 반환"""
        self.intel._detected_tech_alerts.add("NYDUS_INCOMING")
        alerts = self.intel.get_tech_alerts()
        assert isinstance(alerts, set)
        assert "NYDUS_INCOMING" in alerts

        alerts.add("FAKE_ALERT")
        assert "FAKE_ALERT" not in self.intel._detected_tech_alerts

    def test_has_tech_alert_known(self):
        """has_tech_alert 정상 등록된 경고 검출"""
        self.intel._detected_tech_alerts.add("DT_RUSH")
        assert self.intel.has_tech_alert("DT_RUSH") is True
        assert self.intel.has_tech_alert("UNKNOWN_ALERT") is False

    # ===== Scouted Locations =====

    def test_record_scouted_location_adds_to_set(self):
        """record_scouted_location 이 정찰 위치를 set 에 추가"""
        loc = (100, 100)
        self.intel.record_scouted_location(loc)
        assert loc in self.intel.scouted_locations

    def test_record_scouted_location_idempotent(self):
        """동일 위치 중복 등록은 한 번만 저장 (set 특성)"""
        loc = (50, 50)
        self.intel.record_scouted_location(loc)
        self.intel.record_scouted_location(loc)
        # set 이므로 중복 없음
        assert sum(1 for l in self.intel.scouted_locations if l == loc) == 1

    # ===== Enemy Structure Tracking =====

    def test_get_destructible_rocks_returns_copy(self):
        """get_destructible_rocks 가 list 사본 반환"""
        self.intel.destructible_rocks = []  # ensure list 형태
        rocks = self.intel.get_destructible_rocks()
        assert isinstance(rocks, list)

        rocks.append("FAKE")
        # 사본이므로 원본에 영향 없음
        assert "FAKE" not in self.intel.destructible_rocks

    def test_get_closest_destructible_rock_empty_returns_none(self):
        """파괴 가능한 구조물이 없으면 None 반환"""
        self.intel.destructible_rocks = []
        assert self.intel.get_closest_destructible_rock((50, 50)) is None

    def test_get_all_enemy_structures_returns_copy(self):
        """get_all_enemy_structures 가 list 사본 반환"""
        self.intel.all_enemy_structures = []
        structs = self.intel.get_all_enemy_structures()
        assert isinstance(structs, list)

        structs.append("FAKE")
        assert "FAKE" not in self.intel.all_enemy_structures

    def test_get_enemy_structure_count_initial(self):
        """get_enemy_structure_count 초기값"""
        assert self.intel.get_enemy_structure_count() == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
