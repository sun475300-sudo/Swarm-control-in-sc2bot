# -*- coding: utf-8 -*-
"""
누락 로직 검사 도구

호출되지만 정의되지 않은 메서드, pass 문만 있는 메서드,
TODO 주석을 찾는다.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger("CheckMissingLogic")

PROJECT_ROOT = Path(__file__).parent.parent

EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "models",
    ".pytest_cache",
}


class MissingLogicChecker:
    """누락 로직 검사기."""

    def __init__(self) -> None:
        self.defined_methods: Dict[str, Set[str]] = defaultdict(set)
        self.called_methods: Dict[str, Set[str]] = defaultdict(set)
        self.pass_statements: Dict[str, List[int]] = defaultdict(list)
        self.todo_comments: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
        self.missing_implementations: List[Dict] = []

    def extract_methods_from_file(self, file_path: Path) -> Set[str]:
        """파일에서 정의된 메서드 이름을 모두 수집한다."""
        methods: Set[str] = set()
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            try:
                tree = ast.parse(content, filename=str(file_path))
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.add(node.name)
            except SyntaxError as exc:
                logger.debug("syntax error in %s: %s", file_path, exc)
        except OSError as exc:
            logger.debug("cannot read %s: %s", file_path, exc)
        return methods

    def extract_calls_from_file(self, file_path: Path) -> Set[str]:
        """파일에서 `self.*` 형태로 호출되는 메서드 이름을 수집한다."""
        calls: Set[str] = set()
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            for line in content.splitlines():
                # `await self._method(` / `self._method(`
                matches = re.findall(
                    r"(?:await\s+)?self\.(_[a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
                    line,
                )
                calls.update(matches)
                # public method 호출
                matches_public = re.findall(
                    r"(?:await\s+)?self\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
                    line,
                )
                calls.update(matches_public)
        except OSError as exc:
            logger.debug("cannot read %s: %s", file_path, exc)
        return calls

    def find_pass_statements(self, file_path: Path) -> List[int]:
        """함수 본문이 단일 `pass` 인 위치의 라인 번호를 반환한다."""
        pass_lines: List[int] = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            try:
                tree = ast.parse(content, filename=str(file_path))
            except SyntaxError:
                return pass_lines
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    body = node.body
                    # docstring 제외 후 본문이 pass 한 문장뿐인 경우만 카운트
                    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                        body = body[1:]
                    if len(body) == 1 and isinstance(body[0], ast.Pass):
                        pass_lines.append(body[0].lineno)
        except OSError as exc:
            logger.debug("cannot read %s: %s", file_path, exc)
        return pass_lines

    def find_todo_comments(self, file_path: Path) -> List[Tuple[int, str]]:
        """TODO / FIXME / XXX 주석을 찾는다."""
        todos: List[Tuple[int, str]] = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            for i, line in enumerate(lines, 1):
                upper = line.upper()
                if "TODO" in upper or "FIXME" in upper or "XXX" in upper:
                    todos.append((i, line.strip()))
        except OSError as exc:
            logger.debug("cannot read %s: %s", file_path, exc)
        return todos

    def scan_file(self, file_path: Path) -> None:
        """단일 파일 검사."""
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

        # 같은 파일에서 호출되지만 정의되지 않은 메서드
        missing = called - defined
        for method in missing:
            self.missing_implementations.append(
                {
                    "file": rel_path,
                    "method": method,
                    "type": "missing_in_same_file",
                }
            )

    def scan_all(self) -> Dict:
        """프로젝트 전체 검사."""
        for file_path in PROJECT_ROOT.rglob("*.py"):
            if any(part in EXCLUDED_DIRS for part in file_path.parts):
                continue
            if file_path.is_file():
                self.scan_file(file_path)

        all_defined: Set[str] = set()
        for methods in self.defined_methods.values():
            all_defined.update(methods)

        # 프로젝트 어디에도 정의되지 않은 private 메서드 호출
        # (이미 missing_in_same_file 로 기록한 항목은 중복으로 추가될 수 있으므로
        #  set 으로 관리)
        seen: Set[Tuple[str, str]] = {
            (it["file"], it["method"]) for it in self.missing_implementations
        }
        for file_path, called in self.called_methods.items():
            for method in called:
                if method.startswith("_") and method not in all_defined:
                    key = (file_path, method)
                    if key in seen:
                        continue
                    seen.add(key)
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
    """엔트리 포인트."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    logger.info("=" * 70)
    logger.info("누락 로직 검사 도구")
    logger.info("=" * 70)
    checker = MissingLogicChecker()
    logger.info("스캔 중...")
    results = checker.scan_all()

    logger.info("\n검사 완료!")
    logger.info("  - 누락 메서드: %d건", results["total_missing"])
    logger.info("  - pass 만 있는 파일: %d개", results["files_with_pass"])
    logger.info("  - TODO 주석이 있는 파일: %d개", results["files_with_todos"])

    if results["missing_implementations"]:
        logger.info("=" * 70)
        logger.info("누락 메서드:")
        logger.info("=" * 70)
        by_file: Dict[str, List[str]] = defaultdict(list)
        for item in results["missing_implementations"]:
            by_file[item["file"]].append(item["method"])
        for file_path, methods in sorted(by_file.items()):
            logger.info("\n%s:", file_path)
            for method in sorted(set(methods)):
                logger.info("  - %s", method)

    if results["pass_statements"]:
        logger.info("\n" + "=" * 70)
        logger.info("pass 만 있는 파일 (상위 10개):")
        logger.info("=" * 70)
        sorted_files = sorted(
            results["pass_statements"].items(),
            key=lambda x: len(x[1]),
            reverse=True,
        )[:10]
        for file_path, lines in sorted_files:
            logger.info("\n%s: %d개 pass 문", file_path, len(lines))
            preview = ", ".join(map(str, lines[:20]))
            if len(lines) <= 20:
                logger.info("  라인: %s", preview)
            else:
                logger.info("  라인: %s ... (총 %d개)", preview, len(lines))

    if results["todo_comments"]:
        logger.info("\n" + "=" * 70)
        logger.info("TODO 주석 (상위 20개):")
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
