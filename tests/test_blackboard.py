"""Unit tests for the GameStateBlackboard.

Covers the production queue, building reservations, per-key TTL cache,
state sync, and the should_defend / can_attack / should_expand decision
helpers. All tests are pure-Python — no SC2 game state needed.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add wicked_zerg_challenger/ itself to sys.path so the blackboard's
# transitive `from utils.logger import get_logger` resolves under the
# bot's "package directory on sys.path" runtime convention. Without
# this, simply importing blackboard via the package prefix would
# trigger ModuleNotFoundError for `utils.logger` and also leak into
# other test modules' bare-name imports (#dependency: must run before
# the wicked_zerg_challenger.* import below).
_PKG = Path(__file__).resolve().parent.parent / "wicked_zerg_challenger"
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

import pytest  # noqa: E402

try:
    from wicked_zerg_challenger.blackboard import (  # noqa: E402
        GamePhase,
        GameStateBlackboard,
        ThreatLevel,
    )
except ImportError as exc:  # pragma: no cover
    pytest.skip(f"blackboard import failed: {exc}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Generic state set/get
# ---------------------------------------------------------------------------


class TestStateSetGet:
    def test_get_returns_default_when_missing(self):
        bb = GameStateBlackboard()
        assert bb.get("missing", "fallback") == "fallback"

    def test_set_then_get_round_trips(self):
        bb = GameStateBlackboard()
        bb.set("foo", 42)
        assert bb.get("foo") == 42

    def test_set_strategy_mode_syncs_attribute(self):
        bb = GameStateBlackboard()
        bb.set("strategy_mode", "AGGRESSIVE")
        assert bb.strategy_mode == "AGGRESSIVE"

    def test_set_enemy_race_syncs_attribute(self):
        bb = GameStateBlackboard()
        bb.set("enemy_race", "zerg")
        assert bb.enemy_race == "zerg"

    def test_set_is_rush_detected_syncs_threat(self):
        bb = GameStateBlackboard()
        bb.set("is_rush_detected", True)
        assert bb.threat.is_rushing is True


# ---------------------------------------------------------------------------
# Game-phase auto-derivation in update_game_info
# ---------------------------------------------------------------------------


class TestGamePhaseDerivation:
    @pytest.mark.parametrize(
        "game_time,expected",
        [
            (0.0, GamePhase.OPENING),
            (179.9, GamePhase.OPENING),
            (180.0, GamePhase.EARLY_GAME),
            (359.9, GamePhase.EARLY_GAME),
            (360.0, GamePhase.MID_GAME),
            (719.9, GamePhase.MID_GAME),
            (720.0, GamePhase.LATE_GAME),
            (1500.0, GamePhase.LATE_GAME),
        ],
    )
    def test_phase_thresholds(self, game_time, expected):
        bb = GameStateBlackboard()
        bb.update_game_info(game_time)
        assert bb.game_phase == expected


# ---------------------------------------------------------------------------
# Production queue priority + dedup
# ---------------------------------------------------------------------------


class TestProductionQueue:
    def test_get_next_returns_highest_priority(self):
        bb = GameStateBlackboard()
        bb.request_production("ZERGLING", 5, "EconMgr", priority=3)
        bb.request_production("DRONE", 2, "DefenseCoord", priority=0)
        bb.request_production("ROACH", 3, "Strategy", priority=2)

        first = bb.get_next_production()
        assert first == ("DRONE", 2, "DefenseCoord")

    def test_drains_in_priority_order(self):
        bb = GameStateBlackboard()
        bb.request_production("A", 1, "X", priority=2)
        bb.request_production("B", 1, "Y", priority=1)
        bb.request_production("C", 1, "Z", priority=0)

        order = [bb.get_next_production() for _ in range(3)]

        assert [r[0] for r in order] == ["C", "B", "A"]

    def test_returns_none_when_empty(self):
        bb = GameStateBlackboard()
        assert bb.get_next_production() is None

    def test_duplicate_request_updates_count(self):
        """Same (unit_type, requester) at same priority must update count, not duplicate."""
        bb = GameStateBlackboard()
        bb.request_production("ZERGLING", 5, "EconMgr", priority=1)
        bb.request_production("ZERGLING", 9, "EconMgr", priority=1)

        first = bb.get_next_production()
        second = bb.get_next_production()
        assert first == ("ZERGLING", 9, "EconMgr")
        assert second is None

    def test_clear_all_requests(self):
        bb = GameStateBlackboard()
        bb.request_production("A", 1, "X", priority=1)
        bb.request_production("B", 1, "Y", priority=2)

        bb.clear_production_requests()

        assert bb.get_next_production() is None

    def test_clear_only_specific_requester(self):
        bb = GameStateBlackboard()
        bb.request_production("A", 1, "Keep", priority=1)
        bb.request_production("B", 1, "Drop", priority=1)
        bb.request_production("C", 1, "Drop", priority=2)

        bb.clear_production_requests(requester="Drop")

        remaining = []
        while True:
            r = bb.get_next_production()
            if r is None:
                break
            remaining.append(r)
        assert remaining == [("A", 1, "Keep")]


# ---------------------------------------------------------------------------
# Building reservation
# ---------------------------------------------------------------------------


class TestBuildingReservation:
    def test_first_reservation_succeeds(self):
        bb = GameStateBlackboard()
        bb.game_time = 100.0
        assert bb.reserve_building("SPAWNINGPOOL", "BuildOrder", duration=10.0) is True

    def test_second_reservation_within_duration_fails(self):
        bb = GameStateBlackboard()
        bb.game_time = 100.0
        bb.reserve_building("SPAWNINGPOOL", "First", duration=10.0)

        bb.game_time = 105.0  # 5s later, within 10s window
        assert bb.reserve_building("SPAWNINGPOOL", "Second", duration=10.0) is False

    def test_reservation_renewable_after_expiry(self):
        bb = GameStateBlackboard()
        bb.game_time = 100.0
        bb.reserve_building("SPAWNINGPOOL", "First", duration=10.0)

        bb.game_time = 115.0  # 15s later, past 10s expiry
        assert bb.reserve_building("SPAWNINGPOOL", "Second", duration=10.0) is True

    def test_is_building_reserved_within_window(self):
        bb = GameStateBlackboard()
        bb.game_time = 100.0
        bb.reserve_building("EVOLUTIONCHAMBER", "X", duration=8.0)

        bb.game_time = 105.0
        assert bb.is_building_reserved("EVOLUTIONCHAMBER", duration=8.0) is True

    def test_is_building_reserved_after_expiry(self):
        bb = GameStateBlackboard()
        bb.game_time = 100.0
        bb.reserve_building("EVOLUTIONCHAMBER", "X", duration=8.0)

        bb.game_time = 110.0
        assert bb.is_building_reserved("EVOLUTIONCHAMBER", duration=8.0) is False


# ---------------------------------------------------------------------------
# Per-key TTL cache
# ---------------------------------------------------------------------------


class TestCache:
    def test_cache_get_returns_default_for_missing(self):
        bb = GameStateBlackboard()
        assert bb.cache_get("nope", default=99) == 99

    def test_cache_set_get_within_ttl(self):
        bb = GameStateBlackboard()
        bb.game_time = 100.0
        bb.cache_set("k", "v", ttl=5.0)

        bb.game_time = 103.0
        assert bb.cache_get("k") == "v"

    def test_cache_get_returns_default_after_ttl(self):
        bb = GameStateBlackboard()
        bb.game_time = 100.0
        bb.cache_set("k", "v", ttl=5.0)

        bb.game_time = 110.0  # 10s > 5s ttl
        assert bb.cache_get("k", default="expired") == "expired"

    def test_cache_clear_removes_all_entries(self):
        bb = GameStateBlackboard()
        bb.game_time = 0.0
        bb.cache_set("a", 1)
        bb.cache_set("b", 2)

        bb.cache_clear()

        assert bb.cache_get("a") is None
        assert bb.cache_get("b") is None

    def test_per_key_ttl_independence(self):
        """A short-TTL key expiring must not affect a long-TTL key."""
        bb = GameStateBlackboard()
        bb.game_time = 0.0
        bb.cache_set("short", "S", ttl=1.0)
        bb.cache_set("long", "L", ttl=10.0)

        bb.game_time = 3.0  # short expired, long still valid
        assert bb.cache_get("short") is None
        assert bb.cache_get("long") == "L"


# ---------------------------------------------------------------------------
# Decision helpers
# ---------------------------------------------------------------------------


class TestDecisionHelpers:
    def test_should_defend_when_under_attack(self):
        bb = GameStateBlackboard()
        bb.is_under_attack = True
        assert bb.should_defend() is True

    def test_should_defend_when_threat_medium(self):
        bb = GameStateBlackboard()
        bb.threat.level = ThreatLevel.MEDIUM
        assert bb.should_defend() is True

    def test_should_defend_false_when_safe(self):
        bb = GameStateBlackboard()
        bb.threat.level = ThreatLevel.NONE
        bb.is_under_attack = False
        bb.threat.is_rushing = False
        assert bb.should_defend() is False

    def test_can_attack_blocked_in_opening(self):
        bb = GameStateBlackboard()
        bb.game_phase = GamePhase.OPENING
        bb.threat.level = ThreatLevel.NONE
        bb.is_under_attack = False
        assert bb.can_attack() is False

    def test_can_attack_allowed_in_mid_game(self):
        bb = GameStateBlackboard()
        bb.game_phase = GamePhase.MID_GAME
        bb.threat.level = ThreatLevel.LOW
        bb.is_under_attack = False
        assert bb.can_attack() is True

    def test_should_expand_requires_safe_and_funds(self):
        bb = GameStateBlackboard()
        bb.threat.level = ThreatLevel.NONE
        bb.resources.minerals = 350
        bb.resources.supply_used = 30
        bb.resources.supply_cap = 50
        bb.resources.supply_left = 20  # is_supply_blocked == False
        assert bb.should_expand() is True

    def test_should_expand_blocked_when_low_minerals(self):
        bb = GameStateBlackboard()
        bb.threat.level = ThreatLevel.NONE
        bb.resources.minerals = 100
        bb.resources.supply_used = 30
        bb.resources.supply_cap = 50
        bb.resources.supply_left = 20
        assert bb.should_expand() is False

    def test_should_expand_blocked_when_supply_blocked(self):
        bb = GameStateBlackboard()
        bb.threat.level = ThreatLevel.NONE
        bb.resources.minerals = 800
        bb.resources.supply_used = 30
        bb.resources.supply_cap = 30
        bb.resources.supply_left = 0  # is_supply_blocked == True
        assert bb.should_expand() is False
