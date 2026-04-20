# -*- coding: utf-8 -*-
"""Tests for utils/error_handler.py - exception classes, decorators, validators."""

import sys
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from utils.error_handler import (
    SC2BotError,
    UnitCommandError,
    UpgradeError,
    BuildingError,
    ResourceError,
    safe_execute,
    retry_on_failure,
    validate_unit,
    validate_position,
    log_error_context,
)


class TestExceptionHierarchy:
    def test_sc2_bot_error_is_exception(self):
        assert issubclass(SC2BotError, Exception)

    def test_unit_command_error_is_sc2_bot_error(self):
        assert issubclass(UnitCommandError, SC2BotError)

    def test_upgrade_error_is_sc2_bot_error(self):
        assert issubclass(UpgradeError, SC2BotError)

    def test_building_error_is_sc2_bot_error(self):
        assert issubclass(BuildingError, SC2BotError)

    def test_resource_error_is_sc2_bot_error(self):
        assert issubclass(ResourceError, SC2BotError)

    def test_raise_and_catch_as_base(self):
        with pytest.raises(SC2BotError):
            raise UnitCommandError("test")


class TestSafeExecuteSync:
    def test_decorator_returns_value_on_success(self):
        @safe_execute(default_return="default")
        def good():
            return "value"
        assert good() == "value"

    def test_returns_default_on_attribute_error(self):
        @safe_execute(default_return="fallback")
        def fails():
            raise AttributeError("nope")
        assert fails() == "fallback"

    def test_returns_default_on_key_error(self):
        @safe_execute(default_return=-1)
        def fails():
            raise KeyError("missing")
        assert fails() == -1

    def test_returns_default_on_type_error(self):
        @safe_execute(default_return=None)
        def fails():
            raise TypeError("bad type")
        assert fails() is None

    def test_returns_default_on_sc2_bot_error(self):
        @safe_execute(default_return=0)
        def fails():
            raise UnitCommandError("no unit")
        assert fails() == 0

    def test_returns_default_on_unexpected_error(self):
        @safe_execute(default_return="safe")
        def fails():
            raise RuntimeError("surprise")
        assert fails() == "safe"


class TestRetryOnFailure:
    def test_succeeds_first_try(self):
        calls = [0]

        @retry_on_failure(max_retries=3, delay=0.0)
        def good():
            calls[0] += 1
            return "ok"

        assert good() == "ok"
        assert calls[0] == 1

    def test_retries_and_succeeds(self):
        calls = [0]

        @retry_on_failure(max_retries=3, delay=0.0)
        def eventually_works():
            calls[0] += 1
            if calls[0] < 3:
                raise AttributeError("not yet")
            return "finally!"

        assert eventually_works() == "finally!"
        assert calls[0] == 3

    def test_exhausts_retries_returns_none(self):
        @retry_on_failure(max_retries=2, delay=0.0)
        def always_fails():
            raise KeyError("never works")

        assert always_fails() is None


class TestValidateUnit:
    def test_none_is_invalid(self):
        assert not validate_unit(None)

    def test_valid_unit_like_object(self):
        class Unit:
            tag = 123
            position = (0, 0)
            type_id = "ZERGLING"
        assert validate_unit(Unit())

    def test_missing_attrs_is_invalid(self):
        class BadUnit:
            pass
        assert not validate_unit(BadUnit())


class TestValidatePosition:
    def test_none_is_invalid(self):
        assert not validate_position(None)

    def test_tuple_is_valid(self):
        assert validate_position((10, 20))

    def test_point2_like_object(self):
        class Point:
            x = 5.0
            y = 10.0
        assert validate_position(Point())

    def test_empty_tuple_invalid(self):
        assert not validate_position(())


class TestLogErrorContext:
    def test_does_not_raise_with_context(self):
        try:
            raise ValueError("test error")
        except ValueError as e:
            log_error_context("test_func", e, context={"x": 1})

    def test_does_not_raise_without_context(self):
        try:
            raise RuntimeError("test")
        except RuntimeError as e:
            log_error_context("test_func", e)
