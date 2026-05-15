# -*- coding: utf-8 -*-
"""UnitAuthorityManager 단위 테스트.

권한 요청/해제, 동일 시스템 재요청, 상위 권한 takeover, 만료 청소,
worker protection, 다중 유닛 batch 요청, reset 동작.
"""

import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unit_authority_manager import (
    AuthorityLevel,
    UnitAuthority,
    UnitAuthorityManager,
)


class _StubWorkers:
    def __init__(self, workers):
        self._items = workers

    @property
    def amount(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __bool__(self):
        return bool(self._items)


class _StubWorker:
    def __init__(self, tag, gathering=True):
        self.tag = tag
        self.is_gathering = gathering
        self.is_returning = False


class _StubBot:
    def __init__(self, time=0.0, workers=None):
        self.time = time
        self.workers = _StubWorkers(workers or [])


class TestAuthorityRequest(unittest.TestCase):
    def test_fresh_request_grants_authority(self):
        mgr = UnitAuthorityManager(_StubBot())
        self.assertTrue(mgr.request_unit(1, "A", AuthorityLevel.COMBAT))
        self.assertTrue(mgr.has_authority(1, "A"))

    def test_same_owner_re_request_succeeds(self):
        mgr = UnitAuthorityManager(_StubBot())
        mgr.request_unit(1, "A", AuthorityLevel.COMBAT)
        # 같은 owner 재요청 → 허용 + last_command_time 갱신
        self.assertTrue(mgr.request_unit(1, "A", AuthorityLevel.COMBAT))

    def test_lower_level_request_denied(self):
        mgr = UnitAuthorityManager(_StubBot())
        mgr.request_unit(1, "A", AuthorityLevel.COMBAT)  # level 70
        # ECONOMY=40 < COMBAT=70 → denied
        self.assertFalse(mgr.request_unit(1, "B", AuthorityLevel.ECONOMY))
        self.assertTrue(mgr.has_authority(1, "A"))

    def test_higher_level_request_takes_over(self):
        mgr = UnitAuthorityManager(_StubBot())
        mgr.request_unit(1, "A", AuthorityLevel.ECONOMY)  # 40
        # DEFENSE=100 > ECONOMY=40 → takeover
        self.assertTrue(mgr.request_unit(1, "B", AuthorityLevel.DEFENSE))
        self.assertTrue(mgr.has_authority(1, "B"))
        self.assertFalse(mgr.has_authority(1, "A"))
        self.assertEqual(mgr.total_conflicts, 1)


class TestRelease(unittest.TestCase):
    def test_owner_can_release(self):
        mgr = UnitAuthorityManager(_StubBot())
        mgr.request_unit(1, "A", AuthorityLevel.COMBAT)
        self.assertTrue(mgr.release_unit(1, "A"))
        self.assertFalse(mgr.has_authority(1, "A"))

    def test_non_owner_cannot_release(self):
        mgr = UnitAuthorityManager(_StubBot())
        mgr.request_unit(1, "A", AuthorityLevel.COMBAT)
        self.assertFalse(mgr.release_unit(1, "B"))
        # 권한은 그대로 A
        self.assertTrue(mgr.has_authority(1, "A"))

    def test_release_unknown_unit_returns_false(self):
        mgr = UnitAuthorityManager(_StubBot())
        self.assertFalse(mgr.release_unit(999, "A"))


class TestExpiry(unittest.TestCase):
    def test_cleanup_removes_expired(self):
        bot = _StubBot(time=0.0)
        mgr = UnitAuthorityManager(bot)
        mgr.request_unit(1, "A", AuthorityLevel.COMBAT)
        # AUTHORITY_TIMEOUT=5.0 → 6초 후 만료
        bot.time = 6.0
        mgr._cleanup_expired_authorities()
        self.assertFalse(mgr.has_authority(1, "A"))

    def test_cleanup_keeps_active(self):
        bot = _StubBot(time=0.0)
        mgr = UnitAuthorityManager(bot)
        mgr.request_unit(1, "A", AuthorityLevel.COMBAT)
        bot.time = 3.0  # under timeout
        mgr._cleanup_expired_authorities()
        self.assertTrue(mgr.has_authority(1, "A"))


class TestWorkerProtection(unittest.TestCase):
    def test_protect_economy_workers_registers_protection(self):
        bot = _StubBot(workers=[_StubWorker(1), _StubWorker(2), _StubWorker(3)])
        mgr = UnitAuthorityManager(bot)
        mgr._protect_economy_workers()
        # 최소 보호 수: max(8, 0.6*3=1) = 8, 일꾼 3명 → 3명 모두 등록
        self.assertTrue(mgr.is_worker_protected(1))
        self.assertTrue(mgr.is_worker_protected(2))

    def test_protected_worker_has_economy_owner(self):
        bot = _StubBot(workers=[_StubWorker(1)])
        mgr = UnitAuthorityManager(bot)
        mgr._protect_economy_workers()
        auth = mgr.authorities[1]
        self.assertEqual(auth.owner, "EconomyManager")
        self.assertEqual(auth.level, AuthorityLevel.WORKER_PROTECTED)


class TestBatchAndReset(unittest.TestCase):
    def test_request_authority_batch(self):
        mgr = UnitAuthorityManager(_StubBot())
        granted = mgr.request_authority(
            [1, 2, 3], AuthorityLevel.COMBAT, "A", game_loop=10
        )
        self.assertEqual(granted, {1, 2, 3})

    def test_reset_clears_all(self):
        mgr = UnitAuthorityManager(_StubBot())
        mgr.request_unit(1, "A", AuthorityLevel.COMBAT)
        mgr.request_unit(2, "B", AuthorityLevel.DEFENSE)
        mgr.total_conflicts = 5
        mgr.reset()
        self.assertEqual(mgr.authorities, {})
        self.assertEqual(mgr.total_conflicts, 0)


class TestAuthorityLevelOrdering(unittest.TestCase):
    def test_ordering(self):
        # 단조 감소: WORKER_PROTECTED(125) > DEFENSE(100) > COMBAT(70) > IDLE(10)
        self.assertGreater(AuthorityLevel.WORKER_PROTECTED, AuthorityLevel.DEFENSE)
        self.assertGreater(AuthorityLevel.DEFENSE, AuthorityLevel.COMBAT)
        self.assertGreater(AuthorityLevel.COMBAT, AuthorityLevel.IDLE)


if __name__ == "__main__":
    unittest.main()
