# -*- coding: utf-8 -*-
"""Regression tests for ai.zerg_strategy_tree helpers."""

import os
import sys
import unittest
from unittest.mock import MagicMock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ai.zerg_strategy_tree import should_expand


class _FakeTownhalls:
    """Minimal stand-in for sc2 Units that supports `amount`, `first`, and truthiness."""

    def __init__(self, members=None):
        members = list(members or [])
        self._members = members
        self.amount = len(members)
        self.first = members[0] if members else None

    def __bool__(self):
        return bool(self._members)

    def __len__(self):
        return len(self._members)


def _make_townhall(type_id="HATCHERY"):
    th = MagicMock()
    th.type_id = type_id
    return th


def _make_bot(*, townhalls, minerals=400, time=180, pending=False):
    bot = MagicMock()
    bot.townhalls = townhalls
    bot.minerals = minerals
    bot.time = time
    bot.already_pending = MagicMock(return_value=1 if pending else 0)
    return bot


class TestShouldExpand(unittest.TestCase):
    def test_no_townhalls_attr_returns_false(self):
        bot = object()
        self.assertFalse(should_expand(bot))

    def test_no_bases_returns_false_without_crash(self):
        """Regression: previously crashed on AttributeError when first was None."""
        bot = _make_bot(townhalls=_FakeTownhalls([]))
        self.assertFalse(should_expand(bot))

    def test_two_bases_under_two_minutes_returns_false(self):
        bot = _make_bot(townhalls=_FakeTownhalls([_make_townhall(), _make_townhall()]), time=100)
        self.assertFalse(should_expand(bot))

    def test_one_base_with_enough_minerals_returns_true(self):
        bot = _make_bot(townhalls=_FakeTownhalls([_make_townhall()]), minerals=400, time=200)
        self.assertTrue(should_expand(bot))

    def test_pending_hatchery_blocks_expansion(self):
        bot = _make_bot(
            townhalls=_FakeTownhalls([_make_townhall()]), minerals=600, time=200, pending=True
        )
        self.assertFalse(should_expand(bot))

    def test_low_minerals_blocks_expansion(self):
        bot = _make_bot(townhalls=_FakeTownhalls([_make_townhall()]), minerals=100, time=200)
        self.assertFalse(should_expand(bot))


if __name__ == "__main__":
    unittest.main()
