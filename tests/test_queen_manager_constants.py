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


# ─────────────────────────────────────────────────────────────────────────────
# Behavioral edge-case tests (no sc2 dependency required)
# ─────────────────────────────────────────────────────────────────────────────


class _Pos:
    """Tiny stand-in for sc2.position.Point2 with `.distance_to`."""

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

    def distance_to(self, other):
        ox = getattr(other, "x", other[0] if isinstance(other, tuple) else None)
        oy = getattr(other, "y", other[1] if isinstance(other, tuple) else None)
        if ox is None or oy is None:
            return float("inf")
        return ((self.x - ox) ** 2 + (self.y - oy) ** 2) ** 0.5


class _FakeUnit:
    def __init__(self, position, type_id=None):
        self.position = position
        self.type_id = type_id

    def distance_to(self, other):
        target = getattr(other, "position", other)
        return self.position.distance_to(target)


class _FakeBot:
    """Minimal bot stub exposing only the attributes _is_base_under_attack uses."""

    def __init__(self, *, time=60.0, townhalls=None, enemy_units=None):
        self.time = time
        self.townhalls = townhalls if townhalls is not None else []
        self.enemy_units = enemy_units if enemy_units is not None else []


def _make_manager_for(bot):
    return QueenManager(bot)


def test_is_base_under_attack_no_townhalls_returns_false():
    bot = _FakeBot(townhalls=[], enemy_units=[_FakeUnit(_Pos(0, 0))])
    mgr = _make_manager_for(bot)
    assert mgr._is_base_under_attack() is False


def test_is_base_under_attack_no_enemies_returns_false():
    base = _FakeUnit(_Pos(50, 50))
    bot = _FakeBot(townhalls=[base], enemy_units=[])
    mgr = _make_manager_for(bot)
    assert mgr._is_base_under_attack() is False


def test_is_base_under_attack_far_enemy_returns_false():
    base = _FakeUnit(_Pos(0, 0))
    far_enemy = _FakeUnit(_Pos(100, 100))
    bot = _FakeBot(time=60.0, townhalls=[base], enemy_units=[far_enemy])
    mgr = _make_manager_for(bot)
    assert mgr._is_base_under_attack() is False


def test_is_base_under_attack_close_enemy_returns_true():
    base = _FakeUnit(_Pos(0, 0))
    close_enemy = _FakeUnit(_Pos(5, 5))  # ~7 tiles, < 20
    bot = _FakeBot(time=60.0, townhalls=[base], enemy_units=[close_enemy])
    mgr = _make_manager_for(bot)
    assert mgr._is_base_under_attack() is True


def test_is_base_under_attack_late_game_uses_tighter_range():
    """Phase 36: after 180s the detection radius shrinks 20->18."""
    base = _FakeUnit(_Pos(0, 0))
    edge_enemy = _FakeUnit(_Pos(0, 19))  # 19 tiles: inside 20 but outside 18
    bot_early = _FakeBot(time=60.0, townhalls=[base], enemy_units=[edge_enemy])
    bot_late = _FakeBot(time=400.0, townhalls=[base], enemy_units=[edge_enemy])
    assert _make_manager_for(bot_early)._is_base_under_attack() is True
    assert _make_manager_for(bot_late)._is_base_under_attack() is False


def test_is_base_under_attack_missing_attrs_returns_false():
    """Missing townhalls / enemy_units must not crash, only return False."""

    class Bare:
        time = 0.0

    mgr = _make_manager_for(Bare())
    assert mgr._is_base_under_attack() is False


def test_count_creep_tumors_handles_missing_structures():
    bot = _FakeBot()
    mgr = _make_manager_for(bot)
    # _FakeBot has no `structures` attribute
    assert mgr._count_creep_tumors() == 0


def test_count_creep_tumors_handles_iteration_failure():
    """If iterating self.bot.structures raises, we suppress and return 0."""

    class Boom:
        def __iter__(self):
            raise RuntimeError("structures not ready")

    class StructBot(_FakeBot):
        structures = Boom()

    mgr = _make_manager_for(StructBot())
    assert mgr._count_creep_tumors() == 0


def test_is_valid_creep_position_none_target():
    bot = _FakeBot()
    mgr = _make_manager_for(bot)
    assert mgr._is_valid_creep_position(None) is False


def test_is_valid_creep_position_no_has_creep_method():
    """Without `bot.has_creep`, the helper returns False (safer default)."""
    bot = _FakeBot()
    mgr = _make_manager_for(bot)
    assert mgr._is_valid_creep_position(_Pos(1, 1)) is False


def test_is_valid_creep_position_returns_bool_from_has_creep():
    class CreepBot(_FakeBot):
        def has_creep(self, _target):
            return True

    mgr = _make_manager_for(CreepBot())
    assert mgr._is_valid_creep_position(_Pos(1, 1)) is True


def test_is_valid_creep_position_swallows_errors():
    class BoomBot(_FakeBot):
        def has_creep(self, _target):
            raise RuntimeError("game state not ready")

    mgr = _make_manager_for(BoomBot())
    # Must NOT propagate; safe default is False
    assert mgr._is_valid_creep_position(_Pos(1, 1)) is False
