# -*- coding: utf-8 -*-
"""
Regression guard for ROADMAP.md Sprint 7 Task 7.3: raw iteration-frequency
magic numbers (11, 22, 33, 44, 66, 88, 110, 220, 330, 660, 990, 1320 —
exact multiples of GameFrequencies.GAME_FPS) must go through
utils.game_constants.GameFrequencies instead of being repeated as literals.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# These are exactly the values GameFrequencies defines as named "every N
# seconds" constants. A raw `iteration % <value>` outside game_constants.py
# itself means a future edit reintroduced an undocumented magic number.
RAW_FREQUENCY_VALUES = {11, 22, 33, 44, 66, 88, 110, 220, 330, 660, 990, 1320}

# `iteration % <value>` where <value> is a bare int literal (not
# GameFrequencies.SOMETHING and not part of a larger identifier/number).
RAW_ITERATION_PATTERN = re.compile(r"\biteration\s*%\s*(\d+)\b")

CHECKED_FILES = [
    "combat_manager.py",
    "strategy_manager.py",
]


class TestNoRawIterationMagicNumbers(unittest.TestCase):
    def test_checked_manager_files_use_game_frequencies_constants(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        offenders = []

        for filename in CHECKED_FILES:
            path = os.path.join(base_dir, filename)
            with open(path, encoding="utf-8") as f:
                for lineno, line in enumerate(f, start=1):
                    for match in RAW_ITERATION_PATTERN.finditer(line):
                        value = int(match.group(1))
                        if value in RAW_FREQUENCY_VALUES:
                            offenders.append(f"{filename}:{lineno}: {line.strip()}")

        self.assertEqual(
            offenders,
            [],
            "Found raw iteration-frequency magic numbers that should use "
            "GameFrequencies instead:\n" + "\n".join(offenders),
        )

    def test_checked_files_import_game_frequencies(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        for filename in CHECKED_FILES:
            path = os.path.join(base_dir, filename)
            with open(path, encoding="utf-8") as f:
                content = f.read()
            self.assertIn(
                "GameFrequencies",
                content,
                f"{filename} no longer references GameFrequencies — "
                "did the import get removed?",
            )


if __name__ == "__main__":
    unittest.main()
