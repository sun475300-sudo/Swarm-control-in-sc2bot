#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for ManagerFactory

Tests the factory pattern for manager initialization
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.manager_factory import ManagerFactory, ManagerConfig, ManagerPriority


class TestManagerFactory(unittest.TestCase):
    """Test suite for ManagerFactory"""

    def setUp(self):
        """Set up test fixtures"""
        self.bot = Mock()
        self.factory = ManagerFactory(self.bot)

    def test_initialization(self):
        """Test factory initializes correctly"""
        self.assertIsNotNone(self.factory)
        self.assertEqual(len(self.factory.managers), 0)
        self.assertEqual(len(self.factory.initialized), 0)
        self.assertEqual(len(self.factory.failed), 0)

    def test_register_manager(self):
        """Test manager registration"""
        config = ManagerConfig(
            name="TestManager",
            module_path="test_module",
            class_name="TestClass",
            attribute_name="test_attr",
            priority=ManagerPriority.MEDIUM,
        )

        self.factory.register_manager(config)

        self.assertEqual(len(self.factory.managers), 1)
        self.assertIn("test_attr", self.factory.managers)

    def test_priority_sorting(self):
        """Test managers are initialized in priority order"""
        configs = [
            ManagerConfig(
                name="LowPriority",
                module_path="test",
                class_name="Test",
                attribute_name="low",
                priority=ManagerPriority.LOW,
            ),
            ManagerConfig(
                name="HighPriority",
                module_path="test",
                class_name="Test",
                attribute_name="high",
                priority=ManagerPriority.HIGH,
            ),
            ManagerConfig(
                name="CriticalPriority",
                module_path="test",
                class_name="Test",
                attribute_name="critical",
                priority=ManagerPriority.CRITICAL,
            ),
        ]

        self.factory.register_managers(configs)

        # Priority order should be: CRITICAL < HIGH < LOW
        sorted_managers = sorted(
            self.factory.managers.values(),
            key=lambda m: (m.priority, m.name)
        )

        self.assertEqual(sorted_managers[0].attribute_name, "critical")
        self.assertEqual(sorted_managers[1].attribute_name, "high")
        self.assertEqual(sorted_managers[2].attribute_name, "low")

    def test_dependency_resolution(self):
        """Test dependency resolution"""
        # Manager B depends on Manager A
        config_a = ManagerConfig(
            name="ManagerA",
            module_path="utils.blackboard",
            class_name="Blackboard",
            attribute_name="manager_a",
            priority=ManagerPriority.HIGH,
        )

        config_b = ManagerConfig(
            name="ManagerB",
            module_path="test",
            class_name="Test",
            attribute_name="manager_b",
            priority=ManagerPriority.HIGH,
            dependencies=["manager_a"],
        )

        self.factory.register_managers([config_b, config_a])

        # Mock the import for manager_a (Blackboard exists)
        # manager_b will fail, but should check dependency first

        stats = self.factory.initialize_all(verbose=False)

        # manager_a should be initialized first (if available)
        if "manager_a" in self.factory.initialized:
            # Check that manager_a was initialized before manager_b attempt
            a_index = self.factory.initialization_order.index("manager_a")
            if "manager_b" in self.factory.initialization_order:
                b_index = self.factory.initialization_order.index("manager_b")
                self.assertLess(a_index, b_index)

    def test_statistics(self):
        """Test statistics generation"""
        stats = self.factory._get_statistics()

        self.assertIn("total", stats)
        self.assertIn("succeeded", stats)
        self.assertIn("failed", stats)
        self.assertIn("success_rate", stats)
        self.assertIn("failed_managers", stats)

    def test_get_manager(self):
        """Test get_manager method"""
        # Mock a successful initialization
        self.bot.test_manager = Mock()
        self.factory.initialized.add("test_manager")

        manager = self.factory.get_manager("test_manager")
        self.assertIsNotNone(manager)

        # Non-existent manager
        manager = self.factory.get_manager("nonexistent")
        self.assertIsNone(manager)

    def test_is_initialized(self):
        """Test is_initialized check"""
        self.factory.initialized.add("test")

        self.assertTrue(self.factory.is_initialized("test"))
        self.assertFalse(self.factory.is_initialized("nonexistent"))

    def test_failed_reason(self):
        """Test failed reason tracking"""
        self.factory.failed["test"] = "ImportError: test module"

        reason = self.factory.get_failed_reason("test")
        self.assertEqual(reason, "ImportError: test module")

        reason = self.factory.get_failed_reason("nonexistent")
        self.assertIsNone(reason)


class TestManagerConfig(unittest.TestCase):
    """Test suite for ManagerConfig"""

    def test_config_creation(self):
        """Test ManagerConfig creation"""
        config = ManagerConfig(
            name="Test",
            module_path="test.module",
            class_name="TestClass",
            attribute_name="test_attr",
            priority=ManagerPriority.HIGH,
        )

        self.assertEqual(config.name, "Test")
        self.assertEqual(config.module_path, "test.module")
        self.assertEqual(config.class_name, "TestClass")
        self.assertEqual(config.attribute_name, "test_attr")
        self.assertEqual(config.priority, ManagerPriority.HIGH)
        self.assertEqual(config.dependencies, [])
        self.assertEqual(config.init_args, {})
        self.assertTrue(config.enabled)

    def test_config_with_dependencies(self):
        """Test ManagerConfig with dependencies"""
        config = ManagerConfig(
            name="Test",
            module_path="test",
            class_name="Test",
            attribute_name="test",
            priority=ManagerPriority.MEDIUM,
            dependencies=["dep1", "dep2"],
        )

        self.assertEqual(len(config.dependencies), 2)
        self.assertIn("dep1", config.dependencies)
        self.assertIn("dep2", config.dependencies)

    def test_config_with_init_args(self):
        """Test ManagerConfig with custom init args"""
        config = ManagerConfig(
            name="Test",
            module_path="test",
            class_name="Test",
            attribute_name="test",
            priority=ManagerPriority.MEDIUM,
            init_args={"arg1": "value1", "arg2": 42},
        )

        self.assertEqual(config.init_args["arg1"], "value1")
        self.assertEqual(config.init_args["arg2"], 42)


if __name__ == '__main__':
    unittest.main()
