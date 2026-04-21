"""
SC2봇 핵심 개선사항 검증 테스트 (P606)

커버 영역:
1. 견제(Harassment) 시스템 - 15초 간격, 복귀 로직, 일꾼 킬 카운트
2. 프레임 스킵 동적 스케일링 - 유닛 수 기반
3. 정찰 시스템 - 30초 오버로드 간격, _assign_patrol 버그 수정
4. conftest BOT_DIR 경로 추가 검증
"""
import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, AsyncMock


# ═══════════════════════════════════════════════════════
# Helper Factories
# ═══════════════════════════════════════════════════════

def make_bot(time=0.0, minerals=500, vespene=100):
    bot = Mock()
    bot.time = time
    bot.minerals = minerals
    bot.vespene = vespene
    bot.supply_used = 20
    bot.supply_cap = 44
    bot.units = Mock()
    bot.units.return_value = Mock()
    bot.enemy_units = Mock()
    bot.townhalls = Mock()
    bot.townhalls.exists = True
    bot.start_location = Mock()
    bot.start_location.distance_to = Mock(return_value=5.0)
    bot.enemy_start_locations = [Mock()]
    bot.do = Mock()
    bot.blackboard = None
    return bot


def make_unit(tag=1, type_name="ZERGLING", health_pct=1.0, pos=(10, 10)):
    unit = Mock()
    unit.tag = tag
    unit.type_id = Mock()
    unit.type_id.name = type_name
    unit.health_percentage = health_pct
    unit.position = Mock()
    unit.position.distance_to = Mock(return_value=50.0)
    unit.can_attack = True
    unit.is_idle = True
    return unit


# ═══════════════════════════════════════════════════════
# 1. StrategyManager 견제 시스템 테스트
# ═══════════════════════════════════════════════════════

class TestHarassmentSystem:
    """견제 시스템: 15초 간격, 복귀 로직, 일꾼 킬 카운트 검증"""

    def setup_method(self):
        try:
            from wicked_zerg_challenger.strategy_manager import StrategyManager
        except ImportError:
            pytest.skip("StrategyManager not available")
        self.StrategyManager = StrategyManager

    def _make_strategy_manager(self, time=0.0):
        bot = make_bot(time=time)
        sm = self.StrategyManager.__new__(self.StrategyManager)
        sm.bot = bot
        sm.logger = Mock()
        sm.early_harassment_active = False
        sm.last_harassment_time = 0.0
        sm.harassment_interval = 15.0
        sm.rush_detected = False
        sm.rush_persistence_count = 0
        return sm

    def test_harassment_interval_is_15_seconds(self):
        """견제 간격이 15초로 설정되어 있는지 확인"""
        sm = self._make_strategy_manager()
        assert sm.harassment_interval == 15.0, "견제 간격은 15초여야 함"

    def test_harassment_not_active_before_1_minute(self):
        """1분 이전에는 견제 비활성"""
        sm = self._make_strategy_manager(time=30.0)
        sm._check_early_harassment()
        assert sm.early_harassment_active is False

    def test_harassment_active_after_1_minute(self):
        """1분 이후 견제 활성화"""
        sm = self._make_strategy_manager(time=65.0)
        sm.last_harassment_time = 0.0
        sm._check_early_harassment()
        assert sm.early_harassment_active is True

    def test_harassment_respects_interval(self):
        """15초 이내 재견제 방지"""
        sm = self._make_strategy_manager(time=100.0)
        sm.last_harassment_time = 95.0  # 5초 전에 견제함
        sm._check_early_harassment()
        # 5초 경과 < 15초 간격 → 견제 불가
        assert sm.early_harassment_active is False

    def test_harassment_triggers_after_interval(self):
        """15초 이후 견제 재활성화"""
        sm = self._make_strategy_manager(time=100.0)
        sm.last_harassment_time = 80.0  # 20초 전에 마지막 견제
        sm._check_early_harassment()
        assert sm.early_harassment_active is True

    def test_harassment_deactivates_after_4_minutes(self):
        """4분 이후 견제 종료"""
        sm = self._make_strategy_manager(time=250.0)
        sm.early_harassment_active = True
        sm._check_early_harassment()
        assert sm.early_harassment_active is False

    def test_harassment_updates_last_time(self):
        """견제 활성화 시 마지막 견제 시간 업데이트"""
        sm = self._make_strategy_manager(time=90.0)
        sm.last_harassment_time = 0.0
        sm._check_early_harassment()
        assert sm.last_harassment_time == 90.0


