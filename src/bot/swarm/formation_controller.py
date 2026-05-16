"""Minimal formation controller used by swarm behavior modules.

The controller is intentionally lightweight: it accepts a list of unit
positions, performs basic validation, and returns the maintained formation
positions (as a list of `(x, y)` pairs). Behavior modules can override
`maintain_formation` to inject custom logic.

Positions are accepted in any of the following shapes:

* `(x, y)` 2-tuples or lists
* objects with `.x` / `.y` attributes (e.g. a `Point2` from `burnysc2`)

The returned value is always a list of `(float, float)` tuples so consumers
do not need to special-case the input format.
"""

from __future__ import annotations

from typing import Any, Iterable, List, Tuple

Position = Tuple[float, float]


def _coerce(point: Any) -> Position:
    if isinstance(point, (tuple, list)) and len(point) >= 2:
        return float(point[0]), float(point[1])
    x = getattr(point, "x", None)
    y = getattr(point, "y", None)
    if x is None or y is None:
        raise TypeError(f"Unsupported position object: {point!r}")
    return float(x), float(y)


class FormationController:
    """Maintain a swarm formation around its current center of mass."""

    def __init__(self, target_spacing: float = 1.5) -> None:
        self.target_spacing = float(target_spacing)

    def maintain_formation(self, positions: Iterable[Any]) -> List[Position]:
        """Return the formation positions for the given units.

        The default implementation simply normalises the input to a list of
        `(x, y)` tuples — behavior modules can override the method or wrap
        the result to apply specific tactics.
        """
        return [_coerce(p) for p in positions]

    def center_of_mass(self, positions: Iterable[Any]) -> Position:
        coerced = [_coerce(p) for p in positions]
        if not coerced:
            return (0.0, 0.0)
        cx = sum(x for x, _ in coerced) / len(coerced)
        cy = sum(y for _, y in coerced) / len(coerced)
        return (cx, cy)

    def __repr__(self) -> str:  # pragma: no cover - trivial repr
        return f"{type(self).__name__}(target_spacing={self.target_spacing})"
