"""
PersonalityModule logic tests.

Covers:
- _get_random_message: missing category / silent mode / category miss
- _get_game_phase: boundary buckets
- get_statistics: shape and clipping
- reset(): clears state
- set_mode: updates mode
- _is_ahead with intel-based and supply-based judgments

No sc2 dependency required — uses lightweight stubs.
"""

import sys
from pathlib import Path

import pytest

_PKG_ROOT = Path(__file__).resolve().parent.parent / "wicked_zerg_challenger"
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

try:
    from personality_module import GamePhase, PersonalityMode, PersonalityModule
except ImportError:
    pytest.skip("personality_module unavailable", allow_module_level=True)


# ---------------------------------------------------------------------------
# Bot stubs
# ---------------------------------------------------------------------------


class _Workers:
    def __init__(self, amount=0):
        self.amount = amount


class _Intel:
    def __init__(self, enemy_army_supply=0):
        self.enemy_army_supply = enemy_army_supply


class _Bot:
    def __init__(
        self,
        time=0.0,
        supply_used=0,
        supply_used_by_enemy=0,
        intel=None,
        workers_amount=0,
    ):
        self.time = time
        self.supply_used = supply_used
        self.supply_used_by_enemy = supply_used_by_enemy
        self.intel = intel
        self.workers = _Workers(workers_amount)


def _make(mode=PersonalityMode.NEUTRAL, **bot_kwargs):
    return PersonalityModule(_Bot(**bot_kwargs), mode=mode)


# ---------------------------------------------------------------------------
# _get_game_phase boundaries
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "t, expected",
    [
        (0, GamePhase.OPENING),
        (299, GamePhase.OPENING),
        (300, GamePhase.EARLY),
        (599, GamePhase.EARLY),
        (600, GamePhase.MID),
        (899, GamePhase.MID),
        (900, GamePhase.LATE),
        (3600, GamePhase.LATE),
    ],
)
def test_game_phase_boundaries(t, expected):
    p = _make()
    assert p._get_game_phase(t) == expected


# ---------------------------------------------------------------------------
# _get_random_message
# ---------------------------------------------------------------------------


def test_random_message_returns_none_for_unknown_category():
    p = _make()
    assert p._get_random_message("does-not-exist") is None


def test_random_message_silent_mode_returns_none():
    p = _make(mode=PersonalityMode.SILENT)
    # SILENT has empty list for every category — must be None.
    assert p._get_random_message("greeting") is None
    assert p._get_random_message("ahead") is None


def test_random_message_polite_mode_returns_string():
    p = _make(mode=PersonalityMode.POLITE)
    msg = p._get_random_message("greeting")
    assert isinstance(msg, str) and msg


# ---------------------------------------------------------------------------
# reset / set_mode
# ---------------------------------------------------------------------------


def test_reset_clears_all_state():
    p = _make()
    p.messages_sent.extend(["a", "b"])
    p.last_message_time = 99.0
    p.game_start_greeted = True
    p.good_game_sent = True
    p.victory_declared = True
    p.taunt_count = 7

    p.reset()

    assert p.messages_sent == []
    assert p.last_message_time == 0
    assert p.game_start_greeted is False
    assert p.good_game_sent is False
    assert p.victory_declared is False
    assert p.taunt_count == 0


def test_set_mode_changes_mode():
    p = _make(mode=PersonalityMode.NEUTRAL)
    p.set_mode(PersonalityMode.COCKY)
    assert p.mode is PersonalityMode.COCKY


# ---------------------------------------------------------------------------
# get_statistics
# ---------------------------------------------------------------------------


def test_get_statistics_default_shape():
    p = _make(mode=PersonalityMode.NEUTRAL)
    stats = p.get_statistics()
    assert stats == {
        "mode": "neutral",
        "messages_sent": 0,
        "taunt_count": 0,
        "recent_messages": [],
    }


def test_get_statistics_recent_messages_clipped_to_last_5():
    p = _make()
    for i in range(8):
        p.messages_sent.append(f"m{i}")
    stats = p.get_statistics()
    assert stats["messages_sent"] == 8
    assert stats["recent_messages"] == ["m3", "m4", "m5", "m6", "m7"]


# ---------------------------------------------------------------------------
# _is_ahead
# ---------------------------------------------------------------------------


def test_is_ahead_intel_army_dominance_returns_true():
    p = _make(supply_used=80, intel=_Intel(enemy_army_supply=20), workers_amount=20)
    # army = 80 - 20 workers = 60; 60 > 20 * 1.3 = 26 -> True
    assert p._is_ahead() is True


def test_is_ahead_no_intel_uses_enemy_supply_when_available():
    p = _make(supply_used=80, supply_used_by_enemy=50)
    # 80 > 50 * 1.3 = 65 -> True
    assert p._is_ahead() is True


def test_is_ahead_no_intel_no_enemy_supply_returns_false():
    p = _make(supply_used=100, supply_used_by_enemy=0)
    assert p._is_ahead() is False


def test_is_ahead_close_supply_returns_false():
    p = _make(supply_used=80, supply_used_by_enemy=70)
    # 80 > 70 * 1.3 = 91 -> False
    assert p._is_ahead() is False