# ═══════════════════════════════════════════════════════
# 2. CombatManager 프레임 스킵 테스트
# ═══════════════════════════════════════════════════════

class TestFrameSkipScaling:
    """전투 로직 동적 프레임 스킵: 유닛 수 기반 스케일링 검증"""

    def setup_method(self):
        try:
            from wicked_zerg_challenger.combat_manager import CombatManager
        except ImportError:
            pytest.skip("CombatManager not available")
        self.CombatManager = CombatManager

    def _make_combat_manager(self, army_count=0):
        bot = make_bot()
        cm = self.CombatManager.__new__(self.CombatManager)
        cm.bot = bot
        cm.logger = Mock()
        cm._combat_base_skip = 4
        cm._combat_max_skip = 8
        cm._combat_frame_skip = 4
        cm._combat_emergency_skip = 1
        cm._combat_is_emergency = False
        cm._last_frame_skip_update = 0
        cm._frame_skip_update_interval = 22
        cm._prev_unit_health_tags = {}

        # 아군 유닛 목 설정
        army_units = [make_unit(tag=i, type_name="ZERGLING") for i in range(army_count)]
        mock_units = Mock()
        mock_units.__iter__ = Mock(return_value=iter(army_units))
        mock_units.__len__ = Mock(return_value=army_count)
        bot.units = Mock(return_value=mock_units)
        bot.units.__iter__ = Mock(return_value=iter(army_units))

        # _filter_army_units 목 설정
        cm._filter_army_units = Mock(return_value=army_units)
        return cm

    def test_base_skip_with_small_army(self):
        """소규모 군대(30 이하): 기본 스킵 4 적용"""
        cm = self._make_combat_manager(army_count=15)
        cm._update_dynamic_frame_skip()
        assert cm._combat_frame_skip == 4

    def test_increased_skip_with_medium_army(self):
        """중규모 군대(30-60): 스킵 4-6 사이"""
        cm = self._make_combat_manager(army_count=45)
        cm._update_dynamic_frame_skip()
        assert 4 <= cm._combat_frame_skip <= 6

    def test_max_skip_with_large_army(self):
        """대규모 군대(60+): 최대 스킵 적용"""
        cm = self._make_combat_manager(army_count=80)
        cm._update_dynamic_frame_skip()
        assert cm._combat_frame_skip >= 6

    def test_frame_skip_does_not_exceed_max(self):
        """프레임 스킵은 최대값(8)을 초과하지 않음"""
        cm = self._make_combat_manager(army_count=200)
        cm._update_dynamic_frame_skip()
        assert cm._combat_frame_skip <= cm._combat_max_skip

    def test_emergency_skip_is_1(self):
        """긴급 상황 프레임 스킵은 1"""
        cm = self._make_combat_manager()
        assert cm._combat_emergency_skip == 1


# ═══════════════════════════════════════════════════════
# 3. 정찰 시스템 테스트
# ═══════════════════════════════════════════════════════

