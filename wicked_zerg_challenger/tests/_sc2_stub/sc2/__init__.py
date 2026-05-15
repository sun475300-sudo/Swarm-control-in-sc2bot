"""Test-only stub for the burnysc2 package.

Lets the test suite collect when burnysc2 (and its mpyq build dependency)
cannot be installed in the local environment. Production code paths that
guard ``try: from sc2... except ImportError`` are unaffected because the
stub is only injected via the wicked_zerg_challenger tests conftest.
"""
