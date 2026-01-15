# -*- coding: utf-8 -*-
"""
클로드 코드를 위한 프로젝트 전체 분석 도구

클로드 코드가 프로젝트를 이해하고 작업할 수 있도록 
프로젝트 구조, 의존성, 실행 방법 등을 종합적으로 분석합니다.
"""

import os
import ast
import json
from pathlib import Path
from collections import defaultdict
import subprocess

PROJECT_ROOT = Path(__file__).parent.parent


class ClaudeCodeProjectAnalyzer:
    """클로드 코드를 위한 프로젝트 분석기"""
 
 def __init__(self):
 self.project_structure: Dict = {}
 self.dependencies: Dict[str, List[str]] = defaultdict(list)
 self.entry_points: List[Dict] = []
 self.test_files: List[str] = []
 self.config_files: List[str] = []
 self.documentation_files: List[str] = []
 
 def analyze_project_structure(self) -> Dict:
        """프로젝트 구조 분석"""
 structure = {
            "root": str(PROJECT_ROOT),
            "directories": [],
            "python_files": [],
            "config_files": [],
            "documentation_files": [],
            "test_files": [],
            "entry_points": []
 }
 
        exclude_dirs = {'__pycache__', '.git', 'node_modules', '.venv', 'venv', 'models', '.pytest_cache'}
 
 for root, dirs, files in os.walk(PROJECT_ROOT):
 # 제외할 디렉토리 제거
 dirs[:] = [d for d in dirs if d not in exclude_dirs]
 
 rel_root = Path(root).relative_to(PROJECT_ROOT)
 
 # 디렉토리 정보
            if rel_root != Path('.'):
                structure["directories"].append(str(rel_root))
 
 # 파일 정보
 for file in files:
 file_path = Path(root) / file
 rel_path = file_path.relative_to(PROJECT_ROOT)
 
                if file.endswith('.py'):
                    structure["python_files"].append(str(rel_path))
                    if 'test' in file.lower() or 'test' in str(rel_path):
                        structure["test_files"].append(str(rel_path))
 
                elif file.endswith(('.json', '.yaml', '.yml', '.toml', '.ini', '.cfg')):
                    structure["config_files"].append(str(rel_path))
 
                elif file.endswith(('.md', '.txt', '.rst')):
                    structure["documentation_files"].append(str(rel_path))
 
 return structure
 
 def analyze_dependencies(self) -> Dict[str, List[str]]:
        """의존성 분석"""
 dependencies = defaultdict(list)
 
 for root, dirs, files in os.walk(PROJECT_ROOT):
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'node_modules', '.venv', 'venv'}]
 
 for file in files:
                if file.endswith('.py'):
 file_path = Path(root) / file
 try:
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 tree = ast.parse(content, filename=str(file_path))
 
 imports = []
 for node in ast.walk(tree):
 if isinstance(node, ast.Import):
 for alias in node.names:
 imports.append(alias.name)
 elif isinstance(node, ast.ImportFrom):
 if node.module:
 imports.append(node.module)
 
 if imports:
 rel_path = file_path.relative_to(PROJECT_ROOT)
 dependencies[str(rel_path)] = imports
 except Exception:
 continue
 
 return dict(dependencies)
 
 def find_entry_points(self) -> List[Dict]:
        """진입점 찾기"""
 entry_points = []
 
 # 배치 파일에서 진입점 찾기
        bat_dir = PROJECT_ROOT / "bat"
 if bat_dir.exists():
            for bat_file in bat_dir.glob("*.bat"):
 try:
                    with open(bat_file, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 # python 명령어 찾기
                        if 'python' in content.lower():
 entry_points.append({
                                "type": "batch",
                                "file": str(bat_file.relative_to(PROJECT_ROOT)),
                                "description": self._extract_batch_description(content)
 })
 except Exception:
 continue
 
 # 주요 Python 파일 찾기
 main_files = [
            "run.py",
            "run_with_training.py",
            "wicked_zerg_bot_pro.py",
            "main_integrated.py"
 ]
 
 for main_file in main_files:
 file_path = PROJECT_ROOT / main_file
 if file_path.exists():
 entry_points.append({
                    "type": "python",
                    "file": main_file,
                    "description": self._extract_file_description(file_path)
 })
 
 return entry_points
 
 def _extract_batch_description(self, content: str) -> str:
        """배치 파일에서 설명 추출"""
        lines = content.split('\n')
 for line in lines[:10]:
            if line.strip().startswith('REM') or line.strip().startswith('::'):
                desc = line.replace('REM', '').replace('::', '').strip()
 if desc:
 return desc
        return "No description"
 
 def _extract_file_description(self, file_path: Path) -> str:
        """파일에서 설명 추출"""
 try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 lines = f.readlines()[:20]
 for i, line in enumerate(lines):
                    if '"""' in line or "'''" in line:
 # Docstring 찾기
 if i + 1 < len(lines):
 return lines[i + 1].strip()
 except Exception:
 pass
        return "No description"
 
 def analyze_test_coverage(self) -> Dict:
        """테스트 커버리지 분석"""
 test_info = {
            "test_files": [],
            "test_functions": [],
            "coverage_estimate": 0
 }
 
 for root, dirs, files in os.walk(PROJECT_ROOT):
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'node_modules', '.venv', 'venv'}]
 
 for file in files:
                if 'test' in file.lower() and file.endswith('.py'):
 file_path = Path(root) / file
 rel_path = file_path.relative_to(PROJECT_ROOT)
                    test_info["test_files"].append(str(rel_path))
 
 try:
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 tree = ast.parse(content, filename=str(file_path))
 
 for node in ast.walk(tree):
 if isinstance(node, ast.FunctionDef):
                                if node.name.startswith('test_'):
                                    test_info["test_functions"].append({
                                        "file": str(rel_path),
                                        "function": node.name,
                                        "line": node.lineno
 })
 except Exception:
 continue
 
 return test_info
 
 def generate_claude_code_instructions(self) -> str:
        """클로드 코드를 위한 지시사항 생성"""
 instructions = []
        instructions.append("# 클로드 코드를 위한 프로젝트 분석 리포트\n\n")
        instructions.append("**생성 일시**: 2026-01-15\n")
        instructions.append("**목적**: 클로드 코드가 프로젝트를 이해하고 작업할 수 있도록 종합 분석\n\n")
        instructions.append("---\n\n")
 
 # 프로젝트 구조
        instructions.append("## 1. 프로젝트 구조\n\n")
 structure = self.analyze_project_structure()
        instructions.append(f"- **루트 디렉토리**: `{structure['root']}`\n")
        instructions.append(f"- **Python 파일**: {len(structure['python_files'])}개\n")
        instructions.append(f"- **설정 파일**: {len(structure['config_files'])}개\n")
        instructions.append(f"- **문서 파일**: {len(structure['documentation_files'])}개\n")
        instructions.append(f"- **테스트 파일**: {len(structure['test_files'])}개\n\n")
 
 # 주요 디렉토리
        instructions.append("### 주요 디렉토리\n\n")
        main_dirs = ['bat', 'tools', 'monitoring', 'local_training', '설명서']
 for dir_name in main_dirs:
            if dir_name in structure['directories']:
                instructions.append(f"- `{dir_name}/` - {self._get_directory_description(dir_name)}\n")
        instructions.append("\n")
 
 # 진입점
        instructions.append("## 2. 진입점 (Entry Points)\n\n")
 entry_points = self.find_entry_points()
 for ep in entry_points[:10]: # 상위 10개
            instructions.append(f"### `{ep['file']}` ({ep['type']})\n\n")
            instructions.append(f"{ep['description']}\n\n")
        instructions.append("\n")
 
 # 의존성
        instructions.append("## 3. 주요 의존성\n\n")
 dependencies = self.analyze_dependencies()
 external_deps = set()
 for file_deps in dependencies.values():
 for dep in file_deps:
                if '.' in dep and not dep.startswith('.'):
                    external_deps.add(dep.split('.')[0])
 
        instructions.append("### 외부 라이브러리\n\n")
 for dep in sorted(external_deps)[:20]: # 상위 20개
            instructions.append(f"- `{dep}`\n")
        instructions.append("\n")
 
 # 테스트 정보
        instructions.append("## 4. 테스트 정보\n\n")
 test_info = self.analyze_test_coverage()
        instructions.append(f"- **테스트 파일**: {len(test_info['test_files'])}개\n")
        instructions.append(f"- **테스트 함수**: {len(test_info['test_functions'])}개\n\n")
 
 # 실행 방법
        instructions.append("## 5. 실행 방법\n\n")
        instructions.append("### 훈련 실행\n\n")
        instructions.append("```bash\n")
        instructions.append("cd wicked_zerg_challenger\n")
        instructions.append("bat\\start_model_training.bat\n")
        instructions.append("```\n\n")
 
        instructions.append("### 리팩토링 분석\n\n")
        instructions.append("```bash\n")
        instructions.append("cd wicked_zerg_challenger\n")
        instructions.append("bat\\run_refactoring_analysis.bat\n")
        instructions.append("```\n\n")
 
 # 클로드 코드 작업 제안
        instructions.append("---\n\n")
        instructions.append("## 클로드 코드 작업 제안\n\n")
        instructions.append("### 1. 대규모 코드베이스 전체 분석\n\n")
        instructions.append("프로젝트 전체를 분석하여:\n")
        instructions.append("- 코드 품질 개선 포인트 발견\n")
        instructions.append("- 아키텍처 패턴 분석\n")
        instructions.append("- 성능 병목 지점 식별\n\n")
 
        instructions.append("### 2. 자율적인 실행 및 테스트\n\n")
        instructions.append("다음 작업들을 자동으로 수행:\n")
        instructions.append("- 리팩토링 후 자동 테스트 실행\n")
        instructions.append("- 코드 변경 사항 검증\n")
        instructions.append("- 성능 벤치마크 실행\n\n")
 
        instructions.append("### 3. 터미널 직접 제어\n\n")
        instructions.append("터미널을 통해:\n")
        instructions.append("- 파일 생성/수정\n")
        instructions.append("- 명령어 실행\n")
        instructions.append("- 배치 작업 수행\n\n")
 
        return ''.join(instructions)
 
 def _get_directory_description(self, dir_name: str) -> str:
        """디렉토리 설명"""
 descriptions = {
            'bat': '배치 파일 (자동화 스크립트)',
            'tools': '유틸리티 도구',
            'monitoring': '모니터링 시스템',
            'local_training': '로컬 훈련 스크립트',
            '설명서': '프로젝트 문서'
 }
        return descriptions.get(dir_name, '기타 파일')


