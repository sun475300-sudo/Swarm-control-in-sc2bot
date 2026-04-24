# -*- coding: utf-8 -*-
"""
핵심 유틸/블랙보드 단위 테스트

sc2 라이브러리 없이 검증 가능한 모듈을 대상으로 한다:
- blackboard.GameStateBlackboard (상태·권한·생산 큐·캐시)
- utils.game_constants (상수·변환 함수)
- utils.common_helpers (has_units/safe_first/safe_amount/clamp/percentage)
- utils.frame_cache (FrameCache, cached_per_frame)

Note: 레포 루트에 별도의 `utils/` 패키지가 있어 이름 충돌을 일으키므로
      importlib로 파일 경로에서 직접 로드한다.
"""

import importlib.util
import os
import sys
from pathlib import Path

import pytest

BOT_ROOT = Path(__file__).resolve().parent.parent / "wicked_zerg_challenger"


def _load_module(name: str, relpath: str):
    """Load a module from an explicit file path, bypassing sys.path namespace conflicts."""
    path = BOT_ROOT / relpath
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    # Ensure wicked_zerg_challenger dir is in sys.path so local sibling imports resolve
    bot_root_str = str(BOT_ROOT)
    if bot_root_str not in sys.path:
        sys.path.insert(0, bot_root_str)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def bb_mod():
    return _load_module("wzc_blackboard", "blackboard.py")


@pytest.fixture
def bb(bb_mod):
    return bb_mod.GameStateBlackboard()


@pytest.fixture(scope="module")
def gc_mod():
    return _load_module("wzc_game_constants", "utils/game_constants.py")


@pytest.fixture(scope="module")
def helpers_mod():
    return _load_module("wzc_common_helpers", "utils/common_helpers.py")


@pytest.fixture(scope="module")
def frame_cache_mod():
    return _load_module("wzc_frame_cache", "utils/frame_cache.py")


# ═══════════════════════════════════════════════════════
# Blackboard
# ═══════════════════════════════════════════════════════


class TestBlackboardBasic:
    def test_default_phase_is_opening(self, bb, bb_mod):
        assert bb.game_phase == bb_mod.GamePhase.OPENING

    def test_update_game_info_phase_transitions(self, bb, bb_mod):
        bb.update_game_info(game_time=0, iteration=0)
        assert bb.game_phase == bb_mod.GamePhase.OPENING
        bb.update_game_info(game_time=200, iteration=1)
        assert bb.game_phase == bb_mod.GamePhase.EARLY_GAME
        bb.update_game_info(game_time=500, iteration=2)
        assert bb.game_phase == bb_mod.GamePhase.MID_GAME
        bb.update_game_info(game_time=800, iteration=3)
        assert bb.game_phase == bb_mod.GamePhase.LATE_GAME

    def test_supply_blocked_flag(self, bb):
        bb.update_resources(minerals=100, vespene=0, supply_used=100, supply_cap=100)
        assert bb.resources.is_supply_blocked is True

        bb.update_resources(minerals=100, vespene=0, supply_used=40, supply_cap=100)
        assert bb.resources.is_supply_blocked is False

    def test_supply_blocked_ignored_at_max_supply(self, bb):
        bb.update_resources(minerals=0, vespene=0, supply_used=200, supply_cap=200)
        assert bb.resources.is_supply_blocked is False


class TestBlackboardUnitCounts:
    def test_update_and_get(self, bb, bb_mod):
        bb.update_unit_count("ZERGLING", current=5, pending=2)
        counts = bb.get_unit_count("ZERGLING")
        assert isinstance(counts, bb_mod.UnitCounts)
        assert counts.current == 5
        assert counts.pending == 2
        assert counts.total == 7

    def test_missing_type_returns_zero(self, bb):
        counts = bb.get_unit_count("NON_EXISTENT")
        assert counts.current == 0
        assert counts.pending == 0
        assert counts.total == 0


class TestBlackboardThreat:
    def test_detected_at_set_on_first_threat(self, bb, bb_mod):
        bb.update_game_info(game_time=120, iteration=1)
        bb.update_threat(bb_mod.ThreatLevel.MEDIUM)
        assert bb.threat.level == bb_mod.ThreatLevel.MEDIUM
        assert bb.threat.detected_at == 120

    def test_detected_at_preserved_on_subsequent_updates(self, bb, bb_mod):
        bb.update_game_info(game_time=100, iteration=0)
        bb.update_threat(bb_mod.ThreatLevel.HIGH)
        first = bb.threat.detected_at
        bb.update_game_info(game_time=300, iteration=1)
        bb.update_threat(bb_mod.ThreatLevel.CRITICAL)
        # detected_at preserved once set (not reset on subsequent level changes)
        assert bb.threat.detected_at == first


