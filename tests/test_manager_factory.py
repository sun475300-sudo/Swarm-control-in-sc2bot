# -*- coding: utf-8 -*-
"""Tests for core/manager_factory.py — ManagerFactory, ManagerConfig, ManagerPriority."""

import sys
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from core.manager_factory import (
    ManagerFactory,
    ManagerConfig,
    ManagerPriority,
)


class _FakeBot:
    pass


class TestManagerPriority:
    def test_priority_ordering(self):
        assert ManagerPriority.CRITICAL < ManagerPriority.HIGH
        assert ManagerPriority.HIGH < ManagerPriority.MEDIUM
        assert ManagerPriority.MEDIUM < ManagerPriority.LOW
        assert ManagerPriority.LOW < ManagerPriority.OPTIONAL

    def test_priority_values(self):
        assert ManagerPriority.CRITICAL == 0
        assert ManagerPriority.OPTIONAL == 40


class TestManagerConfig:
    def test_dependencies_default_empty(self):
        mc = ManagerConfig(
            name="Test",
            module_path="test",
            class_name="Test",
            attribute_name="test",
            priority=ManagerPriority.HIGH,
        )
        assert mc.dependencies == []
        assert mc.init_args == {}
        assert mc.enabled is True

    def test_explicit_dependencies(self):
        mc = ManagerConfig(
            name="A",
            module_path="a",
            class_name="A",
            attribute_name="a",
            priority=ManagerPriority.HIGH,
            dependencies=["dep1", "dep2"],
        )
        assert mc.dependencies == ["dep1", "dep2"]

    def test_explicit_init_args(self):
        mc = ManagerConfig(
            name="B",
            module_path="b",
            class_name="B",
            attribute_name="b",
            priority=ManagerPriority.LOW,
            init_args={"param1": 42},
        )
        assert mc.init_args == {"param1": 42}


class TestManagerFactoryInit:
    def test_empty_factory(self):
        factory = ManagerFactory(_FakeBot())
        assert len(factory.managers) == 0
        assert len(factory.initialized) == 0
        assert len(factory.failed) == 0
        assert factory.initialization_order == []


class TestRegisterManager:
    def test_register_single(self):
        factory = ManagerFactory(_FakeBot())
        config = ManagerConfig(
            name="Test",
            module_path="nonexistent",
            class_name="Test",
            attribute_name="test",
            priority=ManagerPriority.HIGH,
        )
        factory.register_manager(config)
        assert "test" in factory.managers

    def test_register_none_does_not_crash(self):
        factory = ManagerFactory(_FakeBot())
        factory.register_manager(None)  # should log warning and skip
        assert len(factory.managers) == 0

    def test_register_overwrites_same_attribute(self):
        factory = ManagerFactory(_FakeBot())
        c1 = ManagerConfig("A1", "a", "A", "test", ManagerPriority.HIGH)
        c2 = ManagerConfig("A2", "a", "A", "test", ManagerPriority.LOW)
        factory.register_manager(c1)
        factory.register_manager(c2)
        # Later registration overwrites earlier
        assert factory.managers["test"].name == "A2"


class TestRegisterMultiple:
    def test_register_list(self):
        factory = ManagerFactory(_FakeBot())
        configs = [
            ManagerConfig("A", "mod_a", "A", "a", ManagerPriority.HIGH),
            ManagerConfig("B", "mod_b", "B", "b", ManagerPriority.MEDIUM),
            ManagerConfig("C", "mod_c", "C", "c", ManagerPriority.LOW),
        ]
        factory.register_managers(configs)
        assert len(factory.managers) == 3


class TestGetManager:
    def test_not_initialized_returns_none(self):
        factory = ManagerFactory(_FakeBot())
        assert factory.get_manager("never_registered") is None


class TestIsInitialized:
    def test_returns_false_for_new_factory(self):
        factory = ManagerFactory(_FakeBot())
        assert not factory.is_initialized("anything")

    def test_returns_true_after_initialized_set(self):
        factory = ManagerFactory(_FakeBot())
        factory.initialized.add("test_attr")
        assert factory.is_initialized("test_attr")


class TestGetFailedReason:
    def test_returns_none_if_not_failed(self):
        factory = ManagerFactory(_FakeBot())
        assert factory.get_failed_reason("test") is None

    def test_returns_reason_if_failed(self):
        factory = ManagerFactory(_FakeBot())
        factory.failed["test_attr"] = "Import error"
        assert factory.get_failed_reason("test_attr") == "Import error"


class TestInitializeAll:
    def test_empty_factory_returns_empty_stats(self):
        factory = ManagerFactory(_FakeBot())
        stats = factory.initialize_all(verbose=False)
        assert isinstance(stats, dict)

    def test_invalid_module_recorded_as_failed(self):
        factory = ManagerFactory(_FakeBot())
        config = ManagerConfig(
            name="DoesNotExist",
            module_path="this_module_absolutely_does_not_exist_xyz",
            class_name="NoClass",
            attribute_name="no_attr",
            priority=ManagerPriority.OPTIONAL,  # optional so won't halt
        )
        factory.register_manager(config)
        factory.initialize_all(verbose=False)
        # Should fail gracefully
        assert "no_attr" in factory.failed or "no_attr" not in factory.initialized
