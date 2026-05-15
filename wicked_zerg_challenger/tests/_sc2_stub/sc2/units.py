"""Stub Units collection."""


class Units(list):
    """Mimics sc2.units.Units enough for tests in the local fallback path."""

    def __init__(self, units=None, bot_object_or_proto=None):
        super().__init__(list(units or []))
        self._bot = bot_object_or_proto

    @property
    def exists(self) -> bool:
        return len(self) > 0

    @property
    def amount(self) -> int:
        return len(self)

    @property
    def empty(self) -> bool:
        return len(self) == 0

    @property
    def ready(self) -> "Units":
        return Units(u for u in self if getattr(u, "is_ready", True))

    @property
    def idle(self) -> "Units":
        return Units(u for u in self if getattr(u, "is_idle", False))

    @property
    def first(self):
        return self[0] if self else None

    def closer_than(self, distance, position) -> "Units":
        return Units(
            u for u in self if getattr(u, "distance_to", lambda _o: 0)(position) < distance
        )

    def filter(self, predicate) -> "Units":
        return Units(u for u in self if predicate(u))

    def of_type(self, types) -> "Units":
        if not isinstance(types, (list, set, tuple)):
            types = {types}
        return Units(u for u in self if getattr(u, "type_id", None) in types)

    def closest_to(self, position):
        if not self:
            return None
        return min(self, key=lambda u: getattr(u, "distance_to", lambda _o: 0)(position))
