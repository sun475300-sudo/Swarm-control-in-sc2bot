"""
Unit Tests for Resource Manager

Tests the thread-safe resource reservation system.
"""

import pytest
import asyncio
from unittest.mock import Mock


class MockBot:
    def __init__(self, minerals=1000, vespene=500):
        self.minerals = minerals
        self.vespene = vespene


class TestResourceManager:
    """Test suite for Resource Manager"""

    def setup_method(self):
        """Setup before each test"""
        try:
            from wicked_zerg_challenger.core.resource_manager import ResourceManager
            self.bot = MockBot()
            self.manager = ResourceManager(self.bot)
        except ImportError:
            pytest.skip("ResourceManager not available")

    @pytest.mark.asyncio
    async def test_successful_reservation(self):
        """Test successful resource reservation"""
        result = await self.manager.try_reserve(200, 100, "TestManager")

        assert result == True
        assert self.manager._reserved_minerals == 200
        assert self.manager._reserved_gas == 100

    @pytest.mark.asyncio
    async def test_insufficient_resources(self):
        """Test reservation fails with insufficient resources"""
        # Try to reserve more than available
        result = await self.manager.try_reserve(2000, 100, "TestManager")

        assert result == False
        assert self.manager._reserved_minerals == 0
        assert self.manager._reserved_gas == 0

    @pytest.mark.asyncio
    async def test_release_reservation(self):
        """Test resource release"""
        await self.manager.try_reserve(200, 100, "TestManager")
        await self.manager.release("TestManager")

        assert self.manager._reserved_minerals == 0
        assert self.manager._reserved_gas == 0
        assert "TestManager" not in self.manager._reservations

    @pytest.mark.asyncio
    async def test_multiple_managers(self):
        """Test multiple managers reserving simultaneously"""
        result1 = await self.manager.try_reserve(300, 100, "Manager1")
        result2 = await self.manager.try_reserve(300, 100, "Manager2")

        assert result1 == True
        assert result2 == True  # Should succeed (1000 - 300 - 300 = 400 left)
        assert self.manager._reserved_minerals == 600
        assert self.manager._reserved_gas == 200

    @pytest.mark.asyncio
    async def test_manager_replacement(self):
        """Test that manager can replace its own reservation"""
        await self.manager.try_reserve(200, 100, "TestManager")
        await self.manager.try_reserve(300, 150, "TestManager")

        # Should have new reservation, not both
        assert self.manager._reserved_minerals == 300
        assert self.manager._reserved_gas == 150

    @pytest.mark.asyncio
    async def test_get_available_resources(self):
        """Test getting available resources"""
        await self.manager.try_reserve(200, 100, "TestManager")

        available_m, available_g = self.manager.get_available_resources()

        assert available_m == 800  # 1000 - 200
        assert available_g == 400  # 500 - 100

    @pytest.mark.asyncio
    async def test_partial_release(self):
        """Test partial resource release"""
        await self.manager.try_reserve(400, 200, "TestManager")
        await self.manager.release_partial("TestManager", 200, 100)

        # Should have 200M/100G left reserved
        assert self.manager._reserved_minerals == 200
        assert self.manager._reserved_gas == 100

    @pytest.mark.asyncio
    async def test_statistics(self):
        """Test statistics tracking"""
        await self.manager.try_reserve(200, 100, "Manager1")
        await self.manager.try_reserve(300, 150, "Manager2")
        await self.manager.release("Manager1")

        stats = self.manager.get_statistics()

        assert stats["total_reservations"] == 2
        assert stats["total_releases"] == 1
        assert stats["active_reservations"] == 1

    @pytest.mark.asyncio
    async def test_concurrent_reservations(self):
        """Test concurrent reservation requests"""
        # Create multiple managers trying to reserve simultaneously
        tasks = [
            self.manager.try_reserve(200, 50, f"Manager{i}")
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed (total = 1000M, need 1000M)
        success_count = sum(1 for r in results if r)
        assert success_count == 5

    @pytest.mark.asyncio
    async def test_race_condition_prevention(self):
        """Test that race conditions are prevented"""
        self.bot.minerals = 500  # Only 500 minerals

        # Two managers trying to reserve 300 each
        task1 = self.manager.try_reserve(300, 0, "Manager1")
        task2 = self.manager.try_reserve(300, 0, "Manager2")

        result1, result2 = await asyncio.gather(task1, task2)

        # Only one should succeed (500 < 600)
        assert (result1 and not result2) or (result2 and not result1)
        # Should not over-reserve
        assert self.manager._reserved_minerals <= 500

    # ===== 추가 회귀 테스트: release_partial =====

    @pytest.mark.asyncio
    async def test_release_partial_reduces_reservation(self):
        """release_partial 이 일부만 해제하고 잔여분은 유지"""
        await self.manager.try_reserve(300, 150, "ManagerA")
        await self.manager.release_partial("ManagerA", 100, 50)
        # 200/100 잔여
        rem = self.manager.get_manager_reservation("ManagerA")
        assert rem == (200, 100)
        assert self.manager._reserved_minerals == 200
        assert self.manager._reserved_gas == 100

    @pytest.mark.asyncio
    async def test_release_partial_clamps_at_zero(self):
        """요청량이 잔여보다 크면 0으로 클램프 + 예약 삭제"""
        await self.manager.try_reserve(100, 50, "ManagerB")
        await self.manager.release_partial("ManagerB", 999, 999)
        # 모두 해제 → 예약 사라짐
        assert self.manager.get_manager_reservation("ManagerB") is None
        assert self.manager._reserved_minerals == 0
        assert self.manager._reserved_gas == 0

    @pytest.mark.asyncio
    async def test_release_partial_unknown_manager_noop(self):
        """등록되지 않은 매니저 호출은 noop (에러 없음)"""
        # 호출해도 예외 안 나야 함
        await self.manager.release_partial("Ghost", 100, 100)
        assert self.manager._reserved_minerals == 0

    # ===== get_reserved_resources / get_manager_reservation / has_reservation =====

    @pytest.mark.asyncio
    async def test_get_reserved_resources_tuple(self):
        """get_reserved_resources 가 (minerals, gas) 튜플 반환"""
        await self.manager.try_reserve(123, 45, "M1")
        m, g = self.manager.get_reserved_resources()
        assert m == 123
        assert g == 45

    @pytest.mark.asyncio
    async def test_get_manager_reservation_unknown_returns_none(self):
        """등록되지 않은 매니저 → None"""
        assert self.manager.get_manager_reservation("nope") is None

    @pytest.mark.asyncio
    async def test_has_reservation_true_after_reserve(self):
        """예약 후 has_reservation True"""
        await self.manager.try_reserve(50, 25, "X")
        assert self.manager.has_reservation("X") is True
        await self.manager.release("X")
        assert self.manager.has_reservation("X") is False

    # ===== get_statistics 구조 검증 =====

    @pytest.mark.asyncio
    async def test_statistics_includes_active_count_and_success_rate(self):
        """get_statistics 가 active_reservations / success_rate 포함"""
        await self.manager.try_reserve(100, 50, "S1")
        await self.manager.try_reserve(100, 50, "S2")
        stats = self.manager.get_statistics()
        assert stats["active_reservations"] == 2
        assert "success_rate" in stats
        assert 0.0 <= stats["success_rate"] <= 1.0

    @pytest.mark.asyncio
    async def test_statistics_failed_increments_on_overdraft(self):
        """자원 부족 시 failed_reservations 증가"""
        # 1000/500 만 있는데 더 큰 예약 시도 → 실패
        ok = await self.manager.try_reserve(99999, 99999, "Big")
        assert ok is False
        stats = self.manager.get_statistics()
        assert stats["failed_reservations"] >= 1

    # ===== clear_stale_reservations =====

    @pytest.mark.asyncio
    async def test_clear_stale_reservations_releases_old(self):
        """오랫동안 유지된 예약은 stale_threshold 후 자동 해제"""
        await self.manager.try_reserve(100, 50, "Stale")
        # iteration=0 시점 등록 후, iteration=300 (>220 stale_threshold)에서 정리
        await self.manager.clear_stale_reservations(0)
        # 첫 호출은 단순히 시간 등록만 함
        assert self.manager.has_reservation("Stale") is True

        await self.manager.clear_stale_reservations(500)
        # 500 - 0 = 500 > 220 → stale 처리됨
        assert self.manager.has_reservation("Stale") is False
        assert self.manager._reserved_minerals == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
