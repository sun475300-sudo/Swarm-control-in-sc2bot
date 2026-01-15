# -*- coding: utf-8 -*-
"""
종합 코드 품질 개선 도구

다음 작업들을 수행:
1. 중복 코드 제거
2. 사용하지 않는 import 정리
3. 코드 스타일 통일
4. 파일 구조 재구성 제안
5. 클래스 분리 및 통합 제안
6. 의존성 최적화
"""

import ast
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import json

PROJECT_ROOT = Path(__file__).parent.parent


class ComprehensiveCodeImprover:
    """종합 코드 개선기"""
 
 def __init__(self):
 self.unused_imports: Dict[str, List[str]] = {}
 self.duplicate_code: List[Dict] = []
 self.style_issues: Dict[str, List[str]] = {}
 self.class_refactoring_suggestions: List[Dict] = []
 self.dependency_issues: List[Dict] = []
 
 def find_unused_imports(self) -> Dict[str, List[str]]:
        """사용하지 않는 import 찾기"""
        print("사용하지 않는 import 찾는 중...")
 
 unused = {}
 
 for root, dirs, files in os.walk(PROJECT_ROOT):
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'node_modules', '.venv', 'venv', 'models'}]
 
 for file in files:
                if file.endswith('.py'):
 file_path = Path(root) / file
 try:
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 tree = ast.parse(content, filename=str(file_path))
 
 imports = []
 used_names = set()
 
 # Import 찾기
 for node in ast.walk(tree):
 if isinstance(node, ast.Import):
 for alias in node.names:
 imports.append(alias.name)
 elif isinstance(node, ast.ImportFrom):
 if node.module:
 if node.names:
 for alias in node.names:
                                            imports.append(f"{node.module}.{alias.name}")
 else:
 imports.append(node.module)
 
 # 사용된 이름 찾기
 if isinstance(node, ast.Name):
 used_names.add(node.id)
 elif isinstance(node, ast.Attribute):
 if isinstance(node.value, ast.Name):
 used_names.add(node.value.id)
 
 # 사용하지 않는 import 찾기
 unused_in_file = []
 for imp in imports:
                            base_name = imp.split('.')[0]
 if base_name not in used_names and imp not in used_names:
 # 표준 라이브러리는 제외 (간접 사용 가능)
                                if base_name not in ['os', 'sys', 'json', 'pathlib', 'typing', 'collections', 
                                                     'datetime', 'logging', 'subprocess', 're', 'ast']:
 unused_in_file.append(imp)
 
 if unused_in_file:
 rel_path = file_path.relative_to(PROJECT_ROOT)
 unused[str(rel_path)] = unused_in_file
 except Exception:
 continue
 
 self.unused_imports = unused
 return unused
 
 def find_duplicate_code_blocks(self, min_lines: int = 5) -> List[Dict]:
        """중복 코드 블록 찾기"""
        print("중복 코드 블록 찾는 중...")
 
 code_blocks: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
 
 for root, dirs, files in os.walk(PROJECT_ROOT):
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'node_modules', '.venv', 'venv', 'models'}]
 
 for file in files:
                if file.endswith('.py'):
 file_path = Path(root) / file
 try:
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 lines = f.readlines()
 
 # 코드 블록 추출
 for i in range(len(lines) - min_lines + 1):
                            block = ''.join(lines[i:i+min_lines]).strip()
 if len(block) > 30: # 최소 길이
 # 정규화 (공백, 주석 제거)
                                normalized = re.sub(r'\s+', ' ', block)
                                normalized = re.sub(r'#.*', '', normalized)
 if len(normalized) > 20:
 code_blocks[normalized].append((
 str(file_path.relative_to(PROJECT_ROOT)),
 i + 1
 ))
 except Exception:
 continue
 
 duplicates = []
 for block, occurrences in code_blocks.items():
 if len(occurrences) > 1:
 # 같은 파일 내 중복은 제외
 files = set(occ[0] for occ in occurrences)
 if len(files) > 1:
 duplicates.append({
                        "block_preview": block[:150] + "..." if len(block) > 150 else block,
                        "occurrences": occurrences,
                        "count": len(occurrences)
 })
 
        self.duplicate_code = sorted(duplicates, key=lambda x: x["count"], reverse=True)[:30]
 return self.duplicate_code
 
 def check_code_style(self) -> Dict[str, List[str]]:
        """코드 스타일 검사"""
        print("코드 스타일 검사 중...")
 
 style_issues = {}
 
 # PEP 8 기본 검사
 for root, dirs, files in os.walk(PROJECT_ROOT):
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'node_modules', '.venv', 'venv', 'models'}]
 
 for file in files:
                if file.endswith('.py'):
 file_path = Path(root) / file
 issues = []
 
 try:
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 lines = f.readlines()
 
 # 라인 길이 검사 (120자 초과)
 for i, line in enumerate(lines, 1):
 if len(line.rstrip()) > 120:
                                issues.append(f"Line {i}: Line too long ({len(line.rstrip())} characters)")
 
 # 들여쓰기 검사 (탭 사용)
                            if '\t' in line and not line.strip().startswith('#'):
                                issues.append(f"Line {i}: Tab character used (use spaces instead)")
 
 if issues:
 rel_path = file_path.relative_to(PROJECT_ROOT)
 style_issues[str(rel_path)] = issues
 except Exception:
 continue
 
 self.style_issues = style_issues
 return style_issues
 
 def analyze_class_structure(self) -> List[Dict]:
        """클래스 구조 분석 및 리팩토링 제안"""
        print("클래스 구조 분석 중...")
 
 suggestions = []
 
 for root, dirs, files in os.walk(PROJECT_ROOT):
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'node_modules', '.venv', 'venv', 'models'}]
 
 for file in files:
                if file.endswith('.py'):
 file_path = Path(root) / file
 try:
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 tree = ast.parse(content, filename=str(file_path))
 
 for node in ast.walk(tree):
 if isinstance(node, ast.ClassDef):
 methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
 
 # 큰 클래스 (메서드 20개 이상)
 if len(methods) > 20:
 rel_path = file_path.relative_to(PROJECT_ROOT)
 suggestions.append({
                                        "file": str(rel_path),
                                        "class": node.name,
                                        "line": node.lineno,
                                        "method_count": len(methods),
                                        "suggestion": "Consider splitting into smaller classes",
                                        "methods": [m.name for m in methods[:10]]  # 처음 10개만
 })
 except Exception:
 continue
 
 self.class_refactoring_suggestions = suggestions
 return suggestions
 
 def analyze_dependencies(self) -> List[Dict]:
        """의존성 분석 및 최적화 제안"""
        print("의존성 분석 중...")
 
 issues = []
 file_deps: Dict[str, Set[str]] = {}
 
 # 파일별 의존성 수집
 for root, dirs, files in os.walk(PROJECT_ROOT):
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'node_modules', '.venv', 'venv', 'models'}]
 
 for file in files:
                if file.endswith('.py'):
 file_path = Path(root) / file
 try:
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 tree = ast.parse(content, filename=str(file_path))
 
 deps = set()
 for node in ast.walk(tree):
 if isinstance(node, ast.ImportFrom):
                                if node.module and not node.module.startswith('.'):
                                    deps.add(node.module.split('.')[0])
 
 if deps:
 rel_path = file_path.relative_to(PROJECT_ROOT)
 file_deps[str(rel_path)] = deps
 except Exception:
 continue
 
 # 순환 의존성 찾기 (간단한 버전)
 # 너무 많은 의존성을 가진 파일 찾기
 for file, deps in file_deps.items():
 if len(deps) > 15: # 15개 이상의 외부 모듈 의존
 issues.append({
                    "file": file,
                    "issue": "Too many dependencies",
                    "dependency_count": len(deps),
                    "dependencies": list(deps)[:10],  # 처음 10개만
                    "suggestion": "Consider splitting into smaller modules"
 })
 
 self.dependency_issues = issues
 return issues
 
 def generate_improvement_report(self) -> str:
        """개선 리포트 생성"""
 report = []
        report.append("# 종합 코드 품질 개선 리포트\n\n")
        report.append("**생성 일시**: 2026-01-15\n")
        report.append("**목적**: 코드 품질 개선 및 대규모 리팩토링을 위한 종합 분석\n\n")
        report.append("---\n\n")
 
 # 사용하지 않는 import
        report.append("## 1. 사용하지 않는 Import 정리\n\n")
 if self.unused_imports:
            report.append(f"총 {len(self.unused_imports)}개 파일에서 사용하지 않는 import를 발견했습니다.\n\n")
 total_unused = sum(len(imps) for imps in self.unused_imports.values())
            report.append(f"**총 사용하지 않는 import**: {total_unused}개\n\n")
 
 for file, imps in list(self.unused_imports.items())[:20]: # 상위 20개
                report.append(f"### `{file}`\n\n")
 for imp in imps:
                    report.append(f"- `{imp}`\n")
                report.append("\n")
 else:
            report.append("사용하지 않는 import를 찾지 못했습니다.\n\n")
 
 # 중복 코드
        report.append("## 2. 중복 코드 블록\n\n")
 if self.duplicate_code:
            report.append(f"총 {len(self.duplicate_code)}개의 중복 코드 블록을 발견했습니다.\n\n")
 for dup in self.duplicate_code[:10]: # 상위 10개
                report.append(f"### 중복 횟수: {dup['count']}\n\n")
                report.append(f"**코드 미리보기**:\n```python\n{dup['block_preview']}\n```\n\n")
                report.append("**발견 위치**:\n")
                for file, line in dup['occurrences'][:5]:  # 처음 5개만
                    report.append(f"- `{file}:{line}`\n")
                report.append("\n")
 else:
            report.append("중복 코드 블록을 찾지 못했습니다.\n\n")
 
 # 코드 스타일
        report.append("## 3. 코드 스타일 이슈\n\n")
 if self.style_issues:
            report.append(f"총 {len(self.style_issues)}개 파일에서 스타일 이슈를 발견했습니다.\n\n")
 total_issues = sum(len(issues) for issues in self.style_issues.values())
            report.append(f"**총 스타일 이슈**: {total_issues}개\n\n")
 
 for file, issues in list(self.style_issues.items())[:10]: # 상위 10개
                report.append(f"### `{file}`\n\n")
 for issue in issues[:5]: # 처음 5개만
                    report.append(f"- {issue}\n")
                report.append("\n")
 else:
            report.append("코드 스타일 이슈를 찾지 못했습니다.\n\n")
 
 # 클래스 리팩토링 제안
        report.append("## 4. 클래스 리팩토링 제안\n\n")
 if self.class_refactoring_suggestions:
            report.append(f"총 {len(self.class_refactoring_suggestions)}개의 클래스 리팩토링 제안이 있습니다.\n\n")
 for sug in self.class_refactoring_suggestions:
                report.append(f"### `{sug['file']}:{sug['line']}` - `{sug['class']}`\n\n")
                report.append(f"- **메서드 수**: {sug['method_count']}개\n")
                report.append(f"- **제안**: {sug['suggestion']}\n")
                report.append(f"- **주요 메서드**: {', '.join(sug['methods'])}\n\n")
 else:
            report.append("클래스 리팩토링 제안이 없습니다.\n\n")
 
 # 의존성 이슈
        report.append("## 5. 의존성 최적화 제안\n\n")
 if self.dependency_issues:
            report.append(f"총 {len(self.dependency_issues)}개 파일에서 의존성 이슈를 발견했습니다.\n\n")
 for issue in self.dependency_issues:
                report.append(f"### `{issue['file']}`\n\n")
                report.append(f"- **의존성 수**: {issue['dependency_count']}개\n")
                report.append(f"- **제안**: {issue['suggestion']}\n")
                report.append(f"- **주요 의존성**: {', '.join(issue['dependencies'])}\n\n")
 else:
            report.append("의존성 이슈를 찾지 못했습니다.\n\n")
 
 # 개선 작업 제안
        report.append("---\n\n")
        report.append("## 개선 작업 제안\n\n")
        report.append("### 우선순위 1: 사용하지 않는 Import 제거\n\n")
        report.append("```bash\n")
        report.append("# 자동으로 제거 (주의: 검토 필요)\n")
        report.append("python tools/remove_unused_imports.py\n")
        report.append("```\n\n")
 
        report.append("### 우선순위 2: 중복 코드 제거\n\n")
        report.append("중복 코드 블록을 공통 함수로 추출하여 제거\n\n")
 
        report.append("### 우선순위 3: 코드 스타일 통일\n\n")
        report.append("```bash\n")
        report.append("# black 또는 autopep8 사용\n")
        report.append("black wicked_zerg_challenger/\n")
        report.append("# 또는\n")
        report.append("autopep8 --in-place --recursive wicked_zerg_challenger/\n")
        report.append("```\n\n")
 
        report.append("### 우선순위 4: 클래스 리팩토링\n\n")
        report.append("큰 클래스를 작은 클래스로 분리\n\n")
 
        report.append("### 우선순위 5: 의존성 최적화\n\n")
        report.append("의존성이 많은 파일을 작은 모듈로 분리\n\n")
 
        return ''.join(report)


