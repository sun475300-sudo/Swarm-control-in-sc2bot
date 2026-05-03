#!/usr/bin/env python3
"""Regression guard: fail if any empty logger.<level>() calls re-appear.

Background:
    Commit 2e03d2f removed 131 empty `logger.info() / logger.debug() / ...`
    calls that were left behind by the print->logger migration. This script
    is the cheap CI-friendly tripwire that prevents that same bug class
    from recurring.

Usage:
    python scripts/check_no_empty_logger_calls.py [<root>...]

Exit code:
    0 — no offending calls found
    1 — at least one offender; the file:line of each is printed.

Default search root:
    wicked_zerg_challenger/
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Catches both bug variants from the print->logger migration:
#   1) `logger.info()`            — empty parens, the original 131-call regression.
#   2) `logger.info("")` / `('')` / `(f"")` — a no-op blank line, equally useless.
EMPTY_CALL_RE = re.compile(
    r"\blogger\.(?:debug|info|warning|warn|error|critical|exception)"
    r"\(\s*(?:[fF]?[\"\']\s*[\"\'])?\s*\)"
)


def find_offenders(roots: list[Path]) -> list[tuple[Path, int, str]]:
    offenders: list[tuple[Path, int, str]] = []
    for root in roots:
        if not root.exists():
            continue
        for py_file in root.rglob("*.py"):
            # Skip caches
            if "__pycache__" in py_file.parts:
                continue
            try:
                text = py_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                if EMPTY_CALL_RE.search(line):
                    offenders.append((py_file, lineno, line.rstrip()))
    return offenders


def main(argv: list[str]) -> int:
    repo_root = Path(__file__).resolve().parent.parent
    if argv:
        roots = [Path(a) for a in argv]
    else:
        roots = [repo_root / "wicked_zerg_challenger"]

    offenders = find_offenders(roots)
    if not offenders:
        print("OK: no empty logger calls found.")
        return 0

    print(f"FAIL: {len(offenders)} empty logger call(s) found:")
    for path, lineno, line in offenders:
        try:
            rel = path.relative_to(repo_root)
        except ValueError:
            rel = path
        print(f"  {rel}:{lineno}: {line}")
    print(
        "\nThese were introduced by the print->logger migration and should be "
        "removed or given an explicit message."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
