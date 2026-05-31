"""
GameConfig invariants and consistency checks.

These tests pin the cross-constant relationships that are easy to break
by tweaking one value without considering its dependencies.
"""

import pytest

try:
    from wicked_zerg_challenger.game_config import GameConfig
except ImportError:
    pytest.skip("game_config unavailable", allow_module_level=True)


# ---------------------------------------------------------------------------
# Phase / timing ordering
# ---------------------------------------------------------------------------


def test_phase_timings_strictly_increasing():
    assert (
        GameConfig.OPENING_PHASE_END
        < GameConfig.EARLY_GAME_END
        < GameConfig.MID_GAME_END
    ), "phase boundaries must be strictly increasing"


def test_expansion_supply_thresholds_monotonic():
    """Natural < Third < Fourth."""
    assert (
        GameConfig.NATURAL_EXPANSION_TIMING
        < GameConfig.THIRD_BASE_TIMING
        < GameConfig.FOURTH_BASE_TIMING
    )


def test_natural_expansion_time_within_opening_phase():
    """Natural expand should fit before opening ends — otherwise build order
    has no time to apply pressure before mid-game phase logic kicks in."""
    assert GameConfig.NATURAL_EXPANSION_TIME < GameConfig.OPENING_PHASE_END


# ---------------------------------------------------------------------------
# Economy constants
# ---------------------------------------------------------------------------


def test_drone_caps_consistent():
    assert GameConfig.DRONE_LIMIT_PER_BASE < GameConfig.DRONE_LIMIT_PER_BASE_GAS
    assert GameConfig.MIN_DRONES <= GameConfig.MAX_DRONES


def test_drone_limit_per_base_gas_equals_minerals_plus_gas():
    """Per code comment: 16 mineral + 6 gas = 22."""
    assert (
        GameConfig.DRONE_LIMIT_PER_BASE_GAS
        == GameConfig.DRONE_LIMIT_PER_BASE + 6
    )


def test_mineral_thresholds_strictly_increasing():
    assert (
        GameConfig.MINERAL_BANKING_THRESHOLD
        < GameConfig.MINERAL_OVERFLOW
        < GameConfig.MINERAL_CRITICAL
    )


def test_gas_thresholds_strictly_increasing():
    assert GameConfig.GAS_OVERFLOW_THRESHOLD < GameConfig.GAS_CRITICAL


def test_supply_buffers_non_negative_and_within_supply_cap():
    for buffer in (
        GameConfig.SUPPLY_BUFFER_OPENING,
        GameConfig.SUPPLY_BUFFER_EARLY,
        GameConfig.SUPPLY_BUFFER_MID,
        GameConfig.SUPPLY_BUFFER_HIGH_GAS,
    ):
        assert 0 <= buffer < GameConfig.SUPPLY_CAP


def test_supply_cap_matches_sc2_max():
    assert GameConfig.SUPPLY_CAP == 200


# ---------------------------------------------------------------------------
# Combat thresholds
# ---------------------------------------------------------------------------


def test_engage_higher_than_retreat_ratio():
    """The army-ratio at which we choose to engage must be strictly above
    the ratio at which we choose to retreat — otherwise we oscillate."""
    assert GameConfig.ENGAGE_ARMY_RATIO > GameConfig.RETREAT_ARMY_RATIO


def test_combat_ratios_in_unit_range():
    for ratio in (
        GameConfig.ENGAGE_ARMY_RATIO,
        GameConfig.RETREAT_ARMY_RATIO,
        GameConfig.TARGET_ARMY_RATIO,
    ):
        assert 0.0 < ratio < 1.0


# ---------------------------------------------------------------------------
# Cache TTL ordering
# ---------------------------------------------------------------------------


def test_cache_ttls_strictly_increasing():
    assert (
        GameConfig.CACHE_TTL_SHORT
        < GameConfig.CACHE_TTL_MEDIUM
        < GameConfig.CACHE_TTL_LONG
    )


# ---------------------------------------------------------------------------
# Update intervals — frequent <= rare
# ---------------------------------------------------------------------------


