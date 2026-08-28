"""ROADMAP Sprint 4 Task 4.3: 바퀴-히드라 연합 포메이션 검증.

이전에는 ROACH와 HYDRALISK가 같은 '원거리 유닛' 취급으로 동일한 부채꼴에
배치되어 전열/후열 구분이 전혀 없었다 (실제 감사 결과: 관련 로직 부재).
이제 두 병종이 함께 있으면 바퀴는 목표를 향한 전열에, 히드라는 바퀴 뒤
사거리(6)만큼 떨어진 후열에 배치되어야 한다.
"""

import os
import sys

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from types import SimpleNamespace

from combat.formation_manager import FormationManager
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2

import pytest


class FakeUnit:
    def __init__(self, tag, type_id):
        self.tag = tag
        self.type_id = type_id


def make_bot(base_pos=(2.0, 3.0)):
    # Deliberately not (0.0, 0.0): Point2((0.0, 0.0)) is falsy (sc2's Point2
    # treats the zero vector as False in a boolean context), which previously
    # let a `if our_base and ...` guard accidentally skip over a real bug
    # instead of exercising it. Real SC2 maps never place a base at the
    # world origin either, so this default matches actual game conditions.
    townhall = SimpleNamespace(position=Point2(base_pos))
    townhalls = SimpleNamespace(exists=True, first=townhall)
    return SimpleNamespace(townhalls=townhalls)


@pytest.fixture
def manager():
    return FormationManager(make_bot())


def test_roach_hydra_mix_splits_into_front_and_rear(manager):
    roaches = [FakeUnit(1, UnitTypeId.ROACH), FakeUnit(2, UnitTypeId.ROACH)]
    hydras = [FakeUnit(3, UnitTypeId.HYDRALISK), FakeUnit(4, UnitTypeId.HYDRALISK)]
    enemy_center = Point2((20.0, 0.0))

    assignments = manager.form_concave(roaches + hydras, enemy_center)
    by_tag = {unit.tag: pos for unit, pos in assignments}

    assert set(by_tag) == {1, 2, 3, 4}

    # Roaches must be closer to the enemy than the base-line, hydras must sit
    # further back (away from the enemy) than the roaches by ~6 units.
    for tag in (1, 2):
        assert by_tag[tag].distance_to(enemy_center) < 3.0
    for tag in (3, 4):
        assert by_tag[tag].distance_to(enemy_center) == pytest.approx(6.0, abs=2.0)
        # hydra rear position must be farther from the enemy than any roach position
        assert by_tag[tag].distance_to(enemy_center) > by_tag[1].distance_to(
            enemy_center
        )


def test_pure_hydra_army_keeps_original_concave_behavior(manager):
    hydras = [FakeUnit(1, UnitTypeId.HYDRALISK), FakeUnit(2, UnitTypeId.HYDRALISK)]
    enemy_center = Point2((20.0, 0.0))

    assignments = manager.form_concave(hydras, enemy_center)

    assert len(assignments) == 2
    assert {u.tag for u, _ in assignments} == {1, 2}


def test_pure_roach_army_keeps_original_concave_behavior(manager):
    roaches = [FakeUnit(1, UnitTypeId.ROACH), FakeUnit(2, UnitTypeId.ROACH)]
    enemy_center = Point2((20.0, 0.0))

    assignments = manager.form_concave(roaches, enemy_center)

    assert len(assignments) == 2
    assert {u.tag for u, _ in assignments} == {1, 2}


def test_point2_normalized_is_a_property_not_a_method():
    """Regression guard: sc2.position.Point2.normalized is a @property in the
    installed python-sc2 version, not a method. Calling it as `.normalized()`
    (as formation_manager.py used to, everywhere it computed a direction
    vector) raises `TypeError: 'Point2' object is not callable` any time the
    vector is non-zero — i.e. on every real call. This silently broke the
    entire formation system (form_concave / get_optimal_position) for any
    composition with melee units, ranged units without a roach+hydra mix, or
    get_optimal_position, since no test previously exercised these code
    paths with a non-origin base position.
    """
    vector = Point2((20.0, 0.0)) - Point2((2.0, 3.0))
    assert isinstance(vector.normalized, Point2)
    with pytest.raises(TypeError):
        vector.normalized()


def test_melee_and_ranged_formation_does_not_crash_with_realistic_base(manager):
    """Exercises the (previously broken) non-roach-hydra concave paths."""
    units = [
        FakeUnit(1, UnitTypeId.HYDRALISK),
        FakeUnit(2, UnitTypeId.ZERGLING),
    ]
    enemy_center = Point2((20.0, 0.0))

    assignments = manager.form_concave(units, enemy_center)

    assert {u.tag for u, _ in assignments} == {1, 2}


def test_get_optimal_position_does_not_crash_with_realistic_base(manager):
    unit = FakeUnit(1, UnitTypeId.HYDRALISK)
    enemy_center = Point2((20.0, 0.0))

    pos = manager.get_optimal_position(unit, enemy_center, formation_type="concave")

    assert isinstance(pos, Point2)
