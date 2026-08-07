"""Match log lines against named regex patterns."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Pattern


@dataclass
class PatternHit:
    pattern_name: str
    text: str
    groups: tuple


class PatternMatcher:
    """Registry of named regex patterns with ``find_all`` lookup."""

    name = "pattern_matcher"

    def __init__(self) -> None:
        self._patterns: Dict[str, Pattern[str]] = {}

    def add_pattern(self, name: str, regex: str, flags: int = 0) -> None:
        if not name:
            raise ValueError("pattern name must be non-empty")
        self._patterns[name] = re.compile(regex, flags)

    def remove_pattern(self, name: str) -> bool:
        return self._patterns.pop(name, None) is not None

    def patterns(self) -> List[str]:
        return list(self._patterns.keys())

    def match_first(self, text: str) -> List[PatternHit]:
        hits: List[PatternHit] = []
        for name, pattern in self._patterns.items():
            m = pattern.search(text)
            if m:
                hits.append(PatternHit(name, text, m.groups()))
        return hits

    def find_all(self, text: str) -> List[PatternHit]:
        hits: List[PatternHit] = []
        for name, pattern in self._patterns.items():
            for m in pattern.finditer(text):
                hits.append(PatternHit(name, m.group(0), m.groups()))
        return hits
