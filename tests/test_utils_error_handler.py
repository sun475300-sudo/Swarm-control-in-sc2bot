# -*- coding: utf-8 -*-
"""utils.error_handler 테스트 - 데코레이터 + 유효성 검증"""

import sys
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
BOT_ROOT = PROJECT_ROOT / "wicked_zerg_challenger"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))


def _load():
    if "bot_utils_error_handler" in sys.modules:
        return sys.modules["bot_utils_error_handler"]
    spec = importlib.util.spec_from_file_location(
        "bot_utils_error_handler", BOT_ROOT / "utils" / "error_handler.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bot_utils_error_handler"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestExceptionHierarchy:
    def test_base(self):
        m = _load()
        assert issubclass(m.UnitCommandError, m.SC2BotError)
        assert issubclass(m.UpgradeError, m.SC2BotError)
        assert issubclass(m.BuildingError, m.SC2BotError)
        assert issubclass(m.ResourceError, m.SC2BotError)


class TestSafeExecute:
    def test_normal(self):
        m = _load()
        @m.safe_execute(default_return="d")
        def f(x):
            return x * 2
        assert f(5) == 10

    def test_error_returns_default(self):
        m = _load()
        @m.safe_execute(default_return="DEFAULT")
        def fail():
            raise AttributeError("x")
        assert fail() == "DEFAULT"

    def test_unknown_exception(self):
        m = _load()
        @m.safe_execute(default_return="DEFAULT")
        def fail():
            raise RuntimeError("x")
        assert fail() == "DEFAULT"

    def test_sc2_error(self):
        m = _load()
        @m.safe_execute(default_return="DEFAULT")
        def fail():
            raise m.SC2BotError("x")
        assert fail() == "DEFAULT"


class TestValidateUnit:
    def test_valid(self):
        m = _load()
        u = MagicMock()
        u.tag = 1; u.position = MagicMock(); u.type_id = MagicMock()
        assert m.validate_unit(u) is True

    def test_none(self):
        assert _load().validate_unit(None) is False


class TestValidatePosition:
    def test_point2(self):
        m = _load()
        p = MagicMock(); p.x = 10; p.y = 20
        assert m.validate_position(p) is True

    def test_tuple(self):
        assert _load().validate_position((10, 20)) is True

    def test_none(self):
        assert _load().validate_position(None) is False

    def test_empty_tuple(self):
        assert _load().validate_position(()) is False


class TestLogErrorContext:
    def test_with_context(self):
        _load().log_error_context("f", ValueError("e"), context={"k": "v"})

    def test_without_context(self):
        _load().log_error_context("f", RuntimeError("e"))
