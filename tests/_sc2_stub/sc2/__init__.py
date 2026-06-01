"""Minimal sc2 stub for offline test collection.

This package satisfies `from sc2.*` imports in the test suite when the real
python-sc2 (or burnysc2) library cannot be installed in CI.

It is loaded by `tests/conftest.py` only when a real sc2 module is absent.
"""
