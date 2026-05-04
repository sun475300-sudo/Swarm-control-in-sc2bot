# -*- coding: utf-8 -*-
"""Missing-logic auditor.

Walks every Python file in the project, extracts defined / called method
names via AST + regex, and reports:
  - methods that are called but never defined,
  - functions whose body is just ``pass`` (likely stubs),
  - lines containing TODO / FIXME / XXX comments.
"""

import ast
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

logger = logging.getLogger("CheckMissingLogic")

PROJECT_ROOT = Path(__file__).parent.parent

EXCLUDE_DIR_PARTS = {
    "__pycache__",
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "models",
    ".pytest_cache",
}


class MissingLogicChecker:
    """Find missing implementations / pass-only stubs / TODOs."""

    def __init__(self):
        self.defined_methods: Dict[str, Set[str]] = defaultdict(set)
        self.called_methods: Dict[str, Set[str]] = defaultdict(set)
        self.pass_statements: Dict[str, List[int]] = defaultdict(list)
        self.todo_comments: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
        self.missing_implementations: List[Dict] = []

    def extract_methods_from_file(self, file_path: Path) -> Set[str]:
        """Extract names of every def / async def in the file."""
        methods: Set[str] = set()
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            try:
                tree = ast.parse(content, filename=str(file_path))
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.add(node.name)
            except SyntaxError:
                pass
        except Exception:
            pass
        return methods

    def extract_calls_from_file(self, file_path: Path) -> Set[str]:
        """Extract self.<method>(...) call names from the file."""
        calls: Set[str] = set()
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
            for line in lines:
                # await self._method(...) / self._method(...)
                calls.update(
                    re.findall(
                        r"(?:await\s+)?self\.(_[a-zA-Z_][a-zA-Z0-9_]*)\s*\(", line
                    )
                )
                # public self.method(...)
                calls.update(
                    re.findall(
                        r"(?:await\s+)?self\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", line
                    )
                )
        except Exception:
            pass
        return calls

    def find_pass_statements(self, file_path: Path) -> List[int]:
        """Find lines whose body is a bare `pass` directly under a def/async-def."""
        pass_lines: List[int] = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped == "pass":
                    context = "\n".join(lines[max(0, i - 10) : i])
                    if "def " in context or "async def " in context:
                        pass_lines.append(i)
        except Exception:
            pass
        return pass_lines

    def find_todo_comments(self, file_path: Path) -> List[Tuple[int, str]]:
        """Find TODO / FIXME / XXX lines."""
        todos: List[Tuple[int, str]] = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            for i, line in enumerate(lines, 1):
                upper = line.upper()
                if "TODO" in upper or "FIXME" in upper or "XXX" in upper:
                    todos.append((i, line.strip()))
        except Exception:
            pass
        return todos

    def scan_file(self, file_path: Path) -> None:
        """Scan a single file and record results keyed on its relative path."""
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

        # Same-file: called but not defined here.
        for method in called - defined:
            self.missing_implementations.append(
                {
                    "file": rel_path,
                    "method": method,
                    "type": "missing_in_same_file",
                }
            )

    def scan_all(self) -> Dict:
        """Scan every .py file under PROJECT_ROOT."""
        for path in PROJECT_ROOT.rglob("*.py"):
            if any(part in EXCLUDE_DIR_PARTS for part in path.parts):
                continue
            if path.is_file():
                self.scan_file(path)

        # Cross-file: private methods called somewhere but never defined anywhere.
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
    logger.info("=" * 70)
    logger.info("Missing-logic checker started")
    logger.info("=" * 70)
    checker = MissingLogicChecker()
    logger.info("Scanning ...")
    results = checker.scan_all()

    logger.info("Scan complete!")
    logger.info(f"  - missing methods: {results['total_missing']}")
    logger.info(f"  - files with pass-only bodies: {results['files_with_pass']}")
    logger.info(f"  - files with TODO comments: {results['files_with_todos']}")

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
        logger.info("Files with the most pass-only bodies (top 10):")
        logger.info("=" * 70)
        sorted_files = sorted(
            results["pass_statements"].items(),
            key=lambda x: len(x[1]),
            reverse=True,
        )[:10]
        for file_path, lines in sorted_files:
            logger.info(f"\n{file_path}: {len(lines)} pass-only line(s)")
            if len(lines) <= 20:
                logger.info(f"  lines: {', '.join(map(str, lines[:20]))}")
            else:
                logger.info(
                    f"  lines: {', '.join(map(str, lines[:20]))} ... ({len(lines)} total)"
                )

    if results["todo_comments"]:
        logger.info("\n" + "=" * 70)
        logger.info("TODO comments (first 20):")
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
    main()
