"""
Frame-based cache decorator inspired by BurnySc2's property_cache_once_per_frame.

Usage:
    class MyManager:
        def __init__(self, bot):
            self.bot = bot
            self._frame_cache = FrameCache()

        def on_step(self, iteration):
            self._frame_cache.clear_if_new_frame(iteration)

        @cached_per_frame
        def expensive_calculation(self):
            ...
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Dict


class FrameCache:
    """Per-frame cache that automatically invalidates when iteration changes."""

    __slots__ = ("_cache", "_last_iteration")

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._last_iteration: int = -1

    def clear_if_new_frame(self, iteration: int) -> None:
        if iteration != self._last_iteration:
            self._cache.clear()
            self._last_iteration = iteration

    def get(self, key: str, default=None):
        return self._cache.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = value

    def has(self, key: str) -> bool:
        return key in self._cache

    def clear(self) -> None:
        self._cache.clear()


def cached_per_frame(func: Callable) -> Callable:
    """
    Decorator that caches method results per game frame.

    Requires the instance to have a `_frame_cache` attribute of type FrameCache.
    The cache key is the function name + args hash.

    Example:
        class Manager:
            def __init__(self):
                self._frame_cache = FrameCache()

            @cached_per_frame
            def get_threats(self):
                return expensive_computation()
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        cache = getattr(self, "_frame_cache", None)
        if cache is None:
            return func(self, *args, **kwargs)

        key = f"{func.__name__}:{hash(args)}"
        if cache.has(key):
            return cache.get(key)

        result = func(self, *args, **kwargs)
        cache.set(key, result)
        return result

    return wrapper
