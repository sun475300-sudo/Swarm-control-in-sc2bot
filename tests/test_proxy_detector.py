"""Regression tests for the proxy_detector distance-aware fix shipped in this PR.

Pre-fix: distance_to_base was computed and discarded — every proxy got
0.8 confidence + HIGH threat regardless of whether it was 50 tiles or 200
tiles from the enemy main.
"""

from __future__ import annotations

from wicked_zerg_challenger.proxy_detector import (
    ProxyDetector,
    ProxyType,
    create_proxy_detector,
)


def _detector_with_known_expansions():
    d = create_proxy_detector()
    # Known expansion locations clustered in one quadrant
    d.initialize_normal_expansions([(140, 140), (130, 140), (140, 130)])
    return d


class TestDistanceAwareConfidence:
    """Pick positions that clear both _is_near_expansion (>15 from any
    expansion) and _is_near_start (>20 from each of the 4 corners
    [(0,0),(150,150),(150,0),(0,150)]) so the proxy branch actually fires.
    """

    def test_close_proxy_lower_confidence_than_far_proxy(self):
        d = _detector_with_known_expansions()
        # close_pos: (100,100) → ~70.7 from enemy base, ~70.7 from nearest
        # corner. far_pos: (30,30) → ~169.7 from base, ~42.4 from nearest
        # corner. Both clear the start-radius gate.
        close_pos = (100, 100)
        far_pos = (30, 30)
        close = d.analyze_enemy_building(close_pos, "gateway")
        far = d.analyze_enemy_building(far_pos, "gateway")
        assert close.is_proxy and far.is_proxy
        assert (
            far.confidence > close.confidence
        ), "Pre-fix bug: every proxy got the same 0.8 confidence"

    def test_far_proxy_escalates_to_critical(self):
        d = _detector_with_known_expansions()
        far_pos = (30, 30)  # ~169 from base, > 100 cutoff
        result = d.analyze_enemy_building(far_pos, "gateway")
        assert result.is_proxy
        assert result.threat_level == "CRITICAL"

    def test_close_proxy_stays_high(self):
        d = _detector_with_known_expansions()
        close_pos = (100, 100)  # ~70.7 from base, < 100 cutoff
        result = d.analyze_enemy_building(close_pos, "gateway")
        assert result.is_proxy
        assert result.threat_level == "HIGH"

    def test_confidence_capped_at_0_95(self):
        d = _detector_with_known_expansions()
        # Maximally far while still clearing start radius:
        # (30, 30) → ~169.7 from base, ~42.4 from nearest corner
        result = d.analyze_enemy_building((30, 30), "barracks")
        assert result.is_proxy
        assert result.confidence <= 0.95

    def test_expansion_pylon_not_flagged(self):
        d = _detector_with_known_expansions()
        result = d.analyze_enemy_building((140, 140), "pylon")
        assert not result.is_proxy
        assert result.proxy_type == ProxyType.UNKNOWN
        assert result.threat_level == "LOW"

    def test_non_proxy_building_type_not_classified(self):
        d = _detector_with_known_expansions()
        # 'roboticsfacility' isn't in the proxy-trigger list
        result = d.analyze_enemy_building((10, 10), "roboticsfacility")
        assert not result.is_proxy