def test_update_intervals_consistent():
    assert (
        GameConfig.MICRO_UPDATE_INTERVAL
        <= GameConfig.COMBAT_UPDATE_INTERVAL
        <= GameConfig.ECONOMY_UPDATE_INTERVAL
        <= GameConfig.CREEP_UPDATE_INTERVAL
        <= GameConfig.TECH_UPDATE_INTERVAL
    )


def test_log_intervals_strictly_increasing():
    assert (
        GameConfig.LOG_INTERVAL_FREQUENT
        < GameConfig.LOG_INTERVAL_NORMAL
        < GameConfig.LOG_INTERVAL_RARE
    )


# ---------------------------------------------------------------------------
# Production priorities — workers > defense > army > tech
# ---------------------------------------------------------------------------


def test_production_priority_ordering():
    assert (
        GameConfig.PRODUCTION_PRIORITY_WORKER
        > GameConfig.PRODUCTION_PRIORITY_DEFENSE
        > GameConfig.PRODUCTION_PRIORITY_ARMY
        > GameConfig.PRODUCTION_PRIORITY_TECH
    )


# ---------------------------------------------------------------------------
# Twelve pool / opening rush invariants
# ---------------------------------------------------------------------------


def test_pool_supply_rush_below_standard():
    """12-pool rush triggers earlier than the standard 13-pool opening."""
    assert (
        GameConfig.SPAWNING_POOL_SUPPLY_RUSH < GameConfig.SPAWNING_POOL_SUPPLY_STANDARD
    )


def test_baneling_bust_pool_before_gas():
    """For a baneling bust we need the pool before the extractor."""
    assert (
        GameConfig.BANELING_BUST_POOL_TIMING
        <= GameConfig.BANELING_BUST_GAS_TIMING
    )


def test_early_zergling_target_grows_over_time():
    assert (
        GameConfig.EARLY_ZERGLING_TARGET_2MIN < GameConfig.EARLY_ZERGLING_TARGET_3MIN
    )


# ---------------------------------------------------------------------------
# Reward sanity
# ---------------------------------------------------------------------------


def test_reward_signs_make_sense():
    assert GameConfig.REWARD_WIN > 0 > GameConfig.REWARD_LOSS
    assert GameConfig.REWARD_EARLY_DEFENSE_BONUS > 0
    assert GameConfig.REWARD_EARLY_DEFENSE_PENALTY < 0


def test_learning_rate_in_typical_range():
    assert 0.0 < GameConfig.LEARNING_RATE_DEFAULT <= 0.1
    assert 0.0 < GameConfig.DISCOUNT_FACTOR < 1.0


# ---------------------------------------------------------------------------
# Worker assignment per patch
# ---------------------------------------------------------------------------


def test_close_patch_worker_count_higher_than_far():
    assert (
        GameConfig.WORKERS_PER_CLOSE_PATCH >= GameConfig.WORKERS_PER_FAR_PATCH
    )


def test_depleted_thresholds_consistent():
    """Single-patch depletion should fire before whole-base depletion."""
    assert (
        GameConfig.DEPLETED_PATCH_THRESHOLD < GameConfig.DEPLETED_BASE_TOTAL_THRESHOLD
    )


# ---------------------------------------------------------------------------
# Queen specialization energy invariants
# ---------------------------------------------------------------------------


def test_queen_creep_spread_below_inject_threshold():
    """An inject-queen needs more energy to additionally spread creep
    (inject 25 + creep 25 = 50) — so the spread-only threshold is lower."""
    assert (
        GameConfig.QUEEN_CREEP_SPREAD_ENERGY
        <= GameConfig.QUEEN_INJECT_ENERGY_THRESHOLD
    )


def test_queen_inject_creep_threshold_above_inject_only():
    """A queen that injects then creeps needs more energy than inject-only."""
    assert (
        GameConfig.QUEEN_INJECT_QUEEN_CREEP_ENERGY
        > GameConfig.QUEEN_INJECT_ENERGY_THRESHOLD
    )


def test_queen_transfuse_threshold_at_least_50():
    """Transfusion costs 50 energy."""
    assert GameConfig.QUEEN_TRANSFUSE_ENERGY_THRESHOLD >= 50
