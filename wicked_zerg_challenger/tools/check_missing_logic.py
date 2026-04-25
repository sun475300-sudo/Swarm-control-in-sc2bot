# -*- coding: utf-8 -*-
"""
Missing-logic checker.

Scans the project for:
  * methods that are called but not defined
  * functions whose body is only `pass`
  * TODO / FIXME / XXX comments

The previous version of this file had two problems:
  1. Korean comments and log messages were stored in CP949 bytes but the
     file declared UTF-8, so every string was rendered as mojibake.
  2. `Path.rglob('*.py')` returns Path objects, but the scanner unpacked
     each result as `(root, dirs, files)` — so the script crashed with
     `TypeError: cannot unpack non-iterable PosixPath object` on first
     iteration. The whole tool was DOA.

Both issues are fixed here. Comments are now plain English so the file
survives encoding round-trips on every platform.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import logging

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
    """Scans a Python tree for missing implementations and TODOs."""

    def __init__(self) -> None:
        self.defined_methods: Dict[str, Set[str]] = defaultdict(set)
        self.called_methods: Dict[str, Set[str]] = defaultdict(set)
        self.pass_statements: Dict[str, List[int]] = defaultdict(list)
        self.todo_comments: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
        self.missing_implementations: List[Dict] = []

    def extract_methods_from_file(self, file_path: Path) -> Set[str]:
        """Return every (sync/async) function name defined in `file_path`."""
        methods: Set[str] = set()
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            try:
                tree = ast.parse(content, filename=str(file_path))
            except SyntaxError:
                return methods
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.add(node.name)
        except OSError:
            pass
        return methods

    def extract_calls_from_file(self, file_path: Path) -> Set[str]:
        """Return every `self.<name>(` call (sync or awaited) in the file."""
        calls: Set[str] = set()
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            return calls
        for line in content.splitlines():
            calls.update(
                re.findall(r"(?:await\s+)?self\.(_[a-zA-Z_][a-zA-Z0-9_]*)\s*\(", line)
            )
            calls.update(
                re.findall(r"(?:await\s+)?self\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", line)
            )
        return calls

    def find_pass_statements(self, file_path: Path) -> List[int]:
        """Return line numbers where a function body is only `pass`."""
        pass_lines: List[int] = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except OSError:
            return pass_lines
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped == "pass":
                context = "\n".join(lines[max(0, i - 10): i])
                if "def " in context or "async def " in context:
                    pass_lines.append(i)
        return pass_lines

    def find_todo_comments(self, file_path: Path) -> List[Tuple[int, str]]:
        """Return (line_number, line_text) for every TODO/FIXME/XXX line."""
        todos: List[Tuple[int, str]] = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except OSError:
            return todos
        for i, line in enumerate(lines, 1):
            upper = line.upper()
            if "TODO" in upper or "FIXME" in upper or "XXX" in upper:
                todos.append((i, line.strip()))
        return todos

    def scan_file(self, file_path: Path) -> None:
        """Record findings for a single file."""
        try:
            rel_path = str(file_path.relative_to(PROJECT_ROOT))
        except ValueError:
            rel_path = str(file_path)

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

        for method in called - defined:
            self.missing_implementations.append(
                {
                    "file": rel_path,
                    "method": method,
                    "type": "missing_in_same_file",
                }
            )

    def scan_all(self) -> Dict:
        """Walk the project tree once."""
        for path in PROJECT_ROOT.rglob("*.py"):
            if any(part in EXCLUDED_DIR_PARTS for part in path.parts):
                continue
            if path.is_file():
                self.scan_file(path)

        all_defined: Set[str] = set()
        for methods in self.defined_methods.values():
            all_defined.update(methods)

        for file_path, called in self.called_methods.items():
            for method in called:
                if method not in all_defined and method.startswith("_"):
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
    """CLI entry point."""
    logger.info("=" * 70)
    logger.info("Missing-logic check starting")
    logger.info("=" * 70)
    checker = MissingLogicChecker()
    logger.info("Scanning...")
    results = checker.scan_all()

    logger.info("Scan complete")
    logger.info(f"  - missing methods: {results['total_missing']}")
    logger.info(f"  - files with pass-only bodies: {results['files_with_pass']}")
    logger.info(f"  - files with TODOs: {results['files_with_todos']}")

    if results["missing_implementations"]:
        logger.info("=" * 70)
        logger.info("Missing methods:")
        logger.info("=" * 70)
        by_file: Dict[str, List[str]] = defaultdict(list)
        for item in results["missing_implementations"]:
            by_file[item["file"]].append(item["method"])
        for file_path, methods in sorted(by_file.items()):
            logger.info(f"\n{file_path}:")
            for method in sorted(set(methods)):
                logger.info(f"  - {method}")

    if results["pass_statements"]:
        logger.info("\n" + "=" * 70)
        logger.info("Top 10 files by pass-only count:")
        logger.info("=" * 70)
        sorted_files = sorted(
            results["pass_statements"].items(),
            key=lambda x: len(x[1]),
            reverse=True,
        )[:10]
        for file_path, lines in sorted_files:
            logger.info(f"\n{file_path}: {len(lines)} pass lines")
            preview = ", ".join(map(str, lines[:20]))
            if len(lines) <= 20:
                logger.info(f"  lines: {preview}")
            else:
                logger.info(f"  lines: {preview} ... (total {len(lines)})")

    if results["todo_comments"]:
        logger.info("\n" + "=" * 70)
        logger.info("First 20 TODO comments:")
        logger.info("=" * 70)
        count = 0
        for file_path, todos in sorted(results["todo_comments"].items()):
            for line_num, comment in todos:
                if count >= 20:
                    break
                logger.info(f"\n{file_path}:{line_num}")
                logger.info(f"  {comment[:100]}")
                count += 1
            if count >= 20:
                break


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
