# -*- coding: utf-8 -*-
"""
구현 누락 검사 도구

호출되었지만 정의되지 않은 메서드, pass 만 있는 메서드, TODO 주석을 찾는다.
"""

import ast
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

logger = logging.getLogger("CheckMissingLogic")

PROJECT_ROOT = Path(__file__).parent.parent

EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "models",
    ".pytest_cache",
}


class MissingLogicChecker:
    """구현 누락 검사기"""

    def __init__(self) -> None:
        self.defined_methods: Dict[str, Set[str]] = defaultdict(set)
        self.called_methods: Dict[str, Set[str]] = defaultdict(set)
        self.pass_statements: Dict[str, List[int]] = defaultdict(list)
        self.todo_comments: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
        self.missing_implementations: List[Dict] = []

    def extract_methods_from_file(self, file_path: Path) -> Set[str]:
        """파일에서 정의된 메서드 추출"""
        methods: Set[str] = set()
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=str(file_path))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.add(node.name)
        except SyntaxError as e:
            logger.debug("SyntaxError in %s: %s", file_path, e)
        except OSError as e:
            logger.debug("OSError reading %s: %s", file_path, e)
        return methods

    def extract_calls_from_file(self, file_path: Path) -> Set[str]:
        """파일에서 호출된 메서드 추출"""
        calls: Set[str] = set()
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            logger.debug("OSError reading %s: %s", file_path, e)
            return calls

        # await self._method() / self._method() / self.method() 모두 캡처
        pattern = re.compile(r"(?:await\s+)?self\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")
        for line in content.splitlines():
            calls.update(pattern.findall(line))
        return calls

    def find_pass_statements(self, file_path: Path) -> List[int]:
        """함수 본문이 pass 단독인 라인을 찾는다"""
        pass_lines: List[int] = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return pass_lines

        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            return pass_lines

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # docstring 만 있거나 pass 만 있는 본문
                body = node.body
                if len(body) == 1 and isinstance(body[0], ast.Pass):
                    pass_lines.append(body[0].lineno)
        return pass_lines

    def find_todo_comments(self, file_path: Path) -> List[Tuple[int, str]]:
        """TODO/FIXME/XXX 주석 찾기"""
        todos: List[Tuple[int, str]] = []
        try:
            lines = file_path.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()
        except OSError:
            return todos

        for i, line in enumerate(lines, 1):
            up = line.upper()
            if "TODO" in up or "FIXME" in up or "XXX" in up:
                todos.append((i, line.strip()))
        return todos

    def scan_file(self, file_path: Path) -> None:
        """단일 파일 스캔"""
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

        # 같은 파일 안에서 호출되었지만 정의되지 않은 메서드
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
        """전체 프로젝트 스캔"""
        for path in PROJECT_ROOT.rglob("*.py"):
            if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
                continue
            if path.is_file():
                self.scan_file(path)

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
    """엔트리포인트"""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    logger.info("=" * 70)
    logger.info("구현 누락 검사 시작")
    logger.info("=" * 70)
    checker = MissingLogicChecker()
    logger.info("스캔 중...")
    results = checker.scan_all()

    logger.info("\n검사 완료!")
    logger.info("  - 누락 메서드: %d개", results["total_missing"])
    logger.info("  - pass 만 있는 파일: %d개", results["files_with_pass"])
    logger.info("  - TODO 주석이 있는 파일: %d개", results["files_with_todos"])

    if results["missing_implementations"]:
        logger.info("=" * 70)
        logger.info("누락된 메서드:")
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
            logger.info("\n%s: %d개 pass", file_path, len(lines))
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
