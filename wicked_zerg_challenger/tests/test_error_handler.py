# -*- coding: utf-8 -*-
"""
utils/error_handler.py 데코레이터 및 검증 함수 단위 테스트.
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.error_handler import (
    BuildingError,
    ResourceError,
    SC2BotError,
    UnitCommandError,
    UpgradeError,
    log_error_context,
    retry_on_failure,
    safe_execute,
    validate_position,
    validate_unit,
)


class TestSafeExecuteSync(unittest.TestCase):
    def test_success_returns_value(self):
        @safe_execute(default_return="fallback")
        def f(x):
            return x * 2

        self.assertEqual(f(5), 10)

    def test_attribute_error_returns_default(self):
        @safe_execute(default_return="fallback", log_errors=False)
        def f():
            raise AttributeError("oops")

        self.assertEqual(f(), "fallback")

    def test_key_error_returns_default(self):
        @safe_execute(default_return=42, log_errors=False)
        def f():
            d = {}
            return d["missing"]

        self.assertEqual(f(), 42)

    def test_sc2_bot_error_returns_default(self):
        @safe_execute(default_return=None, log_errors=False)
        def f():
            raise BuildingError("can't build")

        self.assertIsNone(f())

    def test_generic_exception_returns_default(self):
        @safe_execute(default_return="generic", log_errors=False)
        def f():
            raise RuntimeError("any error")

        self.assertEqual(f(), "generic")

    def test_default_return_none(self):
        @safe_execute(log_errors=False)
        def f():
            raise IndexError("oops")

        self.assertIsNone(f())


class TestSafeExecuteAsync(unittest.IsolatedAsyncioTestCase):
    async def test_success_returns_value(self):
        @safe_execute(default_return="fallback")
        async def f(x):
            return x * 3

        self.assertEqual(await f(4), 12)

    async def test_exception_returns_default(self):
        @safe_execute(default_return=999, log_errors=False)
        async def f():
            raise KeyError("nope")

        self.assertEqual(await f(), 999)


class TestRetryOnFailureSync(unittest.TestCase):
    def test_success_first_try(self):
        calls = []

        @retry_on_failure(max_retries=3, delay=0)
        def f():
            calls.append(1)
            return "ok"

        self.assertEqual(f(), "ok")
        self.assertEqual(len(calls), 1)

    def test_retries_on_failure_then_succeeds(self):
        attempts = {"count": 0}

        @retry_on_failure(max_retries=3, delay=0)
        def f():
            attempts["count"] += 1
            if attempts["count"] < 2:
                raise AttributeError("first attempt fails")
            return "ok"

        self.assertEqual(f(), "ok")
        self.assertEqual(attempts["count"], 2)

    def test_exhausts_retries(self):
        attempts = {"count": 0}

        @retry_on_failure(max_retries=3, delay=0)
        def f():
            attempts["count"] += 1
            raise AttributeError("always fails")

        result = f()
        self.assertIsNone(result)
        self.assertEqual(attempts["count"], 3)


class TestValidateUnit(unittest.TestCase):
    def test_none_returns_false(self):
        self.assertFalse(validate_unit(None))

    def test_valid_unit_returns_true(self):
        unit = MagicMock()
        unit.tag = 1
        unit.position = (5, 5)
        unit.type_id = "Drone"
        self.assertTrue(validate_unit(unit))

    def test_missing_attr_returns_false(self):
        class _BadUnit:
            @property
            def tag(self):
                raise AttributeError("no tag")

        self.assertFalse(validate_unit(_BadUnit()))


class TestValidatePosition(unittest.TestCase):
    def test_none_returns_false(self):
        self.assertFalse(validate_position(None))

    def test_tuple_returns_true(self):
        self.assertTrue(validate_position((5.0, 7.0)))

    def test_point_returns_true(self):
        from sc2.position import Point2

        self.assertTrue(validate_position(Point2((1, 2))))

    def test_empty_tuple_returns_false(self):
        self.assertFalse(validate_position(()))


class TestExceptionHierarchy(unittest.TestCase):
    def test_all_inherit_from_sc2boterror(self):
        for cls in (
            UnitCommandError,
            UpgradeError,
            BuildingError,
            ResourceError,
        ):
            self.assertTrue(issubclass(cls, SC2BotError))


class TestLogErrorContext(unittest.TestCase):
    def test_does_not_raise_with_none_context(self):
        # Just ensure it doesn't crash
        try:
            log_error_context("test_func", RuntimeError("boom"), context=None)
        except Exception as e:
            self.fail(f"log_error_context raised unexpectedly: {e}")

    def test_does_not_raise_with_context_dict(self):
        try:
            log_error_context(
                "test_func", RuntimeError("boom"), context={"key": "value"}
            )
        except Exception as e:
            self.fail(f"log_error_context raised unexpectedly: {e}")


if __name__ == "__main__":
    unittest.main()