def main():
    """메인 함수"""
    print("=" * 70)
    print("종합 코드 품질 개선 분석")
    print("=" * 70)
 print()
 
 improver = ComprehensiveCodeImprover()
 
 # 각 분석 수행
 unused_imports = improver.find_unused_imports()
    print(f"  - 사용하지 않는 import: {len(unused_imports)}개 파일")
 
 duplicate_code = improver.find_duplicate_code_blocks()
    print(f"  - 중복 코드 블록: {len(duplicate_code)}개")
 
 style_issues = improver.check_code_style()
    print(f"  - 스타일 이슈: {len(style_issues)}개 파일")
 
 class_suggestions = improver.analyze_class_structure()
    print(f"  - 클래스 리팩토링 제안: {len(class_suggestions)}개")
 
 dependency_issues = improver.analyze_dependencies()
    print(f"  - 의존성 이슈: {len(dependency_issues)}개 파일")
 print()
 
 # 리포트 생성
    print("리포트 생성 중...")
 report = improver.generate_improvement_report()
 
    report_path = PROJECT_ROOT / "COMPREHENSIVE_CODE_IMPROVEMENT_REPORT.md"
    with open(report_path, 'w', encoding='utf-8') as f:
 f.write(report)
 
    print(f"리포트가 생성되었습니다: {report_path}")
 print()
    print("=" * 70)
    print("분석 완료!")
    print("=" * 70)


if __name__ == "__main__":
 main()