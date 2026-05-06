"""Tests for utils/game_constants helpers introduced in 2026-05-06 round."""

from __future__ import annotations

import math

import pytest
from wicked_zerg_challenger.utils.game_constants import (
    ATTACK_THRESHOLD_TIERS_DEFAULT,
    ATTACK_THRESHOLD_TIERS_VS_PROTOSS,
    GameFrequencies,
    StrategyConstants,
    get_attack_threshold,
    iterations_to_seconds,
    race_gas_timing_seconds,
    seconds_to_iterations,
)


class TestAttackThresholdHelpers:
    """`get_attack_threshold` 단(tier) 표 검증."""

    def test_default_early_game_uses_caller_override(self):
        # caller-provided early/mid override 가 그대로 반영되어야 함
        assert get_attack_threshold(0, vs_protoss=False, early_game_min=8) == 8
        assert get_attack_threshold(120, vs_protoss=False, early_game_min=15) == 15

    def test_default_mid_game_uses_caller_override(self):
        # 4분 ≤ time < 8분 구간은 mid_game_min 사용
        assert get_attack_threshold(300, vs_protoss=False, mid_game_min=22) == 22
        assert get_attack_threshold(479, vs_protoss=False, mid_game_min=18) == 18

    def test_default_late_game_uses_table(self):
        # 단(tier) 표 그대로 — caller override 무시
        assert get_attack_threshold(580, vs_protoss=False, mid_game_min=99) == 30
        assert get_attack_threshold(1200, vs_protoss=False) == 40

    def test_protoss_early_game_higher_threshold(self):
        # vs Protoss 는 동일 시간대에 default 보다 ≥ 큰 임계값
        for t in (0, 100, 200):
            default_v = get_attack_threshold(t, vs_protoss=False, early_game_min=12)
            protoss_v = get_attack_threshold(t, vs_protoss=True)
            assert protoss_v >= default_v
        assert get_attack_threshold(200, vs_protoss=True) == 16

    def test_protoss_late_game_threshold(self):
        assert get_attack_threshold(1200, vs_protoss=True) == 45

    def test_threshold_monotonic_non_decreasing(self):
        # 시간이 흐르면 임계값은 단조 비감소
        prev = -1
        for t in (10, 200, 300, 400, 500, 600, 1200):
            v = get_attack_threshold(t, vs_protoss=False)
            assert v >= prev
            prev = v

        prev = -1
        for t in (10, 200, 300, 400, 500, 600, 1200):
            v = get_attack_threshold(t, vs_protoss=True)
            assert v >= prev
            prev = v

    def test_tier_tables_sorted_by_upper_bound(self):
        for table in (
            ATTACK_THRESHOLD_TIERS_DEFAULT,
            ATTACK_THRESHOLD_TIERS_VS_PROTOSS,
        ):
            uppers = [u for u, _ in table]
            assert uppers == sorted(uppers)
            assert uppers[-1] == math.inf


class TestRaceGasTiming:
    def test_known_races(self):
        assert race_gas_timing_seconds("Protoss") == 75
        assert race_gas_timing_seconds("Terran") == 90
        assert race_gas_timing_seconds("Zerg") == 105
        assert race_gas_timing_seconds("Random") == 90
        assert race_gas_timing_seconds("Unknown") == 90

    def test_unknown_race_default(self):
        assert race_gas_timing_seconds("Klingon") == 90
        assert race_gas_timing_seconds("") == 90

    def test_zerg_slowest_protoss_fastest(self):
        assert (
            race_gas_timing_seconds("Protoss")
            < race_gas_timing_seconds("Terran")
            < race_gas_timing_seconds("Zerg")
        )


class TestStrategyConstants:
    def test_harassment_interval_present(self):
        assert StrategyConstants.EARLY_HARASSMENT_INTERVAL == pytest.approx(15.0)

    def test_log_cooldown_present(self):
        assert StrategyConstants.LOG_COOLDOWN == pytest.approx(5.0)


class TestSecondsIterationsRoundTrip:
    @pytest.mark.parametrize("seconds", [0.5, 1.0, 5.0, 30.0, 60.0, 300.0])
    def test_round_trip(self, seconds):
        iters = seconds_to_iterations(seconds)
        recovered = iterations_to_seconds(iters)
        # int 변환 절단으로 1프레임 미만 오차 허용
        assert abs(recovered - seconds) <= 1.0 / GameFrequencies.GAME_FPS
