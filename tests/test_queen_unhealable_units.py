"""
Regression tests for QueenManager._build_unhealable_units().

Transfusing self-destructing or auto-expiring units is a strict waste of
queen energy. This file pins the membership of UNHEALABLE_UNITS so a
future refactor can't silently drop e.g. CHANGELING and start
transfusing 150-second spy units.

This test file does NOT depend on the optional `sc2` library: it uses
the same UnitTypeId reference that queen_manager.py resolves at import
time (real sc2 if installed, or the in-module stub if not).
"""

import pytest


class TestQueenManagerUnhealableUnits:
    def setup_method(self):
        try:
            from wicked_zerg_challenger import queen_manager as qm
        except ImportError:
            pytest.skip("queen_manager not importable")
            return
        self.QueenManager = qm.QueenManager
        self.UnitTypeId = qm.UnitTypeId

    def test_returns_a_set(self):
        unhealable = self.QueenManager._build_unhealable_units()
        assert isinstance(unhealable, set)

    def test_baneling_is_unhealable_when_available(self):
        """Baneling self-destructs on attack -> never transfuse."""
        unhealable = self.QueenManager._build_unhealable_units()
        baneling = getattr(self.UnitTypeId, "BANELING", None)
        if baneling is None:
            pytest.skip("UnitTypeId.BANELING not available")
        assert baneling in unhealable

    def test_broodling_is_unhealable_when_available(self):
        """Broodlord-spawned broodlings expire ~12s -> never transfuse."""
        unhealable = self.QueenManager._build_unhealable_units()
        broodling = getattr(self.UnitTypeId, "BROODLING", None)
        if broodling is None:
            pytest.skip("UnitTypeId.BROODLING not available")
        assert broodling in unhealable

    def test_changelings_are_unhealable_when_available(self):
        """Overseer changelings auto-expire ~150s -> never transfuse."""
        unhealable = self.QueenManager._build_unhealable_units()
        any_known = False
        for name in (
            "CHANGELING",
            "CHANGELINGZERGLING",
            "CHANGELINGZERGLINGWINGS",
            "CHANGELINGMARINE",
            "CHANGELINGMARINESHIELD",
            "CHANGELINGZEALOT",
        ):
            t = getattr(self.UnitTypeId, name, None)
            if t is not None:
                any_known = True
                assert t in unhealable, f"{name} should be unhealable"
        if not any_known:
            pytest.skip("No CHANGELING variants available")

    def test_locust_is_unhealable_when_available(self):
        """Swarm-host locusts auto-expire after ~18s -> never transfuse."""
        unhealable = self.QueenManager._build_unhealable_units()
        any_known = False
        for name in ("LOCUSTMP", "LOCUSTMPFLYING"):
            t = getattr(self.UnitTypeId, name, None)
            if t is not None:
                any_known = True
                assert t in unhealable
        if not any_known:
            pytest.skip("No LOCUSTMP variants available")

    def test_normal_units_are_healable(self):
        """Sanity: high-value army units must NOT be in the unhealable set."""
        unhealable = self.QueenManager._build_unhealable_units()
        for name in ("ULTRALISK", "BROODLORD", "ROACH", "HYDRALISK", "QUEEN"):
            t = getattr(self.UnitTypeId, name, None)
            if t is not None:
                assert t not in unhealable, f"{name} must be healable"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
