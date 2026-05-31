"""Looks up suggested fixes for known error signatures."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Pattern


@dataclass
class Suggestion:
    pattern_name: str
    fix: str
    rationale: str = ""


class CodeSuggester:
    """Heuristic registry mapping error patterns to suggested fixes."""

    name = "code_suggester"

    def __init__(self) -> None:
        self._rules: Dict[str, Dict] = {}

    def add_suggestion(
        self,
        pattern_name: str,
        regex: str,
        fix: str,
        rationale: str = "",
        flags: int = 0,
    ) -> None:
        if not pattern_name:
            raise ValueError("pattern_name must be non-empty")
        compiled: Pattern[str] = re.compile(regex, flags)
        self._rules[pattern_name] = {
            "regex": compiled,
            "fix": fix,
            "rationale": rationale,
        }

    def remove_suggestion(self, pattern_name: str) -> bool:
        return self._rules.pop(pattern_name, None) is not None

    def suggest(self, error_message: str) -> List[Suggestion]:
        matches: List[Suggestion] = []
        for name, rule in self._rules.items():
            if rule["regex"].search(error_message):
                matches.append(
                    Suggestion(
                        pattern_name=name,
                        fix=rule["fix"],
                        rationale=rule["rationale"],
                    )
                )
        return matches

    def list_patterns(self) -> List[str]:
        return list(self._rules.keys())
