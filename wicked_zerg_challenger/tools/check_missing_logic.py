# -*- coding: utf-8 -*-
"""
Missing logic checker.

Scans for methods that are called but never defined, "pass"-only
method bodies, and TODO/FIXME/XXX comments.
"""

import ast
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

logger = logging.getLogger("CheckMissingLogic")

PROJECT_ROOT = Path(__file__).parent.parent


class MissingLogicChecker:
    """Scans the project for missing/incomplete implementations."""

    def __init__(self):
        self.defined_methods: Dict[str, Set[str]] = defaultdict(set)  # file -> methods
        self.called_methods: Dict[str, Set[str]] = defaultdict(set)  # file -> methods
        self.pass_statements: Dict[str, List[int]] = defaultdict(
            list
        )  # file -> line numbers
        self.todo_comments: Dict[str, List[Tuple[int, str]]] = defaultdict(
            list
        )  # file -> (line, comment)
        self.missing_implementations: List[Dict] = []

    def extract_methods_from_file(self, file_path: Path) -> Set[str]:
        """Collect method/function names defined in a file."""
        methods = set()
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            try:
                tree = ast.parse(content, filename=str(file_path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        methods.add(node.name)
                    elif isinstance(node, ast.AsyncFunctionDef):
                        methods.add(node.name)
            except SyntaxError:
                pass
        except Exception:
            pass
        return methods

    def extract_calls_from_file(self, file_path: Path) -> Set[str]:
        """Collect `self.method()` calls made in a file (comments excluded)."""
        calls = set()
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
                lines = content.splitlines()

            for line in lines:
                # Skip commented-out code so it isn't mistaken for a live call.
                code_part = line.split("#", 1)[0]
                if not code_part.strip():
                    continue

                # self._method() / await self._method() (private methods)
                matches = re.findall(
                    r"(?:await\s+)?self\.(_[a-zA-Z_][a-zA-Z0-9_]*)\s*\(", code_part
                )
                calls.update(matches)

                # self.method() / await self.method() (public methods)
                matches2 = re.findall(
                    r"(?:await\s+)?self\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", code_part
                )
                calls.update(matches2)
        except Exception:
            pass
        return calls

    def find_pass_statements(self, file_path: Path) -> List[int]:
        """Find lone `pass` statements that are the entire body of a function."""
        pass_lines = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                # Only a standalone "pass" line, not one combined with other code.
                if stripped == "pass" or (
                    stripped.startswith("pass") and len(stripped) == 4
                ):
                    # Confirm this pass is directly inside a function body.
                    context = "\n".join(lines[max(0, i - 10) : i])
                    if "def " in context or "async def " in context:
                        pass_lines.append(i)
        except Exception:
            pass
        return pass_lines

    def find_todo_comments(self, file_path: Path) -> List[Tuple[int, str]]:
        """Find TODO/FIXME/XXX comments."""
        todos = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                if (
                    "TODO" in line.upper()
                    or "FIXME" in line.upper()
                    or "XXX" in line.upper()
                ):
                    todos.append((i, line.strip()))
        except Exception:
            pass
        return todos

    def scan_file(self, file_path: Path):
        """Scan a single file."""
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

        # Methods called in this file but not defined anywhere in it.
        missing = called - defined
        if missing:
            for method in missing:
                self.missing_implementations.append(
                    {"file": rel_path, "method": method, "type": "missing_in_same_file"}
                )

    def scan_all(self) -> Dict:
        """Scan the whole project."""
        excluded_parts = {
            "__pycache__",
            ".git",
            "node_modules",
            ".venv",
            "venv",
            "models",
            ".pytest_cache",
        }
        for py_file in Path(PROJECT_ROOT).rglob("*.py"):
            if excluded_parts.intersection(py_file.parts):
                continue
            if py_file.is_file():
                self.scan_file(py_file)

        # Private methods called somewhere in the project but defined nowhere.
        all_defined = set()
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


def main():
    """Run the scan and print a report."""
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.setLevel(logging.INFO)

    logger.info("=" * 70)
    logger.info("Missing logic checker")
    logger.info("=" * 70)
    checker = MissingLogicChecker()
    logger.info("Scanning...")
    results = checker.scan_all()

    logger.info("\nScan complete!")
    logger.info(f"  - Missing methods: {results['total_missing']}")
    logger.info(f"  - Files with pass-only bodies: {results['files_with_pass']}")
    logger.info(f"  - Files with TODO comments: {results['files_with_todos']}")

    if results["missing_implementations"]:
        logger.info("=" * 70)
        logger.info("Missing methods:")
        logger.info("=" * 70)

        by_file = defaultdict(list)
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
            results["pass_statements"].items(), key=lambda x: len(x[1]), reverse=True
        )[:10]

        for file_path, lines in sorted_files:
            logger.info(f"\n{file_path}: {len(lines)} pass statement(s)")
            if len(lines) <= 20:
                logger.info(f"  lines: {', '.join(map(str, lines[:20]))}")
            else:
                logger.info(
                    f"  lines: {', '.join(map(str, lines[:20]))} ... ({len(lines)} total)"
                )

    if results["todo_comments"]:
        logger.info("\n" + "=" * 70)
        logger.info("TODO comments (top 20):")
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
