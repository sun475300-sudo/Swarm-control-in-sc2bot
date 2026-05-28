# -*- coding: utf-8 -*-
"""Regression tests for DynamicResourceBalancer threshold initialization.

A mojibake-glued line previously swallowed ``self.high_mineral_threshold``
into a comment, so the attribute was never set and ``_analyze`` raised
AttributeError when it read it. These tests lock the thresholds in place.
"""

import os
import sys
from unittest.mock import Mock

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)

try:
    from dynamic_resource_balancer import DynamicResourceBalancer
except ImportError:
    pytest.skip(
        "dynamic_resource_balancer not importable", allow_module_level=True
    )


@pytest.fixture
def balancer():
    return DynamicResourceBalancer(Mock())


def test_high_mineral_threshold_is_set(balancer):
    # The bug: this attribute was lost inside a comment and never assigned.
    assert balancer.high_mineral_threshold == 1500


def test_all_resource_thresholds_present(balancer):
    for attr in (
        "mineral_excess_threshold",
        "gas_shortage_threshold",
        "high_mineral_threshold",
    ):
        assert hasattr(balancer, attr), f"{attr} should be initialized"


def test_threshold_ordering(balancer):
    # The "high" mineral threshold must exceed the plain excess threshold,
    # otherwise the GAS_SHORTAGE rebalance branch can never trigger sanely.
    assert balancer.high_mineral_threshold > balancer.mineral_excess_threshold
