"""
ProxyDetector tests - pure-Python proxy classification logic.

Coverage:
- _classify_proxy: every known building type + unknown
- _is_near_expansion / _is_near_start
- analyze_enemy_building: proxy classification, near-expansion downgrade,
  proxy_history accumulation
- get_proxy_alerts: filters non-proxy results
- calculate_counter_strategy: each known type + unknown fallback
- create_proxy_detector factory
"""

import sys
from pathlib import Path

import pytest

_PKG_ROOT = Path(__file__).resolve().parent.parent / "wicked_zerg_challenger"
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

try:
    from proxy_detector import (
        ProxyDetectionResult,
        ProxyDetector,
        ProxyType,
        create_proxy_detector,
    )
except ImportError:
    pytest.skip("proxy_detector unavailable", allow_module_level=True)


# ---------------------------------------------------------------------------
# Factory + init
# ---------------------------------------------------------------------------


def test_create_proxy_detector_factory_returns_instance():
    d = create_proxy_detector()
    assert isinstance(d, ProxyDetector)
    assert d.bot is None
    assert d.proxy_history == []
    assert d.normal_expansion_locations == []


def test_initialize_normal_expansions_stores_locations():
    d = ProxyDetector()
    d.initialize_normal_expansions([(10, 10), (20, 30)])
    assert d.normal_expansion_locations == [(10, 10), (20, 30)]


# ---------------------------------------------------------------------------
# _distance / _is_near_*
# ---------------------------------------------------------------------------


def test_distance_pythagorean():
    d = ProxyDetector()
    assert d._distance((0, 0), (3, 4)) == 5.0


def test_is_near_expansion_true_within_15():
    d = ProxyDetector()
    d.initialize_normal_expansions([(50, 50)])
    assert d._is_near_expansion((55, 55)) is True  # ~7 distance


def test_is_near_expansion_false_outside_15():
    d = ProxyDetector()
    d.initialize_normal_expansions([(0, 0)])
    assert d._is_near_expansion((20, 20)) is False  # ~28 distance


def test_is_near_start_uses_default_corners():
    d = ProxyDetector()
    # (0, 0) is a corner; threshold is 20.
    assert d._is_near_start((10, 10)) is True
    # Center (75, 75) is far from every corner.
    assert d._is_near_start((75, 75)) is False


# ---------------------------------------------------------------------------
# _classify_proxy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name, expected",
    [
        ("gateway", ProxyType.GATEWAY),
        ("Gateway", ProxyType.GATEWAY),
        ("FORGE", ProxyType.FORGE),
        ("pylon", ProxyType.PYLON),
        ("barracks", ProxyType.BARRACKS),
        ("factory", ProxyType.FACTORY),
        ("starport", ProxyType.STARPORT),
        ("nexus", ProxyType.UNKNOWN),
        ("hatchery", ProxyType.UNKNOWN),
    ],
)
def test_classify_proxy(name, expected):
    d = ProxyDetector()
    assert d._classify_proxy(name) == expected


# ---------------------------------------------------------------------------
# analyze_enemy_building
# ---------------------------------------------------------------------------


def test_analyze_proxy_far_from_anything_flags_high_threat():
    d = ProxyDetector()
    d.initialize_normal_expansions([(100, 100)])
    # (75, 75) is >20 from every default start corner *and* >15 from (100,100).
    result = d.analyze_enemy_building((75, 75), "gateway")
    assert result.is_proxy is True
    assert result.proxy_type == ProxyType.GATEWAY
    assert result.confidence == 0.8
    assert result.threat_level == "HIGH"
    assert "ATTACK gateway" in result.recommendation


def test_analyze_building_near_expansion_is_not_proxy():
    d = ProxyDetector()
    d.initialize_normal_expansions([(50, 50)])
    result = d.analyze_enemy_building((52, 52), "gateway")
    assert result.is_proxy is False
    assert result.threat_level == "LOW"
    assert result.confidence == 0.9


def test_analyze_unknown_building_type_returns_default_result():
    """Buildings outside the known set are not flagged as proxy and don't
    crash; the result keeps its constructor defaults."""
    d = ProxyDetector()
    result = d.analyze_enemy_building((75, 75), "spire")  # not in proxy list
    assert result.is_proxy is False
    assert result.proxy_type == ProxyType.UNKNOWN
    assert result.confidence == 0.0


def test_analyze_appends_to_proxy_history():
    d = ProxyDetector()
    d.initialize_normal_expansions([(100, 100)])
    d.analyze_enemy_building((75, 75), "gateway")
    d.analyze_enemy_building((76, 76), "barracks")
    assert len(d.proxy_history) == 2


# ---------------------------------------------------------------------------
# get_proxy_alerts
# ---------------------------------------------------------------------------


def test_get_proxy_alerts_filters_non_proxy_entries():
    d = ProxyDetector()
    d.initialize_normal_expansions([(50, 50)])
    # One actual proxy, one normal expansion.
    d.analyze_enemy_building((75, 75), "gateway")
    d.analyze_enemy_building((52, 52), "gateway")
    alerts = d.get_proxy_alerts()
    assert len(alerts) == 1
    assert alerts[0].is_proxy is True


# ---------------------------------------------------------------------------
# calculate_counter_strategy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ptype, response, timing",
    [
        (ProxyType.GATEWAY, "RUSH_WITH_ZERGLINGS", "IMMEDIATE"),
        (ProxyType.FORGE, "DEFENSIVE_HOLD", "2_MINUTES"),
        (ProxyType.BARRACKS, "EARLY_ATTACK", "ASAP"),
        (ProxyType.PYLON, "DESTROY_PYLON", "IMMEDIATE"),
        (ProxyType.UNKNOWN, "SCOUT_MORE", "NOW"),
    ],
)
def test_counter_strategy_known_types(ptype, response, timing):
    d = ProxyDetector()
    s = d.calculate_counter_strategy(ptype)
    assert s["response"] == response
    assert s["timing"] == timing
    assert isinstance(s["recommended_units"], list) and s["recommended_units"]


def test_counter_strategy_unmapped_type_falls_back_to_unknown():
    """A ProxyType not present in the strategies dict falls back to UNKNOWN
    (via .get(..., strategies[UNKNOWN]))."""
    d = ProxyDetector()
    # FACTORY is in ProxyType but NOT in the strategies dict, so it should
    # return the UNKNOWN fallback strategy.
    s = d.calculate_counter_strategy(ProxyType.FACTORY)
    assert s["response"] == "SCOUT_MORE"
