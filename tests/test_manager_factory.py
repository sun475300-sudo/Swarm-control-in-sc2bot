# -*- coding: utf-8 -*-
"""
Unit Tests for ManagerFactory

테스트 범위:
- ManagerConfig 기본값 / __post_init__
- 매니저 등록 (단일 / 일괄, None 처리)
- 우선순위 기반 초기화 순서 (CRITICAL → HIGH → MEDIUM → LOW)
- 의존성 그래프 (의존성 먼저 초기화, 의존성 실패 시 본인도 실패)
- 통계 (success_rate, failed_managers, initialization_order)
- 조회 API (get_manager, is_initialized, get_failed_reason)
- 실패 모드 (ImportError, InitError, disabled, missing class)
"""

import sys
import types
import pytest

try:
    from wicked_zerg_challenger.core.manager_factory import (
        ManagerFactory,
        ManagerConfig,
        ManagerPriority,
    )
except ImportError:
    pytest.skip("manager_factory not available", allow_module_level=True)


# ============================================================================
# 테스트용 더미 매니저 모듈을 동적으로 sys.modules 에 등록
# ============================================================================

class _GoodManager:
    def __init__(self, bot=None, **kwargs):
        self.bot = bot
        self.kwargs = kwargs


class _ManagerNeedsBlackboard:
    def __init__(self, bot=None, blackboard=None):
        self.bot = bot
        self.blackboard = blackboard


class _ManagerExplodes:
    def __init__(self, bot=None):
        raise RuntimeError("kaboom")


@pytest.fixture(autouse=True)
def _register_dummy_modules():
    """테스트마다 더미 매니저 모듈을 등록/정리"""
    mod = types.ModuleType("dummy_managers_for_tests")
    mod.GoodManager = _GoodManager
    mod.ManagerNeedsBlackboard = _ManagerNeedsBlackboard
    mod.ManagerExplodes = _ManagerExplodes
    sys.modules["dummy_managers_for_tests"] = mod
    yield
    sys.modules.pop("dummy_managers_for_tests", None)


class _Bot:
    """최소 봇 stub"""
    pass


# ============================================================================
# ManagerConfig
# ============================================================================
class TestManagerConfig:
    def test_post_init_fills_defaults(self):
        c = ManagerConfig(
            name="X",
            module_path="m",
            class_name="C",
            attribute_name="x",
            priority=ManagerPriority.MEDIUM,
        )
        assert c.dependencies == []
        assert c.init_args == {}
        assert c.enabled is True
        assert c.post_init is None

    def test_explicit_values_preserved(self):
        c = ManagerConfig(
            name="X",
            module_path="m",
            class_name="C",
            attribute_name="x",
            priority=ManagerPriority.HIGH,
            dependencies=["a", "b"],
            init_args={"foo": 1},
            enabled=False,
        )
        assert c.dependencies == ["a", "b"]
        assert c.init_args == {"foo": 1}
        assert c.enabled is False


# ============================================================================
# 등록
# ============================================================================
class TestRegistration:
    def test_register_single(self):
        bot = _Bot()
        f = ManagerFactory(bot)
        cfg = ManagerConfig(
            name="A", module_path="dummy_managers_for_tests",
            class_name="GoodManager", attribute_name="a",
            priority=ManagerPriority.MEDIUM,
        )
        f.register_manager(cfg)
        assert "a" in f.managers

    def test_register_none_is_safe(self):
        f = ManagerFactory(_Bot())
        f.register_manager(None)  # 예외 없이 무시
        assert len(f.managers) == 0

    def test_register_many(self):
        f = ManagerFactory(_Bot())
        configs = [
            ManagerConfig(name=str(i), module_path="dummy_managers_for_tests",
                          class_name="GoodManager", attribute_name=f"m{i}",
                          priority=ManagerPriority.MEDIUM)
            for i in range(3)
        ]
        f.register_managers(configs)
        assert len(f.managers) == 3

    def test_register_managers_none_is_safe(self):
        f = ManagerFactory(_Bot())
        f.register_managers(None)
        assert len(f.managers) == 0