class TestBlackboardAuthority:
    def test_emergency_mode_prioritizes_defense(self, bb, bb_mod):
        bb.set_authority_mode(bb_mod.AuthorityMode.EMERGENCY)
        assert bb.get_authority_priority("DefenseCoordinator") == 0
        assert bb.get_authority_priority("AggressiveStrategies") == 3

    def test_balanced_mode_defaults(self, bb, bb_mod):
        bb.set_authority_mode(bb_mod.AuthorityMode.BALANCED)
        assert bb.get_authority_priority("DefenseCoordinator") == 0
        assert bb.get_authority_priority("UnitFactory") == 1
        assert bb.get_authority_priority("EconomyManager") == 2
        # Unknown requester returns default 2
        assert bb.get_authority_priority("Unknown") == 2

    def test_auto_adjust_rush_triggers_emergency(self, bb, bb_mod):
        bb.update_threat(bb_mod.ThreatLevel.HIGH, is_rushing=True)
        bb.auto_adjust_authority()
        assert bb.authority_mode == bb_mod.AuthorityMode.EMERGENCY

    def test_auto_adjust_safe_opening_triggers_economy(self, bb, bb_mod):
        bb.update_game_info(game_time=10, iteration=0)
        bb.update_threat(bb_mod.ThreatLevel.NONE)
        bb.auto_adjust_authority()
        assert bb.authority_mode == bb_mod.AuthorityMode.ECONOMY


class TestBlackboardProductionQueue:
    def test_request_and_consume(self, bb):
        bb.request_production("ZERGLING", 6, "EconomyManager", priority=3)
        bb.request_production("ROACH", 4, "UnitFactory", priority=1)
        first = bb.get_next_production()
        assert first == ("ROACH", 4, "UnitFactory")
        second = bb.get_next_production()
        assert second == ("ZERGLING", 6, "EconomyManager")
        assert bb.get_next_production() is None

    def test_duplicate_requester_updates_inplace(self, bb):
        bb.request_production("DRONE", 1, "EconomyManager", priority=2)
        bb.request_production("DRONE", 5, "EconomyManager", priority=2)
        assert bb.production_queue[2] == [("DRONE", 5, "EconomyManager")]

    def test_clear_by_requester_preserves_others(self, bb):
        bb.request_production("DRONE", 5, "EconomyManager", priority=2)
        bb.request_production("ROACH", 4, "UnitFactory", priority=2)
        bb.clear_production_requests("EconomyManager")
        assert bb.production_queue[2] == [("ROACH", 4, "UnitFactory")]


class TestBlackboardBuildingReservation:
    def test_reserve_then_check(self, bb):
        bb.update_game_info(game_time=10, iteration=0)
        assert bb.reserve_building("HATCHERY", "EconomyManager") is True
        assert bb.is_building_reserved("HATCHERY") is True

    def test_duplicate_reserve_fails_within_duration(self, bb):
        bb.update_game_info(game_time=10, iteration=0)
        assert bb.reserve_building("HATCHERY", "A", duration=5.0) is True
        assert bb.reserve_building("HATCHERY", "B", duration=5.0) is False

    def test_reserve_succeeds_after_expiry(self, bb):
        bb.update_game_info(game_time=10, iteration=0)
        bb.reserve_building("HATCHERY", "A", duration=5.0)
        bb.update_game_info(game_time=20, iteration=1)
        assert bb.reserve_building("HATCHERY", "B", duration=5.0) is True


