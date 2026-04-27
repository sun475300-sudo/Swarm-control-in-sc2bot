# -*- coding: utf-8 -*-
"""Tests for core/manager_registry.py — declarative manager configuration."""

import sys
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from core.manager_registry import get_all_manager_configs, get_minimal_manager_configs
from core.manager_factory import ManagerConfig, ManagerPriority


class TestGetAllManagerConfigs:
    def test_returns_list(self):
        configs = get_all_manager_configs()
        assert isinstance(configs, list)

    def test_non_empty(self):
        configs = get_all_manager_configs()
        assert len(configs) > 0

    def test_all_items_are_manager_config(self):
        configs = get_all_manager_configs()
        for config in configs:
            assert isinstance(config, ManagerConfig)

    def test_critical_managers_present(self):
        configs = get_all_manager_configs()
        names = {c.name for c in configs}
        # Blackboard and UnitAuthority are flagged critical
        assert "Blackboard" in names
        assert "UnitAuthorityManager" in names

    def test_no_duplicate_names(self):
        configs = get_all_manager_configs()
        names = [c.name for c in configs]
        assert len(names) == len(set(names)), "Duplicate manager names found"

    def test_no_duplicate_attribute_names(self):
        configs = get_all_manager_configs()
        attrs = [c.attribute_name for c in configs]
        assert len(attrs) == len(set(attrs)), "Duplicate attribute names found"


class TestManagerConfigStructure:
    def test_each_has_required_fields(self):
        configs = get_all_manager_configs()
        for c in configs:
            assert c.name
            assert c.module_path
            assert c.class_name
            assert c.attribute_name
            assert c.priority is not None

    def test_priorities_are_valid_enums(self):
        configs = get_all_manager_configs()
        valid = {
            ManagerPriority.CRITICAL,
            ManagerPriority.HIGH,
            ManagerPriority.MEDIUM,
            ManagerPriority.LOW,
            ManagerPriority.OPTIONAL,
        }
        for c in configs:
            assert c.priority in valid

    def test_critical_managers_have_zero_priority(self):
        configs = get_all_manager_configs()
        critical = [c for c in configs if c.priority == ManagerPriority.CRITICAL]
        for c in critical:
            assert int(c.priority) == 0


class TestPriorityOrdering:
    def test_priority_enum_ordering(self):
        assert ManagerPriority.CRITICAL < ManagerPriority.HIGH
        assert ManagerPriority.HIGH < ManagerPriority.MEDIUM
        assert ManagerPriority.MEDIUM < ManagerPriority.LOW
        assert ManagerPriority.LOW < ManagerPriority.OPTIONAL


class TestDependencies:
    def test_dependency_references_are_valid(self):
        """Every dependency should reference an existing attribute_name."""
        configs = get_all_manager_configs()
        attr_names = {c.attribute_name for c in configs}

        for c in configs:
            for dep in (c.dependencies or []):
                assert dep in attr_names, (
                    f"{c.name} depends on '{dep}' but no manager has that attribute_name"
                )


class TestMinimalConfigs:
    def test_returns_list(self):
        configs = get_minimal_manager_configs()
        assert isinstance(configs, list)

    def test_smaller_than_full(self):
        minimal = get_minimal_manager_configs()
        full = get_all_manager_configs()
        assert len(minimal) <= len(full)

    def test_minimal_includes_critical(self):
        minimal = get_minimal_manager_configs()
        names = {c.name for c in minimal}
        # Minimal configs should always include the CRITICAL managers
        # (exact contents vary, but at least Blackboard should be present)
        assert "Blackboard" in names or any(
            c.priority == ManagerPriority.CRITICAL for c in minimal
        )


class TestManagerConfigDataclass:
    def test_dependencies_defaults_to_empty_list(self):
        mc = ManagerConfig(
            name="TestMgr",
            module_path="test_mod",
            class_name="TestClass",
            attribute_name="test_attr",
            priority=ManagerPriority.HIGH,
        )
        assert mc.dependencies == []

    def test_enabled_defaults_true(self):
        mc = ManagerConfig(
            name="T",
            module_path="x",
            class_name="Y",
            attribute_name="z",
            priority=ManagerPriority.LOW,
        )
        assert mc.enabled is True
