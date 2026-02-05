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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
