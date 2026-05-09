"""Human-readable formatters for SC2 telemetry and logs."""

from __future__ import annotations

from typing import Tuple

_BYTE_SUFFIXES = ("B", "KB", "MB", "GB", "TB", "PB")


def format_number(value: float, precision: int = 2) -> str:
    """Format ``value`` with thousand-separators and ``precision`` decimals."""
    if precision < 0:
        raise ValueError("precision must be non-negative")
    return f"{value:,.{precision}f}"


def format_percent(value: float, precision: int = 1) -> str:
    """Format a fraction in ``[0, 1]`` (or wider) as a percentage string."""
    return f"{value * 100:.{precision}f}%"


def format_resources(minerals: int, vespene: int, supply: Tuple[int, int]) -> str:
    """Return ``"M=… G=… S=used/cap"`` for a glance at SC2 resource state."""
    used, cap = supply
    if used < 0 or cap < 0:
        raise ValueError("supply values must be non-negative")
    return f"M={minerals} G={vespene} S={used}/{cap}"


def format_supply(used: int, cap: int) -> str:
    """Format an SC2 supply pair as ``used/cap``."""
    if used < 0 or cap < 0:
        raise ValueError("supply values must be non-negative")
    return f"{used}/{cap}"


def format_bytes(num_bytes: float) -> str:
    """Format a byte count using binary (1024-based) suffixes."""
    if num_bytes < 0:
        raise ValueError("num_bytes must be non-negative")
    size = float(num_bytes)
    for suffix in _BYTE_SUFFIXES:
        if size < 1024 or suffix == _BYTE_SUFFIXES[-1]:
            if suffix == "B":
                return f"{int(size)} {suffix}"
            return f"{size:.2f} {suffix}"
        size /= 1024
    return f"{size:.2f} {_BYTE_SUFFIXES[-1]}"
