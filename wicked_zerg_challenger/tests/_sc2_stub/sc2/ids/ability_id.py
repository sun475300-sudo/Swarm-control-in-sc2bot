"""Stub AbilityId."""


class _AbilityIdMeta(type):
    _cache: dict = {}

    def __getattr__(cls, name):
        if name not in cls._cache:
            cls._cache[name] = _AbilityIdValue(name)
        return cls._cache[name]


class _AbilityIdValue:
    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return f"AbilityId.{self.name}"

    def __eq__(self, other) -> bool:
        if isinstance(other, _AbilityIdValue):
            return self.name == other.name
        return False

    def __hash__(self) -> int:
        return hash(("AbilityId", self.name))


class AbilityId(metaclass=_AbilityIdMeta):
    pass
