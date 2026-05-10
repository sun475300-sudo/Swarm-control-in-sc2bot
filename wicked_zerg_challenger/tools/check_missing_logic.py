# -*- coding: utf-8 -*-
"""Check for missing implementations.

Scans Python files to find:
- Methods that are called via ``self.foo(...)`` but never defined
- Functions whose body is a single ``pass`` placeholder
- ``TODO`` / ``FIXME`` / ``XXX`` comments
"""

import ast
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

logger = logging.getLogger("CheckMissingLogic")

PROJECT_ROOT = Path(__file__).parent.parent

EXCLUDED_DIR_PARTS = {
    "__pycache__",
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "models",
    ".pytest_cache",
}


class MissingLogicChecker:
    """Walk the project tree and collect missing-logic signals."""

    def __init__(self):
        self.defined_methods: Dict[str, Set[str]] = defaultdict(set)
        self.called_methods: Dict[str, Set[str]] = defaultdict(set)
        self.pass_statements: Dict[str, List[int]] = defaultdict(list)
        self.todo_comments: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
        self.missing_implementations: List[Dict] = []

    def extract_methods_from_file(self, file_path: Path) -> Set[str]:
        """Return the set of function/method names defined in ``file_path``."""
        methods: Set[str] = set()
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            try:
                tree = ast.parse(content, filename=str(file_path))
            except SyntaxError as exc:
                logger.debug("SyntaxError parsing %s: %s", file_path, exc)
                return methods

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.add(node.name)
        except OSError as exc:
            logger.debug("Could not read %s: %s", file_path, exc)
        return methods

    def extract_calls_from_file(self, file_path: Path) -> Set[str]:
        """Return the set of ``self.<name>(...)`` calls found in ``file_path``."""
        calls: Set[str] = set()
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            for line in content.splitlines():
                # Matches "self._foo(", "await self._foo(", "self.foo(" — pulls out the attribute.
                matches = re.findall(
                    r"(?:await\s+)?self\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
                    line,
                )
                calls.update(matches)
        except OSError as exc:
            logger.debug("Could not read %s: %s", file_path, exc)
        return calls

    def find_pass_statements(self, file_path: Path) -> List[int]:
        """Return line numbers where a function body is just ``pass``."""
        pass_lines: List[int] = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped == "pass":
                    # Heuristic: only count `pass` that follows a function definition recently.
                    context = "\n".join(lines[max(0, i - 10) : i])
                    if "def " in context or "async def " in context:
                        pass_lines.append(i)
        except OSError as exc:
            logger.debug("Could not read %s: %s", file_path, exc)
        return pass_lines

    def find_todo_comments(self, file_path: Path) -> List[Tuple[int, str]]:
        """Return ``(line_number, line_text)`` for TODO/FIXME/XXX comments."""
        todos: List[Tuple[int, str]] = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                upper = line.upper()
                if "TODO" in upper or "FIXME" in upper or "XXX" in upper:
                    todos.append((i, line.strip()))
        except OSError as exc:
            logger.debug("Could not read %s: %s", file_path, exc)
        return todos

    def scan_file(self, file_path: Path) -> None:
        """Scan a single Python file and record findings."""
        rel_path = str(file_path.relative_to(PROJECT_ROOT))

        defined = self.extract_methods_from_file(file_path)
        called = self.extract_calls_from_file(file_path)
        pass_lines = self.find_pass_statements(file_path)
        todos = self.find_todo_comments(file_path)

        self.defined_methods[rel_path] = defined
        self.called_methods[rel_path] = called
        if pass_lines:
            self.pass_statements[rel_path] = pass_lines
        if todos:
            self.todo_comments[rel_path] = todos

        # Same-file private-call check: self._foo() called but _foo not defined here.
        missing = called - defined
        if missing:
            for method in missing:
                if not method.startswith("_"):
                    continue
                self.missing_implementations.append(
                    {
                        "file": rel_path,
                        "method": method,
                        "type": "missing_in_same_file",
                    }
                )

    def scan_all(self) -> Dict:
        """Walk the whole project and return a summary."""
        for path in PROJECT_ROOT.rglob("*.py"):
            if any(part in EXCLUDED_DIR_PARTS for part in path.parts):
                continue
            if not path.is_file():
                continue
            self.scan_file(path)

        # Project-wide check: any private call that isn't defined anywhere.
        all_defined: Set[str] = set()
        for methods in self.defined_methods.values():
            all_defined.update(methods)

        for file_path, called in self.called_methods.items():
            for method in called:
                if method.startswith("_") and method not in all_defined:
                    self.missing_implementations.append(
                        {
                            "file": file_path,
                            "method": method,
                            "type": "missing_in_project",
                        }
                    )

        return {
            "missing_implementations": self.missing_implementations,
            "pass_statements": dict(self.pass_statements),
            "todo_comments": dict(self.todo_comments),
            "files_with_pass": len(self.pass_statements),
            "files_with_todos": len(self.todo_comments),
            "total_missing": len(self.missing_implementations),
        }


def main() -> None:
    """Entry point: scan the project and log a report."""
    logger.info("=" * 70)
    logger.info("Missing-logic checker")
    logger.info("=" * 70)
    checker = MissingLogicChecker()
    logger.info("Scanning ...")
    results = checker.scan_all()

    logger.info("Scan complete.")
    logger.info("  - missing methods: %d", results["total_missing"])
    logger.info("  - files with bare 'pass': %d", results["files_with_pass"])
    logger.info("  - files with TODO/FIXME/XXX: %d", results["files_with_todos"])

    if results["missing_implementations"]:
        logger.info("=" * 70)
        logger.info("Missing methods:")
        logger.info("=" * 70)

        by_file = defaultdict(list)
        for item in results["missing_implementations"]:
            by_file[item["file"]].append(item["method"])

        for file_path, methods in sorted(by_file.items()):
            logger.info("\n%s:", file_path)
            for method in sorted(set(methods)):
                logger.info("  - %s", method)

    if results["pass_statements"]:
        logger.info("\n" + "=" * 70)
        logger.info("Top files by bare-'pass' count (top 10):")
        logger.info("=" * 70)

        sorted_files = sorted(
            results["pass_statements"].items(),
            key=lambda x: len(x[1]),
            reverse=True,
        )[:10]

        for file_path, lines in sorted_files:
            logger.info("\n%s: %d 'pass' lines", file_path, len(lines))
            preview = ", ".join(map(str, lines[:20]))
            if len(lines) <= 20:
                logger.info("  lines: %s", preview)
            else:
                logger.info("  lines: %s ... (total %d)", preview, len(lines))

    if results["todo_comments"]:
        logger.info("\n" + "=" * 70)
        logger.info("TODO comments (first 20):")
        logger.info("=" * 70)

        count = 0
        for file_path, todos in sorted(results["todo_comments"].items()):
            for line_num, comment in todos:
                if count >= 20:
                    break
                logger.info("\n%s:%d", file_path, line_num)
                logger.info("  %s", comment[:100])
                count += 1
            if count >= 20:
                break


if __name__ == "__main__":
    main()