class TestBlackboardCache:
    def test_cache_set_get(self, bb):
        bb.update_game_info(game_time=0, iteration=0)
        bb.cache_set("k", 123)
        assert bb.cache_get("k") == 123

    def test_cache_ttl_expiry(self, bb):
        bb.update_game_info(game_time=0, iteration=0)
        bb.cache_set("k", 42, ttl=1.0)
        bb.update_game_info(game_time=0.5, iteration=1)
        assert bb.cache_get("k") == 42
        bb.update_game_info(game_time=2.0, iteration=2)
        assert bb.cache_get("k", default="missing") == "missing"

    def test_cache_per_key_ttl(self, bb):
        """Bug fix #6: Per-key TTLs must not clobber each other."""
        bb.update_game_info(game_time=0, iteration=0)
        bb.cache_set("short", "s", ttl=1.0)
        bb.cache_set("long", "l", ttl=10.0)
        bb.update_game_info(game_time=2.0, iteration=1)
        assert bb.cache_get("short", default=None) is None
        assert bb.cache_get("long") == "l"

    def test_cache_clear(self, bb):
        bb.update_game_info(game_time=0, iteration=0)
        bb.cache_set("a", 1)
        bb.cache_set("b", 2)
        bb.cache_clear()
        assert bb.cache_get("a") is None
        assert bb.cache_get("b") is None


class TestBlackboardDecisionHelpers:
    def test_should_defend(self, bb, bb_mod):
        bb.update_threat(bb_mod.ThreatLevel.HIGH)
        assert bb.should_defend() is True

    def test_can_attack_requires_beyond_opening(self, bb, bb_mod):
        bb.update_game_info(game_time=500, iteration=0)
        assert bb.game_phase != bb_mod.GamePhase.OPENING
        bb.update_threat(bb_mod.ThreatLevel.LOW)
        assert bb.can_attack() is True

    def test_should_expand_requires_resources(self, bb, bb_mod):
        bb.update_threat(bb_mod.ThreatLevel.NONE)
        bb.update_resources(minerals=100, vespene=0, supply_used=10, supply_cap=20)
        assert bb.should_expand() is False
        bb.update_resources(minerals=500, vespene=0, supply_used=10, supply_cap=20)
        assert bb.should_expand() is True


# ═══════════════════════════════════════════════════════
# Game Constants
# ═══════════════════════════════════════════════════════


class TestGameConstants:
    def test_frequencies_consistent_with_fps(self, gc_mod):
        GameFrequencies = gc_mod.GameFrequencies
        assert abs(GameFrequencies.EVERY_SECOND - int(GameFrequencies.GAME_FPS)) <= 1

    def test_frequencies_monotonic(self, gc_mod):
        f = gc_mod.GameFrequencies
        assert (
            f.EVERY_HALF_SECOND
            < f.EVERY_SECOND
            < f.EVERY_2_SECONDS
            < f.EVERY_5_SECONDS
            < f.EVERY_10_SECONDS
            < f.EVERY_30_SECONDS
            < f.EVERY_60_SECONDS
        )

    def test_economy_constants_reasonable(self, gc_mod):
        e = gc_mod.EconomyConstants
        assert e.OPTIMAL_WORKERS_PER_BASE > 0
        assert e.MAX_WORKERS_PER_BASE > e.OPTIMAL_WORKERS_PER_BASE
        assert e.OPTIMAL_WORKERS_PER_GAS in (2, 3)

    def test_combat_hp_thresholds_in_range(self, gc_mod):
        c = gc_mod.CombatConstants
        for name in (
            "BURROW_HP_THRESHOLD",
            "RETREAT_HP_THRESHOLD",
            "FULL_HP_THRESHOLD",
            "TRANSFUSION_HP_THRESHOLD",
        ):
            val = getattr(c, name)
            assert 0.0 < val <= 1.0, f"{name}={val}"

    def test_seconds_iteration_roundtrip(self, gc_mod):
        for seconds in (1.0, 5.0, 30.0, 60.0):
            back = gc_mod.iterations_to_seconds(gc_mod.seconds_to_iterations(seconds))
            assert abs(back - seconds) <= 1.0 / 22.4


# ═══════════════════════════════════════════════════════
# Common Helpers
# ═══════════════════════════════════════════════════════


class _MockUnits:
    """Minimal stand-in for sc2 Units collection."""

    def __init__(self, items):
        self._items = list(items)

    @property
    def exists(self):
        return len(self._items) > 0

    @property
    def amount(self):
        return len(self._items)

    @property
    def first(self):
        return self._items[0]

    def closest_to(self, position):
        return min(self._items, key=lambda u: u.distance_to(position))


class _MockUnit:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def distance_to(self, position):
        return ((self.x - position[0]) ** 2 + (self.y - position[1]) ** 2) ** 0.5


