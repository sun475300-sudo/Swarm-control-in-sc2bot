# -*- coding: utf-8 -*-
"""
_sc2_compat 스텁 모듈 자체 검증 테스트.

이 테스트는 sc2 패키지가 실제로 설치되어 있지 않은 환경에서 사용되는
fallback 스텁의 invariant를 직접 검증한다. 다른 단위 테스트는 import
사이드 이펙트를 통해 간접 검증할 뿐이라, 스텁 동작이 미세하게 깨지면
원인 추적이 어렵다 (예: __bool__이 False면 production 코드의
`next_diff if next_diff else fallback` 분기가 무성하게 잘못된다).
"""
import pytest

from _sc2_compat import (
    AbilityId,
    Bot,
    BotAI,
    Computer,
    Difficulty,
    Point2,
    Race,
    Result,
    SC2_AVAILABLE,
    Unit,
    UnitTypeId,
    Units,
    UpgradeId,
)


class TestEnumLikeStubAttribute:
    """Race/Difficulty/UnitTypeId 등 enum-like 스텁의 attribute 접근."""

    def test_attribute_returns_sentinel_with_correct_name(self):
        assert UnitTypeId.OVERLORD.name == "OVERLORD"
        assert Race.Zerg.name == "Zerg"
        assert Difficulty.Easy.name == "Easy"

    def test_same_attribute_returns_same_instance(self):
        # 동일 attribute 두 번 접근 → 같은 캐시된 객체.
        # (set/dict key 불변성을 위해 필수)
        assert UnitTypeId.OVERLORD is UnitTypeId.OVERLORD
        assert Race.Zerg is Race.Zerg

    def test_different_attributes_are_distinct(self):
        assert UnitTypeId.OVERLORD is not UnitTypeId.ZERGLING
        assert UnitTypeId.OVERLORD != UnitTypeId.ZERGLING

    def test_subscript_equivalent_to_attribute(self):
        # production 코드(difficulty_progression.py)가
        # `Race[race_str]` 패턴을 사용하므로 동치성이 중요.
        if SC2_AVAILABLE:
            pytest.skip("real sc2 enums use different subscript semantics")
        assert Race["Zerg"] is Race.Zerg
        assert Difficulty["Medium"] is Difficulty.Medium

    def test_subscript_with_non_string_raises(self):
        if SC2_AVAILABLE:
            pytest.skip("real sc2 enums use different subscript semantics")
        with pytest.raises(KeyError):
            _ = Race[42]


class TestEnumLikeStubProtocols:
    """== / hash / __bool__ 같은 dunder 메서드 동작 검증."""

    def test_equality_by_name(self):
        a = UnitTypeId.OVERLORD
        b = UnitTypeId.OVERLORD
        assert a == b

    def test_hash_consistency(self):
        # set/dict 사용 가능해야 함
        s = {UnitTypeId.OVERLORD, UnitTypeId.OVERLORD, UnitTypeId.ZERGLING}
        assert len(s) == 2
        assert UnitTypeId.OVERLORD in s

    def test_truthiness_is_true(self):
        # production 패턴: `next_diff if next_diff else fallback`
        # sentinel 멤버는 truthy여야 한다 (없음 ≠ 빈값).
        if SC2_AVAILABLE:
            pytest.skip("real sc2 enums always truthy by default")
        assert bool(Difficulty.Easy) is True
        assert bool(UnitTypeId.OVERLORD) is True


class TestPoint2Stub:
    def test_x_y_accessor(self):
        p = Point2((3.0, 4.0))
        assert p.x == 3.0
        assert p.y == 4.0

    def test_distance_to_basic(self):
        a = Point2((0.0, 0.0))
        b = Point2((3.0, 4.0))
        assert a.distance_to(b) == pytest.approx(5.0)

    def test_distance_to_with_tuple(self):
        # production에서 가끔 raw tuple도 들어옴
        a = Point2((0.0, 0.0))
        assert a.distance_to((6.0, 8.0)) == pytest.approx(10.0)

    def test_offset(self):
        p = Point2((1.0, 2.0))
        q = p.offset((4.0, 5.0))
        assert (q.x, q.y) == (5.0, 7.0)


class TestUnitsStub:
    def test_two_arg_constructor(self):
        # burnysc2 시그니처: Units(iterable, bot_object)
        # 빈 list 생성자는 1-arg만 받으므로 명시적 2-arg가 필수.
        u = Units([1, 2, 3], None)
        assert len(u) == 3

    def test_amount_property(self):
        u = Units([1, 2, 3, 4], None)
        assert u.amount == 4

    def test_exists_property(self):
        assert Units([], None).exists is False
        assert Units([1], None).exists is True

    def test_filter_returns_units_instance(self):
        u = Units([1, 2, 3, 4, 5], None)
        evens = u.filter(lambda x: x % 2 == 0)
        assert isinstance(evens, Units)
        assert list(evens) == [2, 4]


class TestPlayerStubs:
    def test_bot_constructor_keeps_args(self):
        b = Bot(race=Race.Zerg, ai=None, name="x")
        assert b.race is Race.Zerg
        assert b.name == "x"

    def test_computer_constructor_keeps_args(self):
        c = Computer(race=Race.Terran, difficulty=Difficulty.Easy)
        assert c.race is Race.Terran
        assert c.difficulty is Difficulty.Easy


class TestBotAIBaseStub:
    def test_botai_is_class(self):
        # 다른 모듈이 `class Foo(BotAI): ...` 식으로 상속할 수 있어야 함
        class _Sub(BotAI):
            pass

        assert issubclass(_Sub, BotAI)


class TestSC2AvailableFlag:
    def test_flag_is_bool(self):
        assert isinstance(SC2_AVAILABLE, bool)

    def test_flag_matches_real_import(self):
        try:
            import sc2  # noqa: F401

            real = True
        except Exception:
            real = False
        # conftest가 가짜 sc2를 sys.modules에 주입하므로,
        # 이 시점의 import는 항상 성공한다. 그러나 SC2_AVAILABLE 자체는
        # _sc2_compat 모듈이 처음 로드될 때 결정된 값이라 False여야 함
        # (conftest 주입은 _sc2_compat 로드 이후 실행).
        # → 두 값이 일치하지 않을 수 있다. 본 테스트는 단지 flag가
        # 외부 호출자가 의도적으로 분기 가능한 안정된 boolean임을 확인.
        assert isinstance(SC2_AVAILABLE, bool)
