# -*- coding: utf-8 -*-
"""
대규모 리팩토링 및 코드 품질 개선 분석 도구

클로드 코드와 함께 사용하기 위한 분석 스크립트
"""

import ast
import os
from collections import defaultdict
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).parent.parent


class RefactoringAnalyzer:
    """리팩토링 분석기"""
 
 def __init__(self):
 self.duplicate_functions: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
 self.long_functions: List[Tuple[str, int, int]] = [] # (file, line, length)
 self.complex_functions: List[Tuple[str, int, int]] = [] # (file, line, complexity)
 self.duplicate_code_blocks: List[Tuple[str, str, int, int]] = [] # (file1, file2, line1, line2)
 self.large_classes: List[Tuple[str, int, int]] = [] # (file, line, method_count)
 self.unused_imports: Dict[str, List[str]] = {}
 
 def analyze_file(self, file_path: Path) -> Dict:
        """파일 분석"""
 try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 tree = ast.parse(content, filename=str(file_path))
 except Exception as e:
            return {"error": str(e)}
 
 result = {
            "file": str(file_path.relative_to(PROJECT_ROOT)),
            "functions": [],
            "classes": [],
            "imports": [],
            "line_count": len(content.splitlines()),
            "complexity": 0
 }
 
 for node in ast.walk(tree):
 if isinstance(node, ast.FunctionDef):
 func_info = self._analyze_function(node, content)
                result["functions"].append(func_info)
                result["complexity"] += func_info["complexity"]
 
 elif isinstance(node, ast.ClassDef):
 class_info = self._analyze_class(node, content)
                result["classes"].append(class_info)
 
 elif isinstance(node, (ast.Import, ast.ImportFrom)):
 import_info = self._analyze_import(node)
                result["imports"].append(import_info)
 
 return result
 
 def _analyze_function(self, node: ast.FunctionDef, content: str) -> Dict:
        """함수 분석"""
 start_line = node.lineno
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
 lines = content.splitlines()[start_line-1:end_line]
 length = len(lines)
 
 # 복잡도 계산 (순환 복잡도 간단 버전)
 complexity = 1 # 기본 복잡도
 for child in ast.walk(node):
 if isinstance(child, (ast.If, ast.While, ast.For, ast.Try, ast.With)):
 complexity += 1
 elif isinstance(child, ast.BoolOp):
 complexity += len(child.values) - 1
 
 return {
            "name": node.name,
            "line": start_line,
            "length": length,
            "complexity": complexity,
            "args": len(node.args.args),
            "decorators": [ast.unparse(d) for d in node.decorator_list] if hasattr(ast, 'unparse') else []
 }
 
 def _analyze_class(self, node: ast.ClassDef, content: str) -> Dict:
        """클래스 분석"""
 methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
 
 return {
            "name": node.name,
            "line": node.lineno,
            "method_count": len(methods),
            "methods": [m.name for m in methods]
 }
 
 def _analyze_import(self, node: ast.Import) -> Dict:
        """Import 분석"""
 if isinstance(node, ast.Import):
 return {
                "type": "import",
                "names": [alias.name for alias in node.names]
 }
 else: # ImportFrom
 return {
                "type": "from",
                "module": node.module or "",
                "names": [alias.name for alias in node.names]
 }
 
 def find_duplicate_functions(self, all_results: List[Dict]) -> List[Dict]:
        """중복 함수 찾기"""
 function_signatures: Dict[str, List[Tuple[str, str, int]]] = defaultdict(list)
 
 for result in all_results:
            if "error" in result:
 continue
            for func in result["functions"]:
 # 함수 시그니처 생성 (이름 + 인자 수)
                sig = f"{func['name']}({func['args']} args)"
 function_signatures[sig].append((
                    result["file"],
                    func["name"],
                    func["line"]
 ))
 
 duplicates = []
 for sig, occurrences in function_signatures.items():
 if len(occurrences) > 1:
 duplicates.append({
                    "signature": sig,
                    "occurrences": occurrences,
                    "count": len(occurrences)
 })
 
        return sorted(duplicates, key=lambda x: x["count"], reverse=True)
 
 def find_long_functions(self, all_results: List[Dict], threshold: int = 100) -> List[Dict]:
        """긴 함수 찾기"""
 long_funcs = []
 for result in all_results:
            if "error" in result:
 continue
            for func in result["functions"]:
                if func["length"] > threshold:
 long_funcs.append({
                        "file": result["file"],
                        "function": func["name"],
                        "line": func["line"],
                        "length": func["length"]
 })
 
        return sorted(long_funcs, key=lambda x: x["length"], reverse=True)
 
 def find_complex_functions(self, all_results: List[Dict], threshold: int = 10) -> List[Dict]:
        """복잡한 함수 찾기"""
 complex_funcs = []
 for result in all_results:
            if "error" in result:
 continue
            for func in result["functions"]:
                if func["complexity"] > threshold:
 complex_funcs.append({
                        "file": result["file"],
                        "function": func["name"],
                        "line": func["line"],
                        "complexity": func["complexity"]
 })
 
        return sorted(complex_funcs, key=lambda x: x["complexity"], reverse=True)
 
 def find_large_classes(self, all_results: List[Dict], threshold: int = 20) -> List[Dict]:
        """큰 클래스 찾기"""
 large_classes = []
 for result in all_results:
            if "error" in result:
 continue
            for cls in result["classes"]:
                if cls["method_count"] > threshold:
 large_classes.append({
                        "file": result["file"],
                        "class": cls["name"],
                        "line": cls["line"],
                        "method_count": cls["method_count"]
 })
 
        return sorted(large_classes, key=lambda x: x["method_count"], reverse=True)
 
 def find_duplicate_code_blocks(self, file_paths: List[Path], min_lines: int = 5) -> List[Dict]:
        """중복 코드 블록 찾기 (간단한 버전)"""
 code_blocks: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
 
 for file_path in file_paths:
 try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 lines = f.readlines()
 
 # 간단한 해시 기반 중복 검사
 for i in range(len(lines) - min_lines + 1):
                    block = ''.join(lines[i:i+min_lines]).strip()
 if len(block) > 20: # 최소 길이
 # 정규화 (공백 제거)
                        normalized = re.sub(r'\s+', ' ', block)
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
                        "block_preview": block[:100] + "..." if len(block) > 100 else block,
                        "occurrences": occurrences,
                        "count": len(occurrences)
 })
 
        return sorted(duplicates, key=lambda x: x["count"], reverse=True)[:20]  # 상위 20개만


