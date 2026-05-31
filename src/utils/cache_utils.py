"""Small in-memory caching helpers."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Hashable


class LRUCache:
    """Bounded least-recently-used cache.

    Keys are inserted to the back on write; ``get`` moves a key to the back so
    that the front always contains the least-recently-used item to evict next.
    """

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._capacity = int(capacity)
        self._store: "OrderedDict[Hashable, Any]" = OrderedDict()

    @property
    def capacity(self) -> int:
        return self._capacity

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: Hashable) -> bool:
        return key in self._store

    def get(self, key: Hashable, default: Any = None) -> Any:
        if key not in self._store:
            return default
        self._store.move_to_end(key)
        return self._store[key]

    def put(self, key: Hashable, value: Any) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = value
        if len(self._store) > self._capacity:
            self._store.popitem(last=False)

    def clear(self) -> None:
        self._store.clear()

    def keys(self):
        return list(self._store.keys())
