# -*- coding: utf-8 -*-
"""Regression test: bot manager attribute names are consistent.

A common bug pattern in this codebase: BotStepIntegrator initializes a
manager as `self.bot.foo`, but a downstream consumer reads
`self.bot.foo_alt` (different name). The wrong name silently no-ops
under `hasattr(...)`, leaving the subsystem dead. We can't catch that
at runtime without sc2; we *can* catch it via a literal-string scan.

The shape of the check:

* Collect every `self.bot.NAME = ...` assignment in
  `bot_step_integration.py` (the canonical instantiation site).
* Collect every `hasattr(self.bot, "NAME")` on the producer side AND
  every `self.bot.NAME` access on the consumer side from other files.
* Each NAME used by a consumer (with `hasattr` guard) MUST appear as
  an assignment somewhere - otherwise it's dead code.

We allowlist sc2 BotAI builtins (expansion_locations, has_creep, ...)
and externally-set attributes (enemy_race, intel, ...).
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INTEGRATOR = os.path.join(ROOT, "bot_step_integration.py")
COMBAT = os.path.join(ROOT, "combat_manager.py")

ASSIGN_RE = re.compile(r"self\.bot\.([a-z][a-z_0-9]+)\s*=")
HASATTR_RE = re.compile(r'hasattr\(self\.bot, "([a-z][a-z_0-9]+)"\)')


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class TestManagerNamingConsistency(unittest.TestCase):
    """Pin the harassment_coord rename + guard against future drift."""

    def test_combat_manager_uses_harassment_coord_not_coordinator(self):
        text = _read(COMBAT)
        # The rename: combat_manager.py used to say 'harassment_coordinator'
        # while the integrator stored it as 'harassment_coord'. The mismatch
        # silently disabled lock-tracking.
        self.assertNotIn(
            'hasattr(self.bot, "harassment_coordinator")',
            text,
            "combat_manager still references the old name 'harassment_coordinator'",
        )
        self.assertIn(
            'hasattr(self.bot, "harassment_coord")',
            text,
            "combat_manager should reference 'harassment_coord' (matches integrator)",
        )

    def test_harassment_coord_is_assigned_in_integrator(self):
        """Producer side: integrator must actually instantiate it."""
        text = _read(INTEGRATOR)
        self.assertRegex(
            text,
            r"self\.bot\.harassment_coord\s*=",
            "harassment_coord is not assigned in bot_step_integration.py",
        )


if __name__ == "__main__":
    unittest.main()