def find_all_python_files() -> List[Path]:
    """모든 Python 파일 찾기"""
 python_files = []
    exclude_dirs = {'__pycache__', '.git', 'node_modules', '.venv', 'venv', 'models'}
 
 for root, dirs, files in os.walk(PROJECT_ROOT):
 # 제외할 디렉토리 제거
 dirs[:] = [d for d in dirs if d not in exclude_dirs]
 
 for file in files:
            if file.endswith('.py'):
 python_files.append(Path(root) / file)
 
 return python_files


def generate_refactoring_report():
    """리팩토링 리포트 생성"""
    print("=" * 70)
    print("대규모 리팩토링 및 코드 품질 개선 분석")
    print("=" * 70)
 print()
 
 analyzer = RefactoringAnalyzer()
 
    print("파일 검색 중...")
 python_files = find_all_python_files()
    print(f"총 {len(python_files)}개의 Python 파일을 찾았습니다.")
 print()
 
    print("파일 분석 중...")
 all_results = []
 for i, file_path in enumerate(python_files, 1):
 if i % 10 == 0:
            print(f"  진행 중: {i}/{len(python_files)}")
 result = analyzer.analyze_file(file_path)
 all_results.append(result)
    print("분석 완료!")
 print()
 
 # 중복 함수 찾기
    print("중복 함수 찾는 중...")
 duplicate_functions = analyzer.find_duplicate_functions(all_results)
 
 # 긴 함수 찾기
    print("긴 함수 찾는 중...")
 long_functions = analyzer.find_long_functions(all_results)
 
 # 복잡한 함수 찾기
    print("복잡한 함수 찾는 중...")
 complex_functions = analyzer.find_complex_functions(all_results)
 
 # 큰 클래스 찾기
    print("큰 클래스 찾는 중...")
 large_classes = analyzer.find_large_classes(all_results)
 
 # 중복 코드 블록 찾기
    print("중복 코드 블록 찾는 중...")
 duplicate_blocks = analyzer.find_duplicate_code_blocks(python_files)
 
 # 리포트 생성
    report_path = PROJECT_ROOT / "REFACTORING_ANALYSIS_REPORT.md"
 
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# 리팩토링 분석 리포트\n\n")
        f.write("**생성 일시**: 2026-01-15\n")
        f.write("**목적**: 대규모 리팩토링 및 코드 품질 개선을 위한 분석\n\n")
        f.write("---\n\n")
 
 # 중복 함수
        f.write("## 1. 중복 함수 (리팩토링 우선순위: 높음)\n\n")
 if duplicate_functions:
            f.write(f"총 {len(duplicate_functions)}개의 중복 함수 패턴을 발견했습니다.\n\n")
 for dup in duplicate_functions[:20]: # 상위 20개
                f.write(f"### {dup['signature']} ({dup['count']}회)\n\n")
                for file, func, line in dup['occurrences']:
                    f.write(f"- `{file}:{line}` - `{func}`\n")
                f.write("\n")
 else:
            f.write("중복 함수를 찾지 못했습니다.\n\n")
 
 # 긴 함수
        f.write("## 2. 긴 함수 (100줄 이상, 리팩토링 권장)\n\n")
 if long_functions:
            f.write(f"총 {len(long_functions)}개의 긴 함수를 발견했습니다.\n\n")
 for func in long_functions[:20]: # 상위 20개
                f.write(f"- `{func['file']}:{func['line']}` - `{func['function']}` ({func['length']}줄)\n")
            f.write("\n")
 else:
            f.write("긴 함수를 찾지 못했습니다.\n\n")
 
 # 복잡한 함수
        f.write("## 3. 복잡한 함수 (순환 복잡도 10 이상, 리팩토링 권장)\n\n")
 if complex_functions:
            f.write(f"총 {len(complex_functions)}개의 복잡한 함수를 발견했습니다.\n\n")
 for func in complex_functions[:20]: # 상위 20개
                f.write(f"- `{func['file']}:{func['line']}` - `{func['function']}` (복잡도: {func['complexity']})\n")
            f.write("\n")
 else:
            f.write("복잡한 함수를 찾지 못했습니다.\n\n")
 
 # 큰 클래스
        f.write("## 4. 큰 클래스 (메서드 20개 이상, 리팩토링 권장)\n\n")
 if large_classes:
            f.write(f"총 {len(large_classes)}개의 큰 클래스를 발견했습니다.\n\n")
 for cls in large_classes[:10]: # 상위 10개
                f.write(f"- `{cls['file']}:{cls['line']}` - `{cls['class']}` ({cls['method_count']}개 메서드)\n")
            f.write("\n")
 else:
            f.write("큰 클래스를 찾지 못했습니다.\n\n")
 
 # 중복 코드 블록
        f.write("## 5. 중복 코드 블록 (5줄 이상, 리팩토링 권장)\n\n")
 if duplicate_blocks:
            f.write(f"총 {len(duplicate_blocks)}개의 중복 코드 블록을 발견했습니다.\n\n")
 for block in duplicate_blocks[:10]: # 상위 10개
                f.write(f"### 중복 횟수: {block['count']}\n\n")
                f.write(f"**코드 미리보기**:\n```python\n{block['block_preview']}\n```\n\n")
                f.write("**발견 위치**:\n")
                for file, line in block['occurrences']:
                    f.write(f"- `{file}:{line}`\n")
                f.write("\n")
 else:
            f.write("중복 코드 블록을 찾지 못했습니다.\n\n")
 
 # 클로드 코드 활용 제안
        f.write("---\n\n")
        f.write("## 클로드 코드 활용 제안\n\n")
        f.write("다음 작업들은 클로드 코드를 활용하여 효율적으로 수행할 수 있습니다:\n\n")
        f.write("1. **중복 함수 통합**: 중복된 함수들을 공통 유틸리티로 추출\n")
        f.write("2. **긴 함수 분리**: 긴 함수를 작은 함수로 분리\n")
        f.write("3. **복잡한 함수 단순화**: 복잡한 로직을 더 읽기 쉽게 리팩토링\n")
        f.write("4. **큰 클래스 분리**: 큰 클래스를 더 작은 클래스로 분리\n")
        f.write("5. **중복 코드 제거**: 중복 코드 블록을 공통 함수로 추출\n\n")
 
    print(f"\n리포트가 생성되었습니다: {report_path}")
    print(f"\n발견된 항목:")
    print(f"  - 중복 함수: {len(duplicate_functions)}개")
    print(f"  - 긴 함수: {len(long_functions)}개")
    print(f"  - 복잡한 함수: {len(complex_functions)}개")
    print(f"  - 큰 클래스: {len(large_classes)}개")
    print(f"  - 중복 코드 블록: {len(duplicate_blocks)}개")


if __name__ == "__main__":
 generate_refactoring_report()