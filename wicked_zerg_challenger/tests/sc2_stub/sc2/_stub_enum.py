"""Shared stub enum used to mimic python-sc2's enum members.

Each access returns a stable sentinel that compares equal across access
and has a `name` and `value` attribute, similar to the real enum members.
"""


class _StubId:
    """Sentinel value used for fallback enum members."""

    __slots__ = ("name", "value")

    def __init__(self, name):
        self.name = name
        self.value = name

    def __repr__(self):
        return f"<StubId {self.name}>"

    def __hash__(self):
        return hash(("_StubId", self.name))

    def __eq__(self, other):
        return isinstance(other, _StubId) and self.name == other.name

    def __ne__(self, other):
        return not self.__eq__(other)

    def __bool__(self):
        return True


class _StubEnum:
    """Auto-vivifying attribute container."""

    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        value = _StubId(name)
        object.__setattr__(self, name, value)
        return value

    def __call__(self, name):
        return _StubId(str(name))

    def __iter__(self):
        return iter([])
