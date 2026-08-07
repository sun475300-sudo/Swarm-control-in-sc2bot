"""Tests for wicked_zerg_challenger/utils/frame_cache.py."""
from __future__ import annotations

from wicked_zerg_challenger.utils.frame_cache import FrameCache, cached_per_frame


# ---------------------------------------------------------------------------
# FrameCache primitive
# ---------------------------------------------------------------------------

def test_initial_state():
    fc = FrameCache()
    assert fc.get("anything") is None
    assert fc.has("anything") is False


def test_set_and_get_round_trip():
    fc = FrameCache()
    fc.set("foo", 42)
    assert fc.has("foo") is True
    assert fc.get("foo") == 42


def test_get_returns_default():
    fc = FrameCache()
    assert fc.get("missing", default=99) == 99


def test_clear_empties_cache():
    fc = FrameCache()
    fc.set("a", 1)
    fc.clear()
    assert fc.has("a") is False


def test_clear_if_new_frame_only_clears_on_change():
    fc = FrameCache()
    fc.clear_if_new_frame(10)
    fc.set("a", 1)

    # Same iteration — must NOT clear.
    fc.clear_if_new_frame(10)
    assert fc.has("a") is True

    # Different iteration — clears.
    fc.clear_if_new_frame(11)
    assert fc.has("a") is False


def test_clear_if_new_frame_first_call_clears_baseline():
    fc = FrameCache()
    fc.set("pre_existing", 7)
    fc.clear_if_new_frame(0)  # first frame transition (-1 → 0)
    assert fc.has("pre_existing") is False


# ---------------------------------------------------------------------------
# cached_per_frame decorator
# ---------------------------------------------------------------------------

class _Counter:
    def __init__(self):
        self._frame_cache = FrameCache()
        self.call_count = 0

    @cached_per_frame
    def expensive(self, x):
        self.call_count += 1
        return x * 2


def test_decorator_caches_within_frame():
    c = _Counter()
    c.expensive(3)
    c.expensive(3)
    c.expensive(3)
    assert c.call_count == 1


def test_decorator_separate_args_cache_separately():
    c = _Counter()
    c.expensive(3)
    c.expensive(4)
    assert c.call_count == 2


def test_decorator_recomputes_after_cache_cleared():
    c = _Counter()
    c.expensive(3)
    c._frame_cache.clear_if_new_frame(99)  # new frame
    c.expensive(3)
    assert c.call_count == 2


def test_decorator_no_frame_cache_attribute_falls_back_to_calling():
    """If the instance has no _frame_cache, the decorator should still work
    by always calling the wrapped function."""

    class NoCache:
        def __init__(self):
            self.calls = 0

        @cached_per_frame
        def f(self, x):
            self.calls += 1
            return x

    n = NoCache()
    n.f(1)
    n.f(1)
    assert n.calls == 2


def test_decorator_returns_correct_value():
    c = _Counter()
    assert c.expensive(5) == 10
    # cached call still returns same value
    assert c.expensive(5) == 10
