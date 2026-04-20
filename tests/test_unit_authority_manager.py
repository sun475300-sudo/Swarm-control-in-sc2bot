# -*- coding: utf-8 -*-
"""Unit tests for UnitAuthorityManager."""

import sys
import pytest
sys.path.insert(0, "wicked_zerg_challenger")

from unit_authority_manager import UnitAuthorityManager, AuthorityLevel


class _FakeBot:
    def __init__(self, time=0.0):
        self.time = time
        self.workers = []


class TestAuthorityRequest:
    def setup_method(self):
        self.bot = _FakeBot(time=10.0)
        self.mgr = UnitAuthorityManager(self.bot)

    def test_request_new_unit_succeeds(self):
        assert self.mgr.request_unit(1, "CombatManager", AuthorityLevel.COMBAT)

    def test_requester_has_authority_after_grant(self):
        self.mgr.request_unit(1, "CombatManager", AuthorityLevel.COMBAT)
        assert self.mgr.has_authority(1, "CombatManager")

    def test_lower_priority_cannot_steal(self):
        self.mgr.request_unit(1, "DefenseManager", AuthorityLevel.DEFENSE)
        result = self.mgr.request_unit(1, "EconomyManager", AuthorityLevel.ECONOMY)
        assert not result
        assert self.mgr.has_authority(1, "DefenseManager")

    def test_higher_priority_steals_authority(self):
        self.mgr.request_unit(1, "EconomyManager", AuthorityLevel.ECONOMY)
        result = self.mgr.request_unit(1, "DefenseManager", AuthorityLevel.DEFENSE)
        assert result
        assert self.mgr.has_authority(1, "DefenseManager")
        assert not self.mgr.has_authority(1, "EconomyManager")

    def test_same_requester_refreshes_without_conflict(self):
        self.mgr.request_unit(1, "CombatManager", AuthorityLevel.COMBAT)
        result = self.mgr.request_unit(1, "CombatManager", AuthorityLevel.COMBAT)
        assert result
        assert self.mgr.total_conflicts == 0

    def test_conflict_counter_increments_on_steal(self):
        self.mgr.request_unit(1, "EconomyManager", AuthorityLevel.ECONOMY)
        self.mgr.request_unit(1, "DefenseManager", AuthorityLevel.DEFENSE)
        assert self.mgr.total_conflicts == 1


class TestAuthorityRelease:
    def setup_method(self):
        self.bot = _FakeBot(time=5.0)
        self.mgr = UnitAuthorityManager(self.bot)

    def test_release_by_owner_succeeds(self):
        self.mgr.request_unit(42, "Combat", AuthorityLevel.COMBAT)
        assert self.mgr.release_unit(42, "Combat")
        assert not self.mgr.has_authority(42, "Combat")

    def test_release_by_non_owner_fails(self):
        self.mgr.request_unit(42, "Combat", AuthorityLevel.COMBAT)
        assert not self.mgr.release_unit(42, "Economy")
        assert self.mgr.has_authority(42, "Combat")

    def test_release_non_existent_unit(self):
        assert not self.mgr.release_unit(999, "AnyManager")


class TestWorkerProtection:
    def test_worker_protected_level_higher_than_combat(self):
        assert AuthorityLevel.WORKER_PROTECTED > AuthorityLevel.COMBAT

    def test_worker_protected_higher_than_defense(self):
        assert AuthorityLevel.WORKER_PROTECTED > AuthorityLevel.DEFENSE

    def test_is_worker_protected_false_for_unknown(self):
        bot = _FakeBot()
        mgr = UnitAuthorityManager(bot)
        assert not mgr.is_worker_protected(9999)

    def test_is_worker_protected_true_after_protection(self):
        bot = _FakeBot()
        mgr = UnitAuthorityManager(bot)
        mgr.request_unit(7, "EconomyManager", AuthorityLevel.WORKER_PROTECTED)
        assert mgr.is_worker_protected(7)


class TestRequestAuthority:
    def test_request_authority_returns_granted_set(self):
        bot = _FakeBot()
        mgr = UnitAuthorityManager(bot)
        tags = [1, 2, 3]
        granted = mgr.request_authority(tags, AuthorityLevel.COMBAT, "CombatManager")
        assert set(granted) == {1, 2, 3}

    def test_request_authority_respects_higher_level(self):
        bot = _FakeBot()
        mgr = UnitAuthorityManager(bot)
        mgr.request_unit(5, "DefenseManager", AuthorityLevel.DEFENSE)
        granted = mgr.request_authority([5], AuthorityLevel.COMBAT, "CombatManager")
        # COMBAT (70) < DEFENSE (100), so tag 5 should NOT be granted
        assert 5 not in granted
