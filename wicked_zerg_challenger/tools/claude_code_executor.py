# -*- coding: utf-8 -*-
"""
클로드 코드를 위한 자동 실행 및 테스트 도구

클로드 코드가 코드 변경 후 자동으로 테스트하고 검증할 수 있도록 도와주는 도구
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Optional
import json

PROJECT_ROOT = Path(__file__).parent.parent


class ClaudeCodeExecutor:
    """클로드 코드 실행기"""
 
 def __init__(self):
 self.test_results: List[Dict] = []
 self.execution_log: List[str] = []
 
 def run_tests(self, test_pattern: Optional[str] = None) -> Dict:
        """테스트 실행"""
        print("=" * 70)
        print("테스트 실행")
        print("=" * 70)
 print()
 
 # pytest가 있는지 확인
 try:
 result = subprocess.run(
                [sys.executable, "-m", "pytest", "--version"],
 capture_output=True,
 text=True,
 timeout=10
 )
 has_pytest = result.returncode == 0
 except Exception:
 has_pytest = False
 
 if not has_pytest:
            print("[INFO] pytest가 설치되어 있지 않습니다.")
            print("[INFO] 간단한 문법 검사만 수행합니다.")
 return self._run_syntax_check()
 
 # pytest 실행
        cmd = [sys.executable, "-m", "pytest"]
 if test_pattern:
 cmd.append(test_pattern)
 else:
            cmd.append("--collect-only")  # 테스트 수집만
 
 try:
 result = subprocess.run(
 cmd,
 cwd=PROJECT_ROOT,
 capture_output=True,
 text=True,
 timeout=300
 )
 
 return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
 }
 except subprocess.TimeoutExpired:
 return {
                "success": False,
                "error": "테스트 실행 시간 초과"
 }
 except Exception as e:
 return {
                "success": False,
                "error": str(e)
 }
 
 def _run_syntax_check(self) -> Dict:
        """문법 검사"""
        print("Python 파일 문법 검사 중...")
 
 errors = []
 checked = 0
 
 for root, dirs, files in os.walk(PROJECT_ROOT):
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'node_modules', '.venv', 'venv'}]
 
 for file in files:
                if file.endswith('.py'):
 file_path = Path(root) / file
 try:
 result = subprocess.run(
                            [sys.executable, "-m", "py_compile", str(file_path)],
 capture_output=True,
 text=True,
 timeout=5
 )
 checked += 1
 if result.returncode != 0:
 errors.append({
                                "file": str(file_path.relative_to(PROJECT_ROOT)),
                                "error": result.stderr
 })
 except Exception as e:
 errors.append({
                            "file": str(file_path.relative_to(PROJECT_ROOT)),
                            "error": str(e)
 })
 
 return {
            "success": len(errors) == 0,
            "checked": checked,
            "errors": errors
 }
 
 def run_refactoring_analysis(self) -> Dict:
        """리팩토링 분석 실행"""
        print("=" * 70)
        print("리팩토링 분석 실행")
        print("=" * 70)
 print()
 
 try:
 result = subprocess.run(
                [sys.executable, "tools/refactoring_analyzer.py"],
 cwd=PROJECT_ROOT,
 capture_output=True,
 text=True,
 timeout=600
 )
 
 return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "report_path": PROJECT_ROOT / "REFACTORING_ANALYSIS_REPORT.md"
 }
 except Exception as e:
 return {
                "success": False,
                "error": str(e)
 }
 
 def run_documentation_generation(self) -> Dict:
        """문서 생성 실행"""
        print("=" * 70)
        print("문서 생성 실행")
        print("=" * 70)
 print()
 
 try:
 result = subprocess.run(
                [sys.executable, "tools/auto_documentation_generator.py"],
 cwd=PROJECT_ROOT,
 capture_output=True,
 text=True,
 timeout=300
 )
 
 return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "api_doc_path": PROJECT_ROOT / "docs" / "API_DOCUMENTATION.md",
                "readme_proposal_path": PROJECT_ROOT / "docs" / "README_UPDATE_PROPOSAL.md"
 }
 except Exception as e:
 return {
                "success": False,
                "error": str(e)
 }
 
 def validate_changes(self, changed_files: List[str]) -> Dict:
        """변경 사항 검증"""
        print("=" * 70)
        print("변경 사항 검증")
        print("=" * 70)
 print()
 
 validation_results = {
            "syntax_check": {},
            "import_check": {},
            "files": changed_files
 }
 
 # 문법 검사
 for file_path in changed_files:
 full_path = PROJECT_ROOT / file_path
            if full_path.exists() and file_path.endswith('.py'):
 try:
 result = subprocess.run(
                        [sys.executable, "-m", "py_compile", str(full_path)],
 capture_output=True,
 text=True,
 timeout=5
 )
                    validation_results["syntax_check"][file_path] = {
                        "success": result.returncode == 0,
                        "error": result.stderr if result.returncode != 0 else None
 }
 except Exception as e:
                    validation_results["syntax_check"][file_path] = {
                        "success": False,
                        "error": str(e)
 }
 
 return validation_results
 
 def generate_execution_report(self) -> str:
        """실행 리포트 생성"""
 report = []
        report.append("# 클로드 코드 실행 리포트\n\n")
        report.append("**생성 일시**: 2026-01-15\n\n")
        report.append("---\n\n")
 
        report.append("## 실행 로그\n\n")
 for log_entry in self.execution_log:
            report.append(f"- {log_entry}\n")
        report.append("\n")
 
        report.append("## 테스트 결과\n\n")
 for test_result in self.test_results:
            report.append(f"### {test_result.get('name', 'Unknown')}\n\n")
            report.append(f"- **성공**: {test_result.get('success', False)}\n")
            if test_result.get('error'):
                report.append(f"- **에러**: {test_result['error']}\n")
            report.append("\n")
 
        return ''.join(report)


def main():
    """메인 함수"""
 import argparse
 
    parser = argparse.ArgumentParser(description="클로드 코드 실행 도구")
    parser.add_argument("--test", action="store_true", help="테스트 실행")
    parser.add_argument("--refactor", action="store_true", help="리팩토링 분석 실행")
    parser.add_argument("--docs", action="store_true", help="문서 생성 실행")
    parser.add_argument("--validate", nargs="+", help="변경 파일 검증")
 
 args = parser.parse_args()
 
 executor = ClaudeCodeExecutor()
 
 if args.test:
 result = executor.run_tests()
        print(f"테스트 결과: {'성공' if result.get('success') else '실패'}")
 
 if args.refactor:
 result = executor.run_refactoring_analysis()
        print(f"리팩토링 분석: {'성공' if result.get('success') else '실패'}")
 
 if args.docs:
 result = executor.run_documentation_generation()
        print(f"문서 생성: {'성공' if result.get('success') else '실패'}")
 
 if args.validate:
 result = executor.validate_changes(args.validate)
        print(f"검증 완료: {len(result['files'])}개 파일")


if __name__ == "__main__":
 import os
 main()