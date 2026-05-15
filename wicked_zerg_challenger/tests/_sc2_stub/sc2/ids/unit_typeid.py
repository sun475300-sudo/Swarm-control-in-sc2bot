"""Stub UnitTypeId — returns a unique string identifier for any attribute access."""


class _UnitTypeIdMeta(type):
    """Metaclass that produces sentinel values for any attribute name."""

    _cache: dict = {}

    def __getattr__(cls, name):
        if name not in cls._cache:
            cls._cache[name] = _UnitTypeIdValue(name)
        return cls._cache[name]


class _UnitTypeIdValue:
    """Stand-in for a UnitTypeId enum member."""

    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return f"UnitTypeId.{self.name}"

    def __eq__(self, other) -> bool:
        if isinstance(other, _UnitTypeIdValue):
            return self.name == other.name
        return False

    def __hash__(self) -> int:
        return hash(("UnitTypeId", self.name))


class UnitTypeId(metaclass=_UnitTypeIdMeta):
    pass
