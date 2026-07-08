# -*- coding: utf-8 -*-
import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unit_authority_manager import AuthorityLevel, UnitAuthorityManager


class FakeWorker:
    def __init__(self, tag, is_gathering=True, is_returning=False):
        self.tag = tag
        self.is_gathering = is_gathering
        self.is_returning = is_returning


class FakeWorkers(list):
    @property
    def amount(self):
        return len(self)


class FakeBot:
    def __init__(self, workers=None, time=0.0):
        self.workers = FakeWorkers(workers or [])
        self.time = time


class TestRequestUnit(unittest.TestCase):
    def setUp(self):
        self.manager = UnitAuthorityManager(FakeBot())

    def test_new_unit_grants_authority(self):
        granted = self.manager.request_unit(1, "CombatManager", AuthorityLevel.COMBAT)
        self.assertTrue(granted)
        self.assertTrue(self.manager.has_authority(1, "CombatManager"))
        self.assertIn(1, self.manager.system_units["CombatManager"])

    def test_same_owner_renews_without_conflict(self):
        self.manager.bot.time = 5.0
        self.manager.request_unit(1, "CombatManager", AuthorityLevel.COMBAT)
        self.manager.bot.time = 10.0
        granted = self.manager.request_unit(1, "CombatManager", AuthorityLevel.COMBAT)
        self.assertTrue(granted)
        self.assertEqual(self.manager.total_conflicts, 0)
        self.assertEqual(self.manager.authorities[1].last_command_time, 10.0)

    def test_higher_priority_requester_takes_over(self):
        self.manager.request_unit(1, "EconomyManager", AuthorityLevel.ECONOMY)
        granted = self.manager.request_unit(1, "DefenseSystem", AuthorityLevel.DEFENSE)
        self.assertTrue(granted)
        self.assertTrue(self.manager.has_authority(1, "DefenseSystem"))
        self.assertNotIn(1, self.manager.system_units["EconomyManager"])
        self.assertIn(1, self.manager.system_units["DefenseSystem"])
        self.assertEqual(self.manager.total_conflicts, 1)

    def test_lower_priority_requester_is_denied(self):
        self.manager.request_unit(1, "DefenseSystem", AuthorityLevel.DEFENSE)
        granted = self.manager.request_unit(
            1, "ScoutingSystem", AuthorityLevel.SCOUTING
        )
        self.assertFalse(granted)
        self.assertTrue(self.manager.has_authority(1, "DefenseSystem"))
        self.assertEqual(self.manager.total_conflicts, 0)

    def test_equal_priority_requester_is_denied(self):
        self.manager.request_unit(1, "CombatManager", AuthorityLevel.COMBAT)
        granted = self.manager.request_unit(
            1, "HarassmentCoordinator", AuthorityLevel.COMBAT
        )
        self.assertFalse(granted)
        self.assertTrue(self.manager.has_authority(1, "CombatManager"))


class TestReleaseUnit(unittest.TestCase):
    def setUp(self):
        self.manager = UnitAuthorityManager(FakeBot())

    def test_release_by_owner_succeeds(self):
        self.manager.request_unit(1, "CombatManager", AuthorityLevel.COMBAT)
        released = self.manager.release_unit(1, "CombatManager")
        self.assertTrue(released)
        self.assertFalse(self.manager.has_authority(1, "CombatManager"))
        self.assertNotIn(1, self.manager.system_units["CombatManager"])

    def test_release_by_non_owner_fails(self):
        self.manager.request_unit(1, "CombatManager", AuthorityLevel.COMBAT)
        released = self.manager.release_unit(1, "ScoutingSystem")
        self.assertFalse(released)
        self.assertTrue(self.manager.has_authority(1, "CombatManager"))

    def test_release_unknown_unit_fails(self):
        released = self.manager.release_unit(999, "CombatManager")
        self.assertFalse(released)


