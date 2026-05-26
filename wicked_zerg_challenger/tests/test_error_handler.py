# -*- coding: utf-8 -*-
"""error_handler 단위 테스트.

safe_execute / retry_on_failure / validate_unit / validate_position의
sync 경로와 SC2BotError 계층 분기를 검증한다. async 경로는 conftest의
경량 asyncio 러너를 통해 검증.
"""

import asyncio
import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.error_handler import (
    BuildingError,
    ResourceError,
    SC2BotError,
    UnitCommandError,
    UpgradeError,
    retry_on_failure,
    safe_execute,
    validate_position,
    validate_unit,
)


class TestSafeExecuteSync(unittest.TestCase):
    def test_returns_value_on_success(self):
        @safe_execute(default_return=-1)
        def f(x):
            return x * 2

        self.assertEqual(f(5), 10)

    def test_returns_default_on_attribute_error(self):
        @safe_execute(default_return="fallback", log_errors=False)
        def f():
            raise AttributeError("x")

        self.assertEqual(f(), "fallback")

    def test_returns_default_on_sc2bot_error(self):
        @safe_execute(default_return=42, log_errors=False)
        def f():
            raise UnitCommandError("bad")

        self.assertEqual(f(), 42)

    def test_returns_default_on_unexpected_error(self):
        @safe_execute(default_return=0, log_errors=False)
        def f():
            raise RuntimeError("anything")

        self.assertEqual(f(), 0)

    def test_kwargs_passed_through(self):
        @safe_execute()
        def f(**kw):
            return kw.get("val")

        self.assertEqual(f(val="ok"), "ok")


class TestRetryOnFailureSync(unittest.TestCase):
    def test_succeeds_on_first_try(self):
        call_count = [0]

        @retry_on_failure(max_retries=3, delay=0.0)
        def f():
            call_count[0] += 1
            return "ok"

        self.assertEqual(f(), "ok")
        self.assertEqual(call_count[0], 1)

    def test_retries_then_returns_none(self):
        call_count = [0]

        @retry_on_failure(max_retries=3, delay=0.0)
        def f():
            call_count[0] += 1
            raise AttributeError("x")

        result = f()
        self.assertIsNone(result)
        self.assertEqual(call_count[0], 3)

    def test_retries_and_succeeds(self):
        call_count = [0]

        @retry_on_failure(max_retries=3, delay=0.0)
        def f():
            call_count[0] += 1
            if call_count[0] < 2:
                raise KeyError("first attempt")
            return "ok"

        self.assertEqual(f(), "ok")
        self.assertEqual(call_count[0], 2)


class TestRetryOnFailureAsync(unittest.TestCase):
    def test_async_succeeds_on_first_try(self):
        @retry_on_failure(max_retries=3, delay=0.0)
        async def f():
            return "async-ok"

        result = asyncio.run(f())
        self.assertEqual(result, "async-ok")

    def test_async_retries_then_none(self):
        call_count = [0]

        @retry_on_failure(max_retries=3, delay=0.0)
        async def f():
            call_count[0] += 1
            raise IndexError()

        result = asyncio.run(f())
        self.assertIsNone(result)
        self.assertEqual(call_count[0], 3)


class TestExceptionHierarchy(unittest.TestCase):
    def test_sc2bot_error_is_exception(self):
        self.assertTrue(issubclass(SC2BotError, Exception))

    def test_subclasses_of_sc2bot_error(self):
        for klass in (UnitCommandError, UpgradeError, BuildingError, ResourceError):
            self.assertTrue(issubclass(klass, SC2BotError))


class TestValidateUnit(unittest.TestCase):
    class _Unit:
        def __init__(self, tag, position, type_id):
            self.tag = tag
            self.position = position
            self.type_id = type_id

    def test_valid_unit(self):
        u = self._Unit(123, (1, 2), "ZERGLING")
        self.assertTrue(validate_unit(u))

    def test_none_unit(self):
        self.assertFalse(validate_unit(None))

    def test_missing_attribute(self):
        class Bad:
            tag = 1
            # missing position / type_id

        self.assertFalse(validate_unit(Bad()))


class TestValidatePosition(unittest.TestCase):
    class _Point:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    def test_point_object(self):
        self.assertTrue(validate_position(self._Point(0, 0)))

    def test_tuple(self):
        self.assertTrue(validate_position((1.0, 2.0)))

    def test_none(self):
        self.assertFalse(validate_position(None))

    def test_invalid_object(self):
        self.assertFalse(validate_position(object()))


if __name__ == "__main__":
    unittest.main()
