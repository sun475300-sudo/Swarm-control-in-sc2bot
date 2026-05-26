# -*- coding: utf-8 -*-
"""Regression: should_expand crash when all townhalls are destroyed."""

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai.zerg_strategy_tree import should_expand


class _FakeTownhalls:
    def __init__(self, items=None):
        self._items = items or []

    @property
    def amount(self):
        return len(self._items)

    @property
    def exists(self):
        return bool(self._items)

    @property
    def first(self):
        return self._items[0]


class TestShouldExpand(unittest.TestCase):
    def test_no_townhalls_does_not_crash(self):
        bot = SimpleNamespace(
            townhalls=_FakeTownhalls([]),
            time=900.0,
            minerals=500,
            already_pending=Mock(return_value=False),
        )

        # Should return False without raising IndexError on `.first`
        self.assertFalse(should_expand(bot))

    def test_expand_when_minerals_and_townhall(self):
        bot = SimpleNamespace(
            townhalls=_FakeTownhalls([SimpleNamespace(type_id="HATCHERY")]),
            time=900.0,
            minerals=500,
            already_pending=Mock(return_value=False),
        )

        self.assertTrue(should_expand(bot))

    def test_no_expand_when_pending(self):
        bot = SimpleNamespace(
            townhalls=_FakeTownhalls([SimpleNamespace(type_id="HATCHERY")]),
            time=900.0,
            minerals=500,
            already_pending=Mock(return_value=True),
        )

        self.assertFalse(should_expand(bot))


if __name__ == "__main__":
    unittest.main()
