"""Minimal Units stub providing list-like behaviour."""


class Units(list):
    """Behaves like a list with a couple of python-sc2 helpers."""

    def __init__(self, units=None, bot_object=None):
        super().__init__(units or [])
        self._bot_object = bot_object

    @property
    def amount(self):
        return len(self)

    @property
    def exists(self):
        return len(self) > 0

    @property
    def first(self):
        return self[0] if self else None

    def closer_than(self, distance, position):
        result = []
        for unit in self:
            try:
                if unit.distance_to(position) < distance:
                    result.append(unit)
            except Exception:
                continue
        return Units(result, self._bot_object)

    def further_than(self, distance, position):
        result = []
        for unit in self:
            try:
                if unit.distance_to(position) >= distance:
                    result.append(unit)
            except Exception:
                continue
        return Units(result, self._bot_object)

    def filter(self, fn):
        return Units([u for u in self if fn(u)], self._bot_object)

    def of_type(self, type_id):
        return Units(
            [u for u in self if getattr(u, "type_id", None) == type_id],
            self._bot_object,
        )

    def ready(self):
        return Units(
            [u for u in self if getattr(u, "is_ready", True)], self._bot_object
        )
