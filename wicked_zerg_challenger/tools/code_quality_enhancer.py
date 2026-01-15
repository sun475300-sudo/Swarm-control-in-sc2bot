# -*- coding: utf-8 -*-
"""
코드 품질 개선 및 버그 수정 도구

소스코드 품질 개선, 버그 발견 및 수정, 에러 처리 강화
"""

import ast
import re

PROJECT_ROOT = Path(__file__).parent.parent


class CodeQualityEnhancer:
    """코드 품질 개선기"""
 
 def __init__(self):
 self.issues_found: List[Dict] = []
 self.fixes_applied: List[Dict] = []
 
 def analyze_file(self, file_path: Path) -> Dict:
        """파일 분석"""
 analysis = {
            "file": str(file_path.relative_to(PROJECT_ROOT)),
            "errors": [],
            "warnings": [],
            "suggestions": []
 }
 
 try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 lines = content.splitlines()
 
 # AST 파싱
 try:
 tree = ast.parse(content, filename=str(file_path))
 except SyntaxError as e:
                analysis["errors"].append({
                    "type": "syntax_error",
                    "line": e.lineno,
                    "message": str(e)
 })
 return analysis
 
 # 에러 처리 분석
 self._analyze_error_handling(tree, lines, analysis)
 
 # 버그 패턴 찾기
 self._find_bug_patterns(content, lines, analysis)
 
 # 코드 품질 이슈 찾기
 self._find_quality_issues(content, lines, analysis)
 
 except Exception as e:
            analysis["errors"].append({
                "type": "analysis_error",
                "message": str(e)
 })
 
 return analysis
 
 def _analyze_error_handling(self, tree: ast.AST, lines: List[str], analysis: Dict):
        """에러 처리 분석"""
 try_blocks = []
 
 for node in ast.walk(tree):
 if isinstance(node, ast.Try):
 try_blocks.append(node)
 
 for try_node in try_blocks:
 # except 절이 있는지 확인
 has_except = len(try_node.handlers) > 0
 has_else = try_node.else_ is not None
 has_finally = try_node.finalbody is not None
 
 if not has_except:
 # except 절이 없는 try 블록
 for stmt in try_node.body:
                    if hasattr(stmt, 'lineno'):
                        analysis["warnings"].append({
                            "type": "missing_except",
                            "line": stmt.lineno,
                            "message": "try 블록에 except 절이 없습니다"
 })
 
 # except Exception as e 패턴 확인
 for handler in try_node.handlers:
 if handler.type is None:
 # bare except
                    analysis["warnings"].append({
                        "type": "bare_except",
                        "line": handler.lineno if hasattr(handler, 'lineno') else 0,
                        "message": "bare except는 피해야 합니다"
 })
                elif isinstance(handler.type, ast.Name) and handler.type.id == 'Exception':
 # Exception만 잡는 경우 - 더 구체적인 예외 처리 필요
 if handler.name:
                        analysis["suggestions"].append({
                            "type": "specific_exception",
                            "line": handler.lineno if hasattr(handler, 'lineno') else 0,
                            "message": f"더 구체적인 예외 타입을 사용하세요: {handler.name.id if handler.name else 'unknown'}"
 })
 
 def _find_bug_patterns(self, content: str, lines: List[str], analysis: Dict):
        """버그 패턴 찾기"""
 # None 체크 없이 속성 접근
        pattern = r'(\w+)\.(\w+)(?!\s*is\s+None|\s*is\s+not\s+None)'
 
 # await 없이 async 함수 호출
        async_pattern = r'(?<!await\s)(\w+)\([^)]*\)\s*(?=\n|$)'
 
 # 비교 연산자 오류 (== 대신 = 사용)
        assignment_pattern = r'if\s+(\w+)\s*=\s*[^=]'
 
 for i, line in enumerate(lines, 1):
 # None 체크 없이 속성 접근
            if re.search(r'\.\w+\s*(?=\[|\.|\(|$)', line) and 'if' not in line and 'is not None' not in line:
                if 'self.' in line or 'bot.' in line:
                    analysis["warnings"].append({
                        "type": "potential_none_access",
                        "line": i,
                        "message": "None 체크 없이 속성 접근 가능성"
 })
 
 # 비교 연산자 오류
 if re.search(assignment_pattern, line):
                analysis["errors"].append({
                    "type": "assignment_in_condition",
                    "line": i,
                    "message": "조건문에서 = 대신 == 사용해야 합니다"
 })
 
 def _find_quality_issues(self, content: str, lines: List[str], analysis: Dict):
        """코드 품질 이슈 찾기"""
 for i, line in enumerate(lines, 1):
 # 긴 줄
 if len(line) > 120:
                analysis["suggestions"].append({
                    "type": "long_line",
                    "line": i,
                    "message": f"줄이 너무 깁니다 ({len(line)}자)"
 })
 
 # 하드코딩된 문자열
            if re.search(r'"[^"]{20,}"', line) or re.search(r"'[^']{20,}'", line):
                analysis["suggestions"].append({
                    "type": "hardcoded_string",
                    "line": i,
                    "message": "하드코딩된 문자열을 상수로 추출하세요"
 })
 
 # TODO, FIXME 주석
            if re.search(r'(TODO|FIXME|BUG|HACK|XXX)', line, re.IGNORECASE):
                analysis["warnings"].append({
                    "type": "todo_comment",
                    "line": i,
                    "message": f"처리 필요: {line.strip()[:50]}"
 })


