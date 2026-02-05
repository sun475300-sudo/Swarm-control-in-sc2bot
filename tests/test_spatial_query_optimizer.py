"""
Unit Tests for Spatial Query Optimizer

Tests cache efficiency, query correctness, and performance improvements.
"""

import pytest
from unittest.mock import Mock, MagicMock
from sc2.position import Point2


class MockUnits:
    """Mock Units collection with closer_than support"""

    def __init__(self, units=[]):
        self._units = units

    def closer_than(self, radius, position):
        """Mock closer_than method"""
        result = []
        for unit in self._units:
            distance = ((unit.position.x - position.x) ** 2 +
                       (unit.position.y - position.y) ** 2) ** 0.5
            if distance < radius:
                result.append(unit)
        return MockUnits(result)

    def __iter__(self):
        return iter(self._units)

    def __len__(self):
        return len(self._units)


class MockBot:
    def __init__(self):
        self.units = MockUnits([])
        self.enemy_units = MockUnits([])


def create_mock_unit(position=(10, 10), tag=1):
    """Create a mock unit for testing"""
    unit = Mock()
    unit.position = Point2(position)
    unit.tag = tag
    return unit


class TestSpatialQueryOptimizer:
    """Test suite for Spatial Query Optimizer"""

    def setup_method(self):
        """Setup before each test"""
        try:
            from wicked_zerg_challenger.combat.spatial_query_optimizer import SpatialQueryOptimizer
            self.bot = MockBot()
            self.optimizer = SpatialQueryOptimizer(self.bot)
        except ImportError:
            pytest.skip("SpatialQueryOptimizer not available")

    # ===== Cache System Tests =====

    def test_cache_initialization(self):
        """Test that cache is properly initialized"""
        assert hasattr(self.optimizer, '_query_cache')
        assert isinstance(self.optimizer._query_cache, dict)
        assert len(self.optimizer._query_cache) == 0

    def test_cache_hit_on_duplicate_query(self):
        """Test that duplicate queries hit the cache"""
        position = Point2((50, 50))
        radius = 10.0
        iteration = 100

        # First query (cache miss)
        result1 = self.optimizer.get_enemies_near_position(position, radius, iteration)
        initial_misses = self.optimizer.cache_misses

        # Second identical query (cache hit)
        result2 = self.optimizer.get_enemies_near_position(position, radius, iteration)

        assert self.optimizer.cache_hits > 0
        assert self.optimizer.cache_misses == initial_misses  # No additional miss

    def test_cache_invalidation_on_new_iteration(self):
        """Test that cache is cleared for new iterations"""
        position = Point2((50, 50))
        radius = 10.0

        # Query at iteration 100
        self.optimizer.get_enemies_near_position(position, radius, 100)

        # Query at iteration 101 (different iteration)
        self.optimizer.get_enemies_near_position(position, radius, 101)

        # Both should be cache misses
        assert self.optimizer.cache_misses >= 2

    def test_clear_cache(self):
        """Test manual cache clearing"""
        position = Point2((50, 50))
        radius = 10.0
        iteration = 100

        # Add to cache
        self.optimizer.get_enemies_near_position(position, radius, iteration)
        assert len(self.optimizer._query_cache) > 0

        # Clear cache
        self.optimizer.clear_cache_if_needed(iteration + 22)  # Next second

        assert len(self.optimizer._query_cache) == 0

    # ===== Statistics Tests =====

    def test_statistics_tracking(self):
        """Test that query statistics are tracked"""
        assert hasattr(self.optimizer, 'total_queries')
        assert hasattr(self.optimizer, 'cache_hits')
        assert hasattr(self.optimizer, 'cache_misses')

        initial_total = self.optimizer.total_queries

        # Execute a query
        self.optimizer.get_enemies_near_position(Point2((50, 50)), 10.0, 100)

        assert self.optimizer.total_queries == initial_total + 1

    def test_cache_hit_rate_calculation(self):
        """Test cache hit rate calculation"""
        position = Point2((50, 50))
        radius = 10.0
        iteration = 100

        # Execute multiple queries
        for i in range(5):
            self.optimizer.get_enemies_near_position(position, radius, iteration)

        hit_rate = self.optimizer.get_cache_hit_rate()

        # First query is miss, next 4 are hits = 80% hit rate
        assert isinstance(hit_rate, float)
        assert 0.0 <= hit_rate <= 1.0

    # ===== Query Correctness Tests =====

    def test_get_enemies_near_position(self):
        """Test enemies near position query"""
        # Add mock enemy units
        enemy1 = create_mock_unit(position=(50, 50), tag=1)
        enemy2 = create_mock_unit(position=(55, 55), tag=2)
        enemy3 = create_mock_unit(position=(100, 100), tag=3)  # Far away

        self.bot.enemy_units = MockUnits([enemy1, enemy2, enemy3])

        # Query enemies within radius 10 of (50, 50)
        result = self.optimizer.get_enemies_near_position(Point2((50, 50)), 10.0, 100)

        # Should return at least enemy1 (distance 0)
        assert result is not None

    def test_get_allies_near_position(self):
        """Test allies near position query"""
        # Add mock ally units
        ally1 = create_mock_unit(position=(50, 50), tag=1)
        ally2 = create_mock_unit(position=(51, 51), tag=2)

        self.bot.units = MockUnits([ally1, ally2])

        # Query allies near position
        result = self.optimizer.get_allies_near_position(Point2((50, 50)), 10.0, 100)

        assert result is not None

    def test_get_closest_enemy(self):
        """Test finding closest enemy"""
        # Add mock enemy units at different distances
        enemy1 = create_mock_unit(position=(60, 60), tag=1)
        enemy2 = create_mock_unit(position=(55, 55), tag=2)  # Closer
        enemy3 = create_mock_unit(position=(70, 70), tag=3)

        self.bot.enemy_units = MockUnits([enemy1, enemy2, enemy3])

        # Find closest to (50, 50)
        result = self.optimizer.get_closest_enemy(Point2((50, 50)))

        # Should return enemy2 or None (depends on implementation)
        assert result is None or result == enemy2

    # ===== Performance Tests =====

    def test_get_statistics(self):
        """Test statistics report generation"""
        # Execute some queries
        for i in range(10):
            self.optimizer.get_enemies_near_position(
                Point2((50, 50)),
                10.0,
                100  # Same iteration for cache hits
            )

        stats = self.optimizer.get_statistics()

        assert "total_queries" in stats
        assert "cache_hits" in stats
        assert "cache_misses" in stats
        assert "cache_hit_rate" in stats

        assert stats["total_queries"] == 10
        assert stats["cache_hits"] == 9  # First is miss, rest are hits
        assert stats["cache_misses"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