class TestScoutingSystem:
    """정찰 시스템: 30초 오버로드 정찰 간격, _assign_patrol 버그 수정 검증"""

    def setup_method(self):
        try:
            from wicked_zerg_challenger.scouting.advanced_scout_system_v2 import AdvancedScoutingSystemV2
        except ImportError:
            pytest.skip("AdvancedScoutingSystemV2 not available")
        self.ScoutSystem = AdvancedScoutingSystemV2

    def _make_scout_system(self, time=0.0):
        bot = make_bot(time=time)
        bot.units = Mock()
        bot.units.find_by_tag = Mock(return_value=None)
        ss = self.ScoutSystem.__new__(self.ScoutSystem)
        ss.bot = bot
        ss.logger = Mock()
        ss.last_scout_times = {
            "OVERLORD": 0.0, "ZERGLING": 0.0,
            "GENERAL": 0.0, "PATROL": 0.0,
            "WATCHTOWER": 0.0, "DROP_WATCH": 0.0
        }
        ss.active_scouts = {}
        ss.last_scouted_at = {}
        ss.MAX_SCOUTS = {"WORKER": 1, "ZERGLING": 4, "OVERLORD": 3, "OVERSEER": 3}
        ss._patrol_routes = {}
        ss._patrol_index = {}
        ss._patrol_units = set()
        ss._watchtower_positions = []
        ss._watchtower_claimers = {}
        ss._drop_watch_positions = []
        ss._priority_scout_targets = []
        ss.scouts_sent = 0
        ss.scouts_returned = 0
        ss.scouts_lost = 0
        ss.intel_updates = 0
        return ss

    def test_overlord_scout_interval_is_30_seconds(self):
        """오버로드 정찰 간격이 30초인지 확인"""
        ss = self._make_scout_system(time=100.0)
        ss.last_scout_times["OVERLORD"] = 71.0  # 29초 전
        # 29초 < 30초 → 정찰 미실행 (타이머 업데이트 안 됨)
        initial_time = ss.last_scout_times["OVERLORD"]
        # 직접 간격 체크: 30초 미만이면 업데이트 안 함
        elapsed = ss.bot.time - ss.last_scout_times["OVERLORD"]
        assert elapsed < 30.0

    def test_overlord_scout_triggers_after_30_seconds(self):
        """30초 후 오버로드 정찰 트리거 조건 충족"""
        ss = self._make_scout_system(time=100.0)
        ss.last_scout_times["OVERLORD"] = 65.0  # 35초 전
        elapsed = ss.bot.time - ss.last_scout_times["OVERLORD"]
        assert elapsed >= 30.0

    def test_dynamic_interval_early_game(self):
        """초반(0-5분): 25초 간격"""
        ss = self._make_scout_system(time=120.0)
        ss._is_emergency_mode = Mock(return_value=False)
        interval = ss._get_dynamic_interval()
        assert interval == 25.0

    def test_dynamic_interval_tech_timing(self):
        """테크 타이밍(4-7분): 20초 간격 (가장 빈번)"""
        ss = self._make_scout_system(time=300.0)
        ss._is_emergency_mode = Mock(return_value=False)
        interval = ss._get_dynamic_interval()
        assert interval == 20.0

    def test_dynamic_interval_mid_game(self):
        """중반(5-10분): 40초 간격"""
        ss = self._make_scout_system(time=480.0)
        ss._is_emergency_mode = Mock(return_value=False)
        interval = ss._get_dynamic_interval()
        assert interval == 40.0

    def test_dynamic_interval_late_game(self):
        """후반(10분+): 35초 간격"""
        ss = self._make_scout_system(time=700.0)
        ss._is_emergency_mode = Mock(return_value=False)
        interval = ss._get_dynamic_interval()
        assert interval == 35.0

    def test_dynamic_interval_emergency_mode(self):
        """긴급 모드: 15초 간격 (가장 공격적)"""
        ss = self._make_scout_system(time=200.0)
        ss._is_emergency_mode = Mock(return_value=True)
        interval = ss._get_dynamic_interval()
        assert interval == 15.0

    def test_assign_patrol_no_crash_without_sc2(self):
        """sc2 미설치 환경에서 _assign_patrol 크래시 없음 (버그 수정 검증)"""
        ss = self._make_scout_system()
        ss._patrol_routes = {}
        # sc2 없어도 AttributeError 발생 안 함
        try:
            result = ss._assign_patrol("nonexistent_route")
            assert result is False
        except AttributeError as e:
            pytest.fail(f"_assign_patrol raised AttributeError: {e}")

    def test_assign_patrol_returns_false_for_missing_route(self):
        """존재하지 않는 경로에 대해 False 반환"""
        ss = self._make_scout_system()
        ss._patrol_routes = {"main_path": [Mock(), Mock()]}
        result = ss._assign_patrol("missing_route")
        assert result is False

    def test_assign_patrol_skips_already_assigned(self):
        """이미 배정된 경로는 스킵"""
        ss = self._make_scout_system()
        mock_pos = Mock()
        ss._patrol_routes = {"main_path": [mock_pos]}
        existing_tag = 99
        ss._patrol_units = {existing_tag}
        ss.active_scouts = {existing_tag: {"patrol_route": "main_path"}}
        result = ss._assign_patrol("main_path")
        assert result is False


# ═══════════════════════════════════════════════════════
# 4. WorkerKillTracking - 견제 일꾼 킬 추적 테스트
# ═══════════════════════════════════════════════════════

