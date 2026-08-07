"""Iterable helpers used by analytics and replay processing."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Callable, Dict, Iterable, Iterator, List, TypeVar

T = TypeVar("T")
K = TypeVar("K")


def chunked(items: Iterable[T], size: int) -> Iterator[List[T]]:
    """Yield successive ``size``-element chunks from ``items``."""
    if size <= 0:
        raise ValueError("size must be positive")
    bucket: List[T] = []
    for item in items:
        bucket.append(item)
        if len(bucket) == size:
            yield bucket
            bucket = []
    if bucket:
        yield bucket


def flatten(items: Iterable[Iterable[T]]) -> List[T]:
    """Flatten one level of nested iterables into a list."""
    return [x for sub in items for x in sub]


def unique(items: Iterable[T]) -> List[T]:
    """Return unique items preserving original order (hashable only)."""
    seen: set = set()
    out: List[T] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def group_by(items: Iterable[T], key: Callable[[T], K]) -> Dict[K, List[T]]:
    """Group ``items`` into a dict keyed by ``key(item)``."""
    out: "OrderedDict[K, List[T]]" = OrderedDict()
    for item in items:
        out.setdefault(key(item), []).append(item)
    return dict(out)


def take(items: Iterable[T], n: int) -> List[T]:
    """Return at most the first ``n`` items as a list."""
    if n < 0:
        raise ValueError("n must be non-negative")
    out: List[T] = []
    iterator = iter(items)
    for _ in range(n):
        try:
            out.append(next(iterator))
        except StopIteration:
            break
    return out


def deep_get(mapping: dict, path: Iterable[str], default: Any = None) -> Any:
    """Walk a dotted path through nested dicts, returning ``default`` on miss."""
    current: Any = mapping
    for key in path:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current