class TestWorkerProtection(unittest.TestCase):
    def setUp(self):
        self.manager = UnitAuthorityManager(FakeBot())

    def test_is_worker_protected_true_for_protected_worker(self):
        self.manager.request_unit(1, "EconomyManager", AuthorityLevel.WORKER_PROTECTED)
        self.assertTrue(self.manager.is_worker_protected(1))

    def test_is_worker_protected_false_for_other_owner(self):
        self.manager.request_unit(1, "EconomyManager", AuthorityLevel.WORKER_PROTECTED)
        # Someone else forcibly took it at a lower level via direct authority swap
        self.manager.authorities[1].owner = "CombatManager"
        self.assertFalse(self.manager.is_worker_protected(1))

    def test_is_worker_protected_false_for_untracked_unit(self):
        self.assertFalse(self.manager.is_worker_protected(42))

    def test_protect_economy_workers_registers_gathering_and_returning_workers(self):
        workers = [FakeWorker(i, is_gathering=True) for i in range(10)]
        workers += [FakeWorker(100, is_gathering=False, is_returning=True)]
        manager = UnitAuthorityManager(FakeBot(workers=workers))

        manager._protect_economy_workers()

        protected_tags = [
            tag
            for tag, auth in manager.authorities.items()
            if auth.owner == "EconomyManager"
        ]
        # min_protected = max(8, int(11 * 0.6)) == 8
        self.assertGreaterEqual(len(protected_tags), 8)
        for tag in protected_tags:
            self.assertTrue(manager.is_worker_protected(tag))

    def test_protect_economy_workers_noop_without_workers(self):
        manager = UnitAuthorityManager(FakeBot(workers=[]))
        manager._protect_economy_workers()
        self.assertEqual(len(manager.authorities), 0)


class TestBatchRequestAuthority(unittest.TestCase):
    def setUp(self):
        self.manager = UnitAuthorityManager(FakeBot())

    def test_request_authority_grants_available_units(self):
        granted = self.manager.request_authority(
            [1, 2, 3], AuthorityLevel.COMBAT, "CombatManager"
        )
        self.assertEqual(granted, {1, 2, 3})

    def test_request_authority_skips_higher_priority_units(self):
        self.manager.request_unit(2, "DefenseSystem", AuthorityLevel.DEFENSE)
        granted = self.manager.request_authority(
            [1, 2, 3], AuthorityLevel.SCOUTING, "ScoutingSystem"
        )
        self.assertEqual(granted, {1, 3})


class TestResetAndCleanup(unittest.TestCase):
    def test_reset_clears_all_state(self):
        manager = UnitAuthorityManager(FakeBot())
        manager.request_unit(1, "CombatManager", AuthorityLevel.COMBAT)
        manager.request_unit(1, "DefenseSystem", AuthorityLevel.DEFENSE)

        manager.reset()

        self.assertEqual(manager.authorities, {})
        self.assertEqual(manager.system_units, {})
        self.assertEqual(manager.total_conflicts, 0)

    def test_cleanup_expired_authorities_releases_stale_units(self):
        bot = FakeBot(time=0.0)
        manager = UnitAuthorityManager(bot)
        manager.request_unit(1, "CombatManager", AuthorityLevel.COMBAT)

        bot.time = manager.AUTHORITY_TIMEOUT + 1
        manager._cleanup_expired_authorities()

        self.assertFalse(manager.has_authority(1, "CombatManager"))

    def test_cleanup_expired_authorities_keeps_recent_units(self):
        bot = FakeBot(time=0.0)
        manager = UnitAuthorityManager(bot)
        manager.request_unit(1, "CombatManager", AuthorityLevel.COMBAT)

        bot.time = manager.AUTHORITY_TIMEOUT - 1
        manager._cleanup_expired_authorities()

        self.assertTrue(manager.has_authority(1, "CombatManager"))


class TestOnStep(unittest.TestCase):
    def test_on_step_protects_workers_on_interval(self):
        workers = [FakeWorker(i) for i in range(8)]
        manager = UnitAuthorityManager(FakeBot(workers=workers))

        import asyncio

        asyncio.run(manager.on_step(22))

        self.assertGreater(len(manager.authorities), 0)

    def test_on_step_skips_protection_off_interval(self):
        workers = [FakeWorker(i) for i in range(8)]
        manager = UnitAuthorityManager(FakeBot(workers=workers))

        import asyncio

        asyncio.run(manager.on_step(1))

        self.assertEqual(len(manager.authorities), 0)


if __name__ == "__main__":
    unittest.main()
