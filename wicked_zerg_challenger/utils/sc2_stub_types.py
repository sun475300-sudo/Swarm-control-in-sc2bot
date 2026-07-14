"""
Shared fallback stand-ins for `sc2` SDK enum types.

Several modules define `UnitTypeId`/`AbilityId`/`UpgradeId` classes as an
`except ImportError` fallback so they can still be imported (and unit
tested) in environments where the `sc2` package isn't installed. Those
hand-rolled stubs only defined the handful of members each module happened
to need, so any test referencing a member outside that hand-picked set
raised `AttributeError` at runtime instead of degrading gracefully.

`_AutoEnumMeta` makes any attribute access on the class return the
attribute's own name (mirroring how the real `sc2` IDs stringify), so a
fallback stub built on it behaves like an open-ended enum instead of a
fixed allowlist. This only matters when `sc2` is unavailable (i.e. outside
production, where the real SDK types are always used instead).
"""


class _AutoEnumMeta(type):
    def __getattr__(cls, name):
        return name


class AutoEnumStub(metaclass=_AutoEnumMeta):
    """Base class for open-ended `sc2` ID fallback stubs."""