class TestCommonHelpers:
    def test_has_units_none(self, helpers_mod):
        assert helpers_mod.has_units(None) is False

    def test_has_units_empty_list(self, helpers_mod):
        assert helpers_mod.has_units([]) is False

    def test_has_units_list_populated(self, helpers_mod):
        assert helpers_mod.has_units([1, 2]) is True

    def test_has_units_sc2_collection(self, helpers_mod):
        assert helpers_mod.has_units(_MockUnits([1])) is True
        assert helpers_mod.has_units(_MockUnits([])) is False

    def test_safe_first_empty(self, helpers_mod):
        assert helpers_mod.safe_first([]) is None
        assert helpers_mod.safe_first(None) is None

    def test_safe_first_sc2(self, helpers_mod):
        assert helpers_mod.safe_first(_MockUnits(["a", "b"])) == "a"

    def test_safe_first_list(self, helpers_mod):
        assert helpers_mod.safe_first([10, 20]) == 10

    def test_safe_amount(self, helpers_mod):
        assert helpers_mod.safe_amount(None) == 0
        assert helpers_mod.safe_amount([]) == 0
        assert helpers_mod.safe_amount([1, 2, 3]) == 3
        assert helpers_mod.safe_amount(_MockUnits(["a", "b"])) == 2

    def test_safe_closest_returns_closest(self, helpers_mod):
        units = _MockUnits([_MockUnit(0, 0), _MockUnit(10, 0), _MockUnit(3, 0)])
        closest = helpers_mod.safe_closest(units, (2, 0))
        assert closest.x == 3

    def test_safe_closest_empty(self, helpers_mod):
        assert helpers_mod.safe_closest([], (0, 0)) is None

    def test_safe_closest_fallback_on_list(self, helpers_mod):
        items = [_MockUnit(0, 0), _MockUnit(10, 0), _MockUnit(3, 0)]
        closest = helpers_mod.safe_closest(items, (2, 0))
        assert closest.x == 3

    def test_clamp(self, helpers_mod):
        assert helpers_mod.clamp(5, 0, 10) == 5
        assert helpers_mod.clamp(-1, 0, 10) == 0
        assert helpers_mod.clamp(20, 0, 10) == 10
        assert helpers_mod.clamp(5.5, 0, 10) == 5.5

    def test_percentage_bounds(self, helpers_mod):
        assert helpers_mod.percentage(0, 10) == 0.0
        assert helpers_mod.percentage(10, 10) == 1.0
        assert helpers_mod.percentage(5, 10) == 0.5

    def test_percentage_zero_total(self, helpers_mod):
        assert helpers_mod.percentage(5, 0) == 0.0
        assert helpers_mod.percentage(5, -1) == 0.0

    def test_percentage_clamps_overflow(self, helpers_mod):
        assert helpers_mod.percentage(20, 10) == 1.0


# ═══════════════════════════════════════════════════════
# FrameCache
# ═══════════════════════════════════════════════════════


class TestFrameCache:
    def test_new_instance_empty(self, frame_cache_mod):
        cache = frame_cache_mod.FrameCache()
        assert cache.get("k") is None
        assert cache.has("k") is False

    def test_set_and_get(self, frame_cache_mod):
        cache = frame_cache_mod.FrameCache()
        cache.set("a", 1)
        assert cache.has("a") is True
        assert cache.get("a") == 1

    def test_clear_on_new_frame(self, frame_cache_mod):
        cache = frame_cache_mod.FrameCache()
        cache.clear_if_new_frame(10)
        cache.set("a", 1)
        cache.clear_if_new_frame(10)
        assert cache.get("a") == 1
        cache.clear_if_new_frame(11)
        assert cache.get("a") is None

    def test_cached_per_frame_decorator_memoizes(self, frame_cache_mod):
        FrameCache = frame_cache_mod.FrameCache
        cached_per_frame = frame_cache_mod.cached_per_frame

        class Manager:
            def __init__(self):
                self._frame_cache = FrameCache()
                self.calls = 0

            @cached_per_frame
            def compute(self):
                self.calls += 1
                return self.calls

        m = Manager()
        m._frame_cache.clear_if_new_frame(0)
        assert m.compute() == 1
        assert m.compute() == 1  # memoized
        m._frame_cache.clear_if_new_frame(1)
        assert m.compute() == 2  # invalidated

    def test_cached_per_frame_without_cache_attr(self, frame_cache_mod):
        """Decorator should pass through if instance has no _frame_cache."""
        cached_per_frame = frame_cache_mod.cached_per_frame

        class NoCache:
            @cached_per_frame
            def compute(self):
                return 42

        n = NoCache()
        assert n.compute() == 42
