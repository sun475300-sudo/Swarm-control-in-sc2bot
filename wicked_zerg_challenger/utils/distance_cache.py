# -*- coding: utf-8 -*-
"""Per-frame distance calculation cache."""

from typing import Any, Dict, Tuple


class DistanceCache:
    """Caches position distances for the current game frame."""

    def __init__(self):
        self._cache: Dict[Tuple[float, float, float, float], float] = {}
        self._frame: int = -1
        self._hits: int = 0
        self._misses: int = 0

    def get(self, pos_a: Any, pos_b: Any, current_frame: int) -> float:
        if current_frame != self._frame:
            self._cache.clear()
            self._frame = current_frame
            self._hits = 0
            self._misses = 0

        a = getattr(pos_a, "position", pos_a)
        b = getattr(pos_b, "position", pos_b)
        key = self._key(a, b)
        if key not in self._cache:
            self._cache[key] = a.distance_to(b)
            self._misses += 1
        else:
            self._hits += 1
        return self._cache[key]

    @staticmethod
    def _key(pos_a: Any, pos_b: Any) -> Tuple[float, float, float, float]:
        ax, ay = round(float(pos_a.x), 1), round(float(pos_a.y), 1)
        bx, by = round(float(pos_b.x), 1), round(float(pos_b.y), 1)
        if (bx, by) < (ax, ay):
            ax, ay, bx, by = bx, by, ax, ay
        return ax, ay, bx, by

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total else 0.0


_global_cache = DistanceCache()


def cached_distance(pos_a: Any, pos_b: Any, frame: int) -> float:
    """Use a process-local distance cache for one-off callers."""
    return _global_cache.get(pos_a, pos_b, frame)