class ErrorHandlerEnhancer:
    """에러 처리 강화기"""
 
 @staticmethod
 def enhance_error_handling(content: str, file_path: Path) -> Tuple[str, int]:
        """에러 처리를 3중으로 강화"""
 lines = content.splitlines()
 modified_lines = []
 fix_count = 0
 
 i = 0
 while i < len(lines):
 line = lines[i]
 modified_lines.append(line)
 
 # try 블록 찾기
            if re.match(r'^\s*try\s*:', line):
 indent = len(line) - len(line.lstrip())
                indent_str = ' ' * indent
 
 # except 절 확인
 j = i + 1
 has_except = False
 except_line_idx = -1
 
 while j < len(lines):
 next_line = lines[j]
 next_indent = len(next_line) - len(next_line.lstrip())
 
 if next_indent <= indent:
 break
 
                    if re.match(r'^\s*except\s', next_line):
 has_except = True
 except_line_idx = j
 break
 
 j += 1
 
 # except 절이 없거나 단순한 경우 강화
 if not has_except or (has_except and except_line_idx > 0):
 # 기존 except 확인
 if has_except:
 except_line = lines[except_line_idx]
 # 단순한 except인 경우 강화
                        if re.match(r'^\s*except\s*:\s*$', except_line) or \
                           re.match(r'^\s*except\s+Exception\s*:\s*$', except_line):
 # 3중 에러 처리 추가
                            enhanced = f"{indent_str}except Exception as e:\n"
                            enhanced += f"{indent_str}    # Level 1: Log error\n"
                            enhanced += f"{indent_str}    import traceback\n"
                            enhanced += f"{indent_str}    error_msg = f\"Error in {file_path.name}: {{str(e)}}\"\n"
                            enhanced += f"{indent_str}    print(f\"[ERROR] {{error_msg}}\")\n"
                            enhanced += f"{indent_str}    print(f\"[TRACEBACK] {{''.join(traceback.format_exc())}}\")\n"
                            enhanced += f"{indent_str}    \n"
                            enhanced += f"{indent_str}    # Level 2: Attempt recovery\n"
                            enhanced += f"{indent_str}    try:\n"
                            enhanced += f"{indent_str}        # Recovery logic here\n"
                            enhanced += f"{indent_str}        pass\n"
                            enhanced += f"{indent_str}    except Exception as recovery_error:\n"
                            enhanced += f"{indent_str}        # Level 3: Final fallback\n"
                            enhanced += f"{indent_str}        print(f\"[CRITICAL] Recovery failed: {{recovery_error}}\")\n"
                            enhanced += f"{indent_str}        # Continue execution if possible\n"
                            enhanced += f"{indent_str}        pass\n"
 
 # 기존 except 라인을 강화된 버전으로 교체
 for k in range(i + 1, except_line_idx + 1):
 if k == except_line_idx:
 modified_lines[-1] = enhanced
 else:
 modified_lines.append(lines[k])
 
 i = except_line_idx
 fix_count += 1
 continue
 
 i += 1
 
        return '\n'.join(modified_lines), fix_count


