"""
Regression tests pinning QueenManager 인스턴스 기본값을 GameConfig 와 일치시키는 단위 테스트.

이 테스트는 magic number 추출 시점의 동작 보존을 보장한다.
값을 의도적으로 변경하려면 GameConfig + 본 테스트를 함께 수정한다.
"""

import pytest

try:
    from wicked_zerg_challenger.game_config import GameConfig
    from wicked_zerg_challenger.queen_manager import QueenManager
except ImportError:
    pytest.skip("queen_manager dependencies missing", allow_module_level=True)


class _DummyBot:
    pass


@pytest.fixture
def manager():
    return QueenManager(_DummyBot())


def test_inject_thresholds_match_gameconfig(manager):
    assert manager.inject_energy_threshold == GameConfig.QUEEN_INJECT_ENERGY_THRESHOLD
    assert manager.inject_cooldown == GameConfig.QUEEN_INJECT_COOLDOWN_SEC
    assert manager.max_inject_distance == GameConfig.QUEEN_MAX_INJECT_DISTANCE
    assert manager.max_queen_travel_distance == GameConfig.QUEEN_MAX_TRAVEL_DISTANCE


def test_creep_thresholds_match_gameconfig(manager):
    assert manager.creep_energy_threshold == GameConfig.QUEEN_CREEP_SPREAD_ENERGY
    assert manager.creep_spread_cooldown == GameConfig.QUEEN_CREEP_SPREAD_COOLDOWN_SEC
    assert (
        manager.inject_queen_creep_threshold
        == GameConfig.QUEEN_INJECT_QUEEN_CREEP_ENERGY
    )


def test_transfuse_thresholds_match_gameconfig(manager):
    assert (
        manager.transfuse_energy_threshold
        == GameConfig.QUEEN_TRANSFUSE_ENERGY_THRESHOLD
    )
    assert manager.transfuse_cooldown == GameConfig.QUEEN_TRANSFUSE_COOLDOWN_SEC
    assert manager.transfuse_health_threshold == GameConfig.QUEEN_TRANSFUSE_HP_THRESHOLD


def test_production_caps_match_gameconfig(manager):
    assert manager.max_queens_per_base == GameConfig.QUEEN_MAX_PER_BASE
    assert manager.creep_queen_bonus == GameConfig.QUEEN_CREEP_BONUS_QUEENS


def test_inject_cooldown_within_sc2_spawn_larva_window():
    # SC2 Spawn Larva 실제 쿨다운 28.57초 — 0.5초 이상 여유, 1초 이내 보장
    assert 28.57 < GameConfig.QUEEN_INJECT_COOLDOWN_SEC <= 29.6


def test_transfuse_health_threshold_in_unit_range():
    assert 0.0 < GameConfig.QUEEN_TRANSFUSE_HP_THRESHOLD < 1.0


def test_queen_energy_thresholds_in_valid_range():
    # 퀸 에너지 풀: 0~200
    for value in (
        GameConfig.QUEEN_INJECT_ENERGY_THRESHOLD,
        GameConfig.QUEEN_CREEP_SPREAD_ENERGY,
        GameConfig.QUEEN_INJECT_QUEEN_CREEP_ENERGY,
        GameConfig.QUEEN_TRANSFUSE_ENERGY_THRESHOLD,
    ):
        assert 0 <= value <= 200, f"queen energy threshold out of range: {value}"
