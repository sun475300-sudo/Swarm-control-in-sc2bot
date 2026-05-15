# -*- coding: utf-8 -*-
"""ProxyDetector 단위 테스트.

프록시 건물 감지(가까운 확장/시작 위치 분기), counter strategy 매핑,
prox history 누적, 누락된 factory/starport 회귀 가드.
"""

import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from proxy_detector import (
    ProxyDetectionResult,
    ProxyDetector,
    ProxyType,
    create_proxy_detector,
)


class TestProxyClassification(unittest.TestCase):
    def setUp(self):
        self.det = ProxyDetector()

    def test_classify_known(self):
        self.assertEqual(self.det._classify_proxy("gateway"), ProxyType.GATEWAY)
        self.assertEqual(self.det._classify_proxy("forge"), ProxyType.FORGE)
        self.assertEqual(self.det._classify_proxy("pylon"), ProxyType.PYLON)
        self.assertEqual(self.det._classify_proxy("barracks"), ProxyType.BARRACKS)
        self.assertEqual(self.det._classify_proxy("factory"), ProxyType.FACTORY)
        self.assertEqual(self.det._classify_proxy("starport"), ProxyType.STARPORT)

    def test_classify_unknown(self):
        self.assertEqual(self.det._classify_proxy("nydus"), ProxyType.UNKNOWN)


class TestAnalyzeEnemyBuilding(unittest.TestCase):
    def setUp(self):
        self.det = ProxyDetector()

    def test_far_from_base_marked_proxy(self):
        # 시작 위치(0,0), (150,150) 등에서 멀리 떨어진 위치
        result = self.det.analyze_enemy_building((75, 75), "gateway")
        self.assertTrue(result.is_proxy)
        self.assertEqual(result.proxy_type, ProxyType.GATEWAY)
        self.assertEqual(result.threat_level, "HIGH")

    def test_near_expansion_not_proxy(self):
        self.det.initialize_normal_expansions([(75, 75)])
        result = self.det.analyze_enemy_building((75, 75), "gateway")
        self.assertFalse(result.is_proxy)

    def test_factory_proxy_regression_guard(self):
        """이전 버전 회귀: factory/starport 가 후보에 누락되어 탐지 실패."""
        result = self.det.analyze_enemy_building((75, 75), "factory")
        self.assertTrue(result.is_proxy)
        self.assertEqual(result.proxy_type, ProxyType.FACTORY)

    def test_starport_proxy_regression_guard(self):
        result = self.det.analyze_enemy_building((75, 75), "starport")
        self.assertTrue(result.is_proxy)
        self.assertEqual(result.proxy_type, ProxyType.STARPORT)

    def test_unknown_building_does_not_mark_proxy(self):
        result = self.det.analyze_enemy_building((75, 75), "nydus_canal")
        self.assertFalse(result.is_proxy)


class TestProxyHistory(unittest.TestCase):
    def test_history_accumulates(self):
        det = ProxyDetector()
        det.analyze_enemy_building((75, 75), "gateway")
        det.analyze_enemy_building((75, 75), "forge")
        self.assertEqual(len(det.proxy_history), 2)

    def test_get_proxy_alerts_filters(self):
        det = ProxyDetector()
        det.initialize_normal_expansions([(50, 50)])
        det.analyze_enemy_building((50, 50), "gateway")  # not proxy
        det.analyze_enemy_building((75, 75), "barracks")  # proxy
        alerts = det.get_proxy_alerts()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].proxy_type, ProxyType.BARRACKS)


class TestCounterStrategy(unittest.TestCase):
    def setUp(self):
        self.det = ProxyDetector()

    def test_gateway_counter(self):
        strat = self.det.calculate_counter_strategy(ProxyType.GATEWAY)
        self.assertEqual(strat["response"], "RUSH_WITH_ZERGLINGS")
        self.assertEqual(strat["timing"], "IMMEDIATE")

    def test_unknown_fallback(self):
        strat = self.det.calculate_counter_strategy(ProxyType.UNKNOWN)
        self.assertIn("response", strat)
        self.assertIn("recommended_units", strat)


class TestFactoryHelper(unittest.TestCase):
    def test_create_proxy_detector(self):
        d = create_proxy_detector()
        self.assertIsInstance(d, ProxyDetector)


class TestDistanceUtility(unittest.TestCase):
    def test_distance_pythagoras(self):
        det = ProxyDetector()
        self.assertAlmostEqual(det._distance((0, 0), (3, 4)), 5.0)


if __name__ == "__main__":
    unittest.main()