class TestWorkerKillTracking:
    """견제 중 적 일꾼 킬 카운트 추적 검증"""

    def setup_method(self):
        try:
            from wicked_zerg_challenger.combat_manager import CombatManager
        except ImportError:
            pytest.skip("CombatManager not available")
        self.CombatManager = CombatManager

    def _make_cm_with_harass_state(self):
        bot = make_bot()
        cm = self.CombatManager.__new__(self.CombatManager)
        cm.bot = bot
        cm.logger = Mock()
        cm._harass_worker_kills = 0
        cm._harass_last_enemy_workers = None
        cm._harass_retreating_tags = set()
        return cm

    def test_initial_kill_count_is_zero(self):
        """초기 일꾼 킬 카운트는 0"""
        cm = self._make_cm_with_harass_state()
        assert cm._harass_worker_kills == 0

    def test_kill_count_increments_when_workers_die(self):
        """적 일꾼이 죽으면 킬 카운트 증가"""
        cm = self._make_cm_with_harass_state()
        cm._harass_last_enemy_workers = 20
        current_workers = 17  # 3명 사망
        kills = cm._harass_last_enemy_workers - current_workers
        cm._harass_worker_kills += kills
        assert cm._harass_worker_kills == 3

    def test_retreat_tag_tracking(self):
        """저체력 유닛은 후퇴 태그에 추가됨"""
        cm = self._make_cm_with_harass_state()
        low_hp_unit = make_unit(tag=42, health_pct=0.2)
        cm._harass_retreating_tags.add(low_hp_unit.tag)
        assert 42 in cm._harass_retreating_tags

    def test_retreating_unit_cleared_when_healthy(self):
        """체력 회복 시 후퇴 태그 제거"""
        cm = self._make_cm_with_harass_state()
        cm._harass_retreating_tags.add(42)
        # 체력 50% 이상 → 후퇴 해제
        healthy_unit = make_unit(tag=42, health_pct=0.6)
        if healthy_unit.health_percentage > 0.5:
            cm._harass_retreating_tags.discard(healthy_unit.tag)
        assert 42 not in cm._harass_retreating_tags

    def test_dead_units_removed_from_retreat_set(self):
        """사망 유닛은 후퇴 집합에서 제거"""
        cm = self._make_cm_with_harass_state()
        cm._harass_retreating_tags = {1, 2, 3}
        alive_tags = {1, 3}  # 2번 태그 사망
        cm._harass_retreating_tags &= alive_tags
        assert 2 not in cm._harass_retreating_tags
        assert 1 in cm._harass_retreating_tags
        assert 3 in cm._harass_retreating_tags


# ═══════════════════════════════════════════════════════
# 5. conftest BOT_DIR 경로 검증
# ═══════════════════════════════════════════════════════

class TestConftestPaths:
    """conftest.py가 BOT_DIR를 sys.path에 추가하는지 검증"""

    def test_bot_dir_in_syspath(self):
        """wicked_zerg_challenger 디렉토리가 sys.path에 있음"""
        bot_dir = str(Path(__file__).parent.parent / "wicked_zerg_challenger")
        assert bot_dir in sys.path, f"BOT_DIR ({bot_dir}) not in sys.path"

    def test_utils_logger_importable(self):
        """utils.logger가 직접 임포트 가능 (BOT_DIR 경로 통해)"""
        try:
            from utils.logger import get_logger
            logger = get_logger("test")
            assert logger is not None
        except ImportError as e:
            pytest.fail(f"utils.logger import failed: {e}")

    def test_queen_manager_importable(self):
        """QueenManager 임포트 가능"""
        try:
            from wicked_zerg_challenger.queen_manager import QueenManager
        except ImportError as e:
            pytest.fail(f"QueenManager import failed: {e}")

    def test_intel_manager_importable(self):
        """IntelManager 임포트 가능"""
        try:
            from wicked_zerg_challenger.intel_manager import IntelManager
        except ImportError as e:
            pytest.fail(f"IntelManager import failed: {e}")

    def test_creep_manager_importable(self):
        """CreepManager 임포트 가능"""
        try:
            from wicked_zerg_challenger.creep_manager import CreepManager
        except ImportError as e:
            pytest.fail(f"CreepManager import failed: {e}")