def main():
    """메인 함수"""
    print("=" * 70)
    print("클로드 코드를 위한 프로젝트 전체 분석")
    print("=" * 70)
 print()
 
 analyzer = ClaudeCodeProjectAnalyzer()
 
    print("프로젝트 구조 분석 중...")
 structure = analyzer.analyze_project_structure()
    print(f"  - Python 파일: {len(structure['python_files'])}개")
    print(f"  - 설정 파일: {len(structure['config_files'])}개")
    print(f"  - 문서 파일: {len(structure['documentation_files'])}개")
 print()
 
    print("의존성 분석 중...")
 dependencies = analyzer.analyze_dependencies()
    print(f"  - 분석된 파일: {len(dependencies)}개")
 print()
 
    print("진입점 찾는 중...")
 entry_points = analyzer.find_entry_points()
    print(f"  - 진입점: {len(entry_points)}개")
 print()
 
    print("테스트 정보 분석 중...")
 test_info = analyzer.analyze_test_coverage()
    print(f"  - 테스트 파일: {len(test_info['test_files'])}개")
    print(f"  - 테스트 함수: {len(test_info['test_functions'])}개")
 print()
 
    print("클로드 코드 지시사항 생성 중...")
 instructions = analyzer.generate_claude_code_instructions()
 
 # 리포트 저장
    report_path = PROJECT_ROOT / "CLAUDE_CODE_PROJECT_ANALYSIS.md"
    with open(report_path, 'w', encoding='utf-8') as f:
 f.write(instructions)
 
    print(f"리포트가 생성되었습니다: {report_path}")
 print()
    print("=" * 70)
    print("분석 완료!")
    print("=" * 70)


if __name__ == "__main__":
 main()