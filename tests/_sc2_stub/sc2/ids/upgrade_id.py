"""Stub for sc2.ids.upgrade_id (mirrors unit_typeid stub)."""
from __future__ import annotations


class _StubMember:
    __slots__ = ("name",)

    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return f"UpgradeId.{self.name}"

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other) -> bool:
        if isinstance(other, _StubMember):
            return self.name == other.name
        return False

    def __hash__(self) -> int:
        return hash(("UpgradeId", self.name))


class _UpgradeIdMeta(type):
    _cache: dict[str, _StubMember] = {}

    def __getattr__(cls, name: str) -> _StubMember:
        if name.startswith("_"):
            raise AttributeError(name)
        member = cls._cache.get(name)
        if member is None:
            member = _StubMember(name)
            cls._cache[name] = member
        return member


class UpgradeId(metaclass=_UpgradeIdMeta):
    """Dynamic stand-in for sc2.ids.upgrade_id.UpgradeId."""
