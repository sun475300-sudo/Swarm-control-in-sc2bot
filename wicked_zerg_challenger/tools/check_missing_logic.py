# -*- coding: utf-8 -*-
"""
누락 로직 검사 도구

호출되지만 정의되지 않은 메서드, pass 만 들어 있는 메서드,
TODO 주석을 찾아 보고합니다.
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
    """누락 로직 검사기"""

    def __init__(self):
        self.defined_methods: Dict[str, Set[str]] = defaultdict(set)  # file -> methods
        self.called_methods: Dict[str, Set[str]] = defaultdict(set)  # file -> methods
        self.pass_statements: Dict[str, List[int]] = defaultdict(list)  # file -> line numbers
        self.todo_comments: Dict[str, List[Tuple[int, str]]] = defaultdict(list)  # file -> (line, comment)
        self.missing_implementations: List[Dict] = []

    def extract_methods_from_file(self, file_path: Path) -> Set[str]:
        """파일에서 정의된 메서드 추출"""
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
        """파일에서 호출된 메서드 추출"""
        calls = set()
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
                lines = content.splitlines()

            # self._method() / await self._method() 패턴
            for line in lines:
                matches = re.findall(
                    r"(?:await\s+)?self\.(_[a-zA-Z_][a-zA-Z0-9_]*)\s*\(", line
                )
                calls.update(matches)

                # self.method() / await self.method() (public methods)
                matches2 = re.findall(
                    r"(?:await\s+)?self\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", line
                )
                calls.update(matches2)
        except Exception:
            pass
        return calls

    def find_pass_statements(self, file_path: Path) -> List[int]:
        """pass 만 있는 줄 찾기"""
        pass_lines = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                # 단독 pass 문 찾기 (주석이나 다른 코드와 함께 있는 것은 제외)
                if stripped == "pass" or (
                    stripped.startswith("pass") and len(stripped) == 4
                ):
                    # 함수 정의 직후의 pass 인지 확인
                    context = "\n".join(lines[max(0, i - 10) : i])
                    if "def " in context or "async def " in context:
                        pass_lines.append(i)
        except Exception:
            pass
        return pass_lines

    def find_todo_comments(self, file_path: Path) -> List[Tuple[int, str]]:
        """TODO 주석 찾기"""
        todos = []
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

    def scan_file(self, file_path: Path):
        """파일 스캔"""
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

        # 같은 파일 내에서 호출되었지만 정의되지 않은 메서드 찾기
        missing = called - defined
        if missing:
            for method in missing:
                self.missing_implementations.append(
                    {
                        "file": rel_path,
                        "method": method,
                        "type": "missing_in_same_file",
                    }
                )

    def scan_all(self) -> Dict:
        """전체 스캔"""
        excluded_parts = {
            "__pycache__",
            ".git",
            "node_modules",
            ".venv",
            "venv",
            "models",
            ".pytest_cache",
        }

        # ★ FIX: rglob 은 Path 객체만 반환하는데 (root, dirs, files) 로
        # 언패킹하던 기존 코드가 TypeError 를 일으켰습니다. 단일 Path 로 순회.
        for py_file in PROJECT_ROOT.rglob("*.py"):
            if not py_file.is_file():
                continue
            if any(part in excluded_parts for part in py_file.parts):
                continue
            self.scan_file(py_file)

        # 전체 프로젝트에서 호출되었지만 정의되지 않은 메서드 찾기
        all_defined = set()
        for methods in self.defined_methods.values():
            all_defined.update(methods)

        for file_path, called in self.called_methods.items():
            for method in called:
                if method not in all_defined and method.startswith("_"):
                    # private method 가 정의되지 않음
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
    """진입점"""
    logger.info("=" * 70)
    logger.info("누락 로직 검사 도구")
    logger.info("=" * 70)
    checker = MissingLogicChecker()
    logger.info("스캔 중...")
    results = checker.scan_all()

    logger.info("검사 완료")
    logger.info(f"  - 누락된 메서드: {results['total_missing']}개")
    logger.info(f"  - pass 만 있는 파일: {results['files_with_pass']}개")
    logger.info(f"  - TODO 주석이 있는 파일: {results['files_with_todos']}개")

    # 누락된 메서드 출력
    if results["missing_implementations"]:
        logger.info("=" * 70)
        logger.info("누락된 메서드:")
        logger.info("=" * 70)

        by_file = defaultdict(list)
        for item in results["missing_implementations"]:
            by_file[item["file"]].append(item["method"])

        for file_path, methods in sorted(by_file.items()):
            logger.info(f"\n{file_path}:")
            for method in sorted(set(methods)):
                logger.info(f"  - {method}")

    # pass 만 있는 파일 출력
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
            logger.info(f"\n{file_path}: {len(lines)}개 pass 라인")
            if len(lines) <= 20:
                logger.info(f"  라인: {', '.join(map(str, lines[:20]))}")
            else:
                logger.info(
                    f"  라인: {', '.join(map(str, lines[:20]))} ... (총 {len(lines)}개)"
                )

    # TODO 주석 출력
    if results["todo_comments"]:
        logger.info("\n" + "=" * 70)
        logger.info("TODO 주석 (상위 20개):")
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
