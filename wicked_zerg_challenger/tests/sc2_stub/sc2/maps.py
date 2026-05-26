"""Minimal maps module stub."""


def get(name):
    """Return a placeholder map object."""
    return _StubMap(name)


class _StubMap:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"<StubMap {self.name}>"
