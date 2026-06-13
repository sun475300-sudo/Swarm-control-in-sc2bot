"""Lightweight validators for boundary checks and config sanitisation."""

from __future__ import annotations

import math
from numbers import Real
from typing import Any, Iterable, Sequence, Type, TypeVar, Union

T = TypeVar("T")


def is_in_range(
    value: float, low: float, high: float, *, inclusive: bool = True
) -> bool:
    """Return ``True`` when ``low <= value <= high`` (or strict variant)."""
    if low > high:
        raise ValueError("low must not exceed high")
    if inclusive:
        return low <= value <= high
    return low < value < high


def is_finite_number(value: Any) -> bool:
    """Return ``True`` if ``value`` is a finite real number."""
    return isinstance(value, Real) and math.isfinite(float(value))


def is_non_empty(value: Any) -> bool:
    """Return ``True`` for sized values that contain at least one element."""
    try:
        return len(value) > 0
    except TypeError:
        return False


def ensure_type(
    value: Any, expected: Union[Type[T], tuple], *, name: str = "value"
) -> T:
    """Raise ``TypeError`` if ``value`` is not of ``expected`` type."""
    if not isinstance(value, expected):
        raise TypeError(f"{name} must be {expected!r}, got {type(value).__name__}")
    return value


def ensure_in_range(
    value: float, low: float, high: float, *, name: str = "value"
) -> float:
    """Raise ``ValueError`` unless ``value`` is in ``[low, high]``."""
    if not is_in_range(value, low, high):
        raise ValueError(f"{name}={value} out of range [{low}, {high}]")
    return value


def all_unique(items: Iterable[Any]) -> bool:
    """Return ``True`` when ``items`` contains no duplicates (hashable only)."""
    items_list = list(items)
    return len(items_list) == len(set(items_list))


def has_keys(mapping: dict, required: Sequence[str]) -> bool:
    """Return ``True`` when every key in ``required`` is present in ``mapping``."""
    return all(k in mapping for k in required)
