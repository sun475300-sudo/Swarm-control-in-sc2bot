"""Time helpers, including SC2-specific gameloop conversions.

StarCraft II runs at 22.4 game-loops per second on "faster" speed (the
ladder default), so ``gameloop_to_seconds`` and ``seconds_to_gameloop``
use that rate by default.
"""

from __future__ import annotations

from typing import Tuple

GAMELOOPS_PER_SECOND = 22.4


def gameloop_to_seconds(loops: int, rate: float = GAMELOOPS_PER_SECOND) -> float:
    """Convert SC2 game-loops to seconds at ``rate`` loops/sec."""
    if rate <= 0:
        raise ValueError("rate must be positive")
    return loops / rate


def seconds_to_gameloop(seconds: float, rate: float = GAMELOOPS_PER_SECOND) -> int:
    """Convert seconds to SC2 game-loops, rounded down."""
    if rate <= 0:
        raise ValueError("rate must be positive")
    return int(seconds * rate)


def format_duration(seconds: float) -> str:
    """Format a non-negative duration as ``MM:SS`` or ``HH:MM:SS``."""
    if seconds < 0:
        raise ValueError("seconds must be non-negative")
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def parse_duration(text: str) -> int:
    """Parse ``MM:SS`` or ``HH:MM:SS`` into total seconds."""
    parts = text.strip().split(":")
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + int(s)
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + int(s)
    raise ValueError(f"unrecognized duration: {text!r}")


def split_hms(seconds: float) -> Tuple[int, int, int]:
    """Split a duration into ``(hours, minutes, seconds)``."""
    if seconds < 0:
        raise ValueError("seconds must be non-negative")
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return hours, minutes, secs
