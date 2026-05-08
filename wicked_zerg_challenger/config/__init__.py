"""Configuration package for wicked_zerg_challenger.

Existing call sites import via the top-level alias `from config.X import …`,
which works because `wicked_zerg_challenger/` is added to ``sys.path`` at
runtime. Adding this empty package marker also makes the directory importable
as ``wicked_zerg_challenger.config`` for static analysis tools (mypy, pyright)
that walk the source tree and would otherwise see the modules under two
different names.
"""