def main():
    """메인 함수"""
    print("=" * 70)
    print("코드 품질 개선 및 버그 수정")
    print("=" * 70)
 print()
 
 enhancer = CodeQualityEnhancer()
 error_enhancer = ErrorHandlerEnhancer()
 
 # 주요 파일 분석
 main_files = [
        "wicked_zerg_bot_pro.py",
        "production_manager.py",
        "combat_manager.py",
        "economy_manager.py",
        "intel_manager.py",
        "scouting_system.py",
        "queen_manager.py"
 ]
 
 all_issues = []
 total_fixes = 0
 
    print("파일 분석 중...")
 for main_file in main_files:
 file_path = PROJECT_ROOT / main_file
 if file_path.exists():
            print(f"  - {main_file}")
 analysis = enhancer.analyze_file(file_path)
 all_issues.append(analysis)
 
 # 에러 처리 강화
            if analysis.get("warnings") or analysis.get("errors"):
 try:
                    with open(file_path, 'r', encoding='utf-8') as f:
 content = f.read()
 
 enhanced_content, fix_count = error_enhancer.enhance_error_handling(content, file_path)
 
 if fix_count > 0:
 # 백업 생성
                        backup_path = file_path.with_suffix(file_path.suffix + '.bak')
                        with open(backup_path, 'w', encoding='utf-8') as f:
 f.write(content)
 
 # 수정된 내용 저장
                        with open(file_path, 'w', encoding='utf-8') as f:
 f.write(enhanced_content)
 
                        print(f"    ? 에러 처리 강화: {fix_count}개")
 total_fixes += fix_count
 except Exception as e:
                    print(f"    ? 에러 처리 강화 실패: {e}")
 
 print()
    print("=" * 70)
    print("분석 결과 요약")
    print("=" * 70)
 
    total_errors = sum(len(a.get("errors", [])) for a in all_issues)
    total_warnings = sum(len(a.get("warnings", [])) for a in all_issues)
    total_suggestions = sum(len(a.get("suggestions", [])) for a in all_issues)
 
    print(f"총 에러: {total_errors}개")
    print(f"총 경고: {total_warnings}개")
    print(f"총 제안: {total_suggestions}개")
    print(f"에러 처리 강화: {total_fixes}개")
 print()
 
 # 리포트 생성
 report = []
    report.append("# 코드 품질 개선 리포트\n\n")
    report.append(f"**생성 일시**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    report.append("---\n\n")
 
    report.append("## 요약\n\n")
    report.append(f"- **총 에러**: {total_errors}개\n")
    report.append(f"- **총 경고**: {total_warnings}개\n")
    report.append(f"- **총 제안**: {total_suggestions}개\n")
    report.append(f"- **에러 처리 강화**: {total_fixes}개\n\n")
 
 for analysis in all_issues:
        if analysis.get("errors") or analysis.get("warnings") or analysis.get("suggestions"):
            report.append(f"## `{analysis['file']}`\n\n")
 
            if analysis.get("errors"):
                report.append("### 에러\n\n")
                for error in analysis["errors"][:10]:
                    report.append(f"- 라인 {error['line']}: {error['message']}\n")
                report.append("\n")
 
            if analysis.get("warnings"):
                report.append("### 경고\n\n")
                for warning in analysis["warnings"][:10]:
                    report.append(f"- 라인 {warning['line']}: {warning['message']}\n")
                report.append("\n")
 
    report_path = PROJECT_ROOT / "CODE_QUALITY_IMPROVEMENT_REPORT.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(''.join(report))
 
    print(f"리포트 생성 완료: {report_path}")
 print()
    print("=" * 70)
    print("완료!")
    print("=" * 70)


if __name__ == "__main__":
 import time
 main()