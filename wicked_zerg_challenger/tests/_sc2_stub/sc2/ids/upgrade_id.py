"""Stub UpgradeId."""


class _UpgradeIdMeta(type):
    _cache: dict = {}

    def __getattr__(cls, name):
        if name not in cls._cache:
            cls._cache[name] = _UpgradeIdValue(name)
        return cls._cache[name]


class _UpgradeIdValue:
    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return f"UpgradeId.{self.name}"

    def __eq__(self, other) -> bool:
        if isinstance(other, _UpgradeIdValue):
            return self.name == other.name
        return False

    def __hash__(self) -> int:
        return hash(("UpgradeId", self.name))


class UpgradeId(metaclass=_UpgradeIdMeta):
    pass