# ============================================================================
# 초기화
# ============================================================================
class TestInitializeAll:
    def _factory_with(self, *configs):
        f = ManagerFactory(_Bot())
        f.register_managers(list(configs))
        return f

    def test_basic_initialization_success(self):
        f = self._factory_with(
            ManagerConfig(name="A", module_path="dummy_managers_for_tests",
                          class_name="GoodManager", attribute_name="a",
                          priority=ManagerPriority.HIGH)
        )
        stats = f.initialize_all(verbose=False)
        assert stats["succeeded"] == 1
        assert stats["failed"] == 0
        assert f.is_initialized("a") is True
        assert isinstance(f.get_manager("a"), _GoodManager)

    def test_priority_order_respected(self):
        """CRITICAL(0) → HIGH(10) → MEDIUM(20) → LOW(30) 순으로 초기화"""
        f = self._factory_with(
            ManagerConfig(name="Low", module_path="dummy_managers_for_tests",
                          class_name="GoodManager", attribute_name="low",
                          priority=ManagerPriority.LOW),
            ManagerConfig(name="Crit", module_path="dummy_managers_for_tests",
                          class_name="GoodManager", attribute_name="crit",
                          priority=ManagerPriority.CRITICAL),
            ManagerConfig(name="Mid", module_path="dummy_managers_for_tests",
                          class_name="GoodManager", attribute_name="mid",
                          priority=ManagerPriority.MEDIUM),
        )
        f.initialize_all(verbose=False)
        assert f.initialization_order == ["crit", "mid", "low"]

    def test_disabled_manager_skipped(self):
        f = self._factory_with(
            ManagerConfig(name="Off", module_path="dummy_managers_for_tests",
                          class_name="GoodManager", attribute_name="off",
                          priority=ManagerPriority.MEDIUM, enabled=False),
        )
        stats = f.initialize_all(verbose=False)
        assert stats["total"] == 0  # disabled 는 total 에서도 제외
        assert f.is_initialized("off") is False

    def test_init_args_passed_to_constructor(self):
        f = self._factory_with(
            ManagerConfig(name="WithBB", module_path="dummy_managers_for_tests",
                          class_name="ManagerNeedsBlackboard", attribute_name="m",
                          priority=ManagerPriority.MEDIUM,
                          init_args={"blackboard": "MOCK_BB"}),
        )
        f.initialize_all(verbose=False)
        m = f.get_manager("m")
        assert m.blackboard == "MOCK_BB"

    def test_dependency_initialized_first(self):
        """B 가 A 에 의존 → A 가 먼저 초기화"""
        f = self._factory_with(
            ManagerConfig(name="B", module_path="dummy_managers_for_tests",
                          class_name="GoodManager", attribute_name="b",
                          priority=ManagerPriority.MEDIUM, dependencies=["a"]),
            ManagerConfig(name="A", module_path="dummy_managers_for_tests",
                          class_name="GoodManager", attribute_name="a",
                          priority=ManagerPriority.MEDIUM),
        )
        f.initialize_all(verbose=False)
        assert f.initialization_order.index("a") < f.initialization_order.index("b")

    def test_dependency_failure_propagates(self):
        """A 가 import 실패하면 A 에 의존하는 B 도 실패"""
        f = self._factory_with(
            ManagerConfig(name="A", module_path="non.existent.module",
                          class_name="X", attribute_name="a",
                          priority=ManagerPriority.MEDIUM),
            ManagerConfig(name="B", module_path="dummy_managers_for_tests",
                          class_name="GoodManager", attribute_name="b",
                          priority=ManagerPriority.MEDIUM, dependencies=["a"]),
        )
        f.initialize_all(verbose=False)
        assert f.is_initialized("a") is False
        assert f.is_initialized("b") is False
        assert "Dependency failed: a" in f.get_failed_reason("b")

    def test_import_error_recorded(self):
        f = self._factory_with(
            ManagerConfig(name="Broken", module_path="non.existent.module",
                          class_name="X", attribute_name="broken",
                          priority=ManagerPriority.MEDIUM),
        )
        f.initialize_all(verbose=False)
        assert f.is_initialized("broken") is False
        reason = f.get_failed_reason("broken")
        assert reason is not None
        assert "ImportError" in reason

    def test_init_error_recorded(self):
        """매니저 생성자에서 예외 발생 시 InitError 로 기록"""
        f = self._factory_with(
            ManagerConfig(name="Boom", module_path="dummy_managers_for_tests",
                          class_name="ManagerExplodes", attribute_name="boom",
                          priority=ManagerPriority.MEDIUM),
        )
        f.initialize_all(verbose=False)
        assert f.is_initialized("boom") is False
        assert "InitError" in f.get_failed_reason("boom")

    def test_post_init_runs_on_success(self):
        called = {"count": 0}

        def cb(bot, instance):
            called["count"] += 1
            assert isinstance(instance, _GoodManager)

        f = self._factory_with(
            ManagerConfig(name="P", module_path="dummy_managers_for_tests",
                          class_name="GoodManager", attribute_name="p",
                          priority=ManagerPriority.MEDIUM, post_init=cb),
        )
        f.initialize_all(verbose=False)
        assert called["count"] == 1


# ============================================================================
# 통계
# ============================================================================
class TestStatistics:
    def test_statistics_structure(self):
        f = ManagerFactory(_Bot())
        f.register_manager(ManagerConfig(
            name="A", module_path="dummy_managers_for_tests",
            class_name="GoodManager", attribute_name="a",
            priority=ManagerPriority.MEDIUM))
        f.register_manager(ManagerConfig(
            name="Bad", module_path="non.existent",
            class_name="X", attribute_name="bad",
            priority=ManagerPriority.MEDIUM))
        stats = f.initialize_all(verbose=False)

        assert stats["total"] == 2
        assert stats["succeeded"] == 1
        assert stats["failed"] == 1
        assert stats["success_rate"] == 50.0
        assert "bad" in stats["failed_managers"]
        assert "a" in stats["initialization_order"]


# ============================================================================
# 조회 API
# ============================================================================
class TestQueryAPI:
    def test_get_manager_unknown_returns_none(self):
        f = ManagerFactory(_Bot())
        assert f.get_manager("nope") is None

    def test_is_initialized_for_uninit(self):
        f = ManagerFactory(_Bot())
        assert f.is_initialized("nope") is False

    def test_get_failed_reason_unknown_returns_none(self):
        f = ManagerFactory(_Bot())
        assert f.get_failed_reason("nope") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
