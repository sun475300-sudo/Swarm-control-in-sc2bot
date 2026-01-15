# -*- coding: utf-8 -*-
"""
대규모 리팩토링 실행 도구

1. 중복 코드 제거
2. 파일 구조 재구성
3. 클래스 분리
4. 의존성 최적화
"""

import ast
import re

PROJECT_ROOT = Path(__file__).parent.parent


class DuplicateCodeExtractor:
    """중복 코드 추출기"""
 
 def __init__(self):
 self.duplicate_functions = []
 self.common_utilities = {}
 
 def analyze_duplicates(self, report_path: Path) -> List[Dict]:
        """REFACTORING_ANALYSIS_REPORT.md에서 중복 함수 분석"""
 duplicates = []
 
 if not report_path.exists():
            print(f"[WARNING] 리포트 파일이 없습니다: {report_path}")
 return duplicates
 
        with open(report_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 
 # 중복 함수 섹션 찾기
 in_duplicate_section = False
 current_function = None
 
 for line in content.splitlines():
            if '중복 함수' in line or 'Duplicate Functions' in line:
 in_duplicate_section = True
 continue
 
 if in_duplicate_section:
 # 함수 이름 패턴 찾기
                match = re.search(r'(\w+)\s*\(.*?\)', line)
 if match:
 func_name = match.group(1)
 # 파일 경로 찾기
                    file_match = re.search(r'(\w+\.py)', line)
 if file_match:
 file_name = file_match.group(1)
 duplicates.append({
                            "function": func_name,
                            "file": file_name,
                            "line": line
 })
 
 return duplicates
 
 def extract_to_utility(self, duplicates: List[Dict], output_dir: Path):
        """중복 함수를 공통 유틸리티로 추출"""
 output_dir.mkdir(parents=True, exist_ok=True)
 
 # 함수별로 그룹화
 func_groups = defaultdict(list)
 for dup in duplicates:
            func_groups[dup["function"]].append(dup)
 
 # 공통 유틸리티 파일 생성
        utility_file = output_dir / "common_utilities.py"
 
        with open(utility_file, 'w', encoding='utf-8') as f:
            f.write("# -*- coding: utf-8 -*-\n")
            f.write('"""\n')
            f.write("공통 유틸리티 함수\n")
            f.write("\n")
            f.write("중복 코드 제거를 위해 추출된 공통 함수들\n")
            f.write('"""\n\n')
 
 for func_name, occurrences in func_groups.items():
 if len(occurrences) > 1: # 2개 이상 중복된 경우만
                    f.write(f"def {func_name}(*args, **kwargs):\n")
                    f.write(f'    """공통 유틸리티 함수: {func_name}"""\n')
                    f.write(f"    # TODO: 구현 필요\n")
                    f.write(f"    pass\n\n")
 
        print(f"[INFO] 공통 유틸리티 파일 생성: {utility_file}")
 return utility_file


class FileStructureReorganizer:
    """파일 구조 재구성기"""
 
 def __init__(self):
 self.new_structure = {}
 
 def read_refactoring_plan(self, plan_path: Path) -> Dict:
        """LARGE_SCALE_REFACTORING_PLAN.md 읽기"""
 if not plan_path.exists():
            print(f"[WARNING] 리팩토링 계획 파일이 없습니다: {plan_path}")
 return {}
 
        with open(plan_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 
 # 파일 구조 섹션 찾기
 structure = {}
 in_structure_section = False
 
 for line in content.splitlines():
            if '파일 구조' in line or 'File Structure' in line:
 in_structure_section = True
 continue
 
            if in_structure_section and line.strip().startswith('-'):
 # 디렉토리 구조 파싱
                match = re.search(r'(\w+)/', line)
 if match:
 dir_name = match.group(1)
 if dir_name not in structure:
 structure[dir_name] = []
 
 return structure
 
 def reorganize_files(self, structure: Dict, backup_dir: Path):
        """파일 구조 재구성"""
 backup_dir.mkdir(parents=True, exist_ok=True)
 
 # 새 디렉토리 생성
 for dir_name in structure.keys():
 new_dir = PROJECT_ROOT / dir_name
 new_dir.mkdir(parents=True, exist_ok=True)
            print(f"[INFO] 디렉토리 생성: {new_dir}")
 
        print("[INFO] 파일 구조 재구성 준비 완료")


class ClassSplitter:
    """클래스 분리기"""
 
 def __init__(self):
 self.split_plans = {}
 
 def analyze_class(self, file_path: Path, class_name: str) -> Dict:
        """클래스 분석"""
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 
 tree = ast.parse(content)
 
 class_info = {
            "name": class_name,
            "methods": [],
            "attributes": [],
            "dependencies": []
 }
 
 for node in ast.walk(tree):
 if isinstance(node, ast.ClassDef) and node.name == class_name:
 for item in node.body:
 if isinstance(item, ast.FunctionDef):
                        class_info["methods"].append(item.name)
 elif isinstance(item, ast.Assign):
 for target in item.targets:
 if isinstance(target, ast.Name):
                                class_info["attributes"].append(target.id)
 
 return class_info
 
 def split_combat_manager(self, file_path: Path, output_dir: Path):
        """CombatManager 분리"""
        class_info = self.analyze_class(file_path, "CombatManager")
 
 # 기능별로 메서드 그룹화
 groups = {
            "micro": [],
            "macro": [],
            "targeting": [],
            "positioning": []
 }
 
        for method in class_info["methods"]:
            if any(keyword in method.lower() for keyword in ['micro', 'unit', 'attack']):
                groups["micro"].append(method)
            elif any(keyword in method.lower() for keyword in ['macro', 'army', 'composition']):
                groups["macro"].append(method)
            elif any(keyword in method.lower() for keyword in ['target', 'priority']):
                groups["targeting"].append(method)
            elif any(keyword in method.lower() for keyword in ['position', 'formation']):
                groups["positioning"].append(method)
 else:
                groups["micro"].append(method)  # 기본값
 
 output_dir.mkdir(parents=True, exist_ok=True)
 
 # 분리된 클래스 생성
 for group_name, methods in groups.items():
 if methods:
                new_file = output_dir / f"combat_{group_name}.py"
                with open(new_file, 'w', encoding='utf-8') as f:
                    f.write(f"# -*- coding: utf-8 -*-\n")
                    f.write(f'"""\n')
                    f.write(f"CombatManager {group_name} 기능\n")
                    f.write(f'"""\n\n')
                    f.write(f"class Combat{group_name.capitalize()}:\n")
                    f.write(f'    """{group_name} 관련 전투 기능"""\n\n')
 for method in methods:
                        f.write(f"    def {method}(self, *args, **kwargs):\n")
                        f.write(f"        # TODO: 구현 필요\n")
                        f.write(f"        pass\n\n")
 
                print(f"[INFO] 클래스 생성: {new_file} ({len(methods)}개 메서드)")
 
 return groups


class DependencyOptimizer:
    """의존성 최적화기"""
 
 def __init__(self):
 self.imports = {}
 self.circular_deps = []
 
 def analyze_imports(self, file_path: Path) -> Set[str]:
        """파일의 import 분석"""
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 
 tree = ast.parse(content)
 imports = set()
 
 for node in ast.walk(tree):
 if isinstance(node, ast.Import):
 for alias in node.names:
                    imports.add(alias.name.split('.')[0])
 elif isinstance(node, ast.ImportFrom):
 if node.module:
                    imports.add(node.module.split('.')[0])
 
 return imports
 
 def find_circular_dependencies(self, project_dir: Path) -> List[Tuple[str, str]]:
        """순환 의존성 찾기"""
        files = list(project_dir.glob("*.py"))
 import_graph = {}
 
 for file_path in files:
            if file_path.name.startswith('_') or file_path.name == 'common_utilities.py':
 continue
 
 module_name = file_path.stem
 imports = self.analyze_imports(file_path)
 import_graph[module_name] = imports
 
 # 순환 의존성 찾기 (간단한 DFS)
 circular = []
 visited = set()
 
 def dfs(node, path):
 if node in path:
 # 순환 발견
 cycle_start = path.index(node)
 cycle = path[cycle_start:] + [node]
 circular.append(tuple(cycle))
 return
 
 if node in visited:
 return
 
 visited.add(node)
 path.append(node)
 
 for neighbor in import_graph.get(node, []):
 if neighbor in import_graph:
 dfs(neighbor, path[:])
 
 path.pop()
 
 for node in import_graph:
 if node not in visited:
 dfs(node, [])
 
 return circular
 
 def create_common_utilities(self, output_dir: Path):
        """공통 유틸리티 모듈 생성"""
 output_dir.mkdir(parents=True, exist_ok=True)
 
        common_file = output_dir / "common_utilities.py"
 
        with open(common_file, 'w', encoding='utf-8') as f:
            f.write("# -*- coding: utf-8 -*-\n")
            f.write('"""\n')
            f.write("공통 유틸리티 모듈\n")
            f.write("\n")
            f.write("순환 의존성을 제거하기 위한 공통 함수들\n")
            f.write('"""\n\n')
            f.write("# 공통 유틸리티 함수들\n")
            f.write("# 순환 의존성을 제거하기 위해 여기에 공통 함수를 배치\n\n")
 
        print(f"[INFO] 공통 유틸리티 모듈 생성: {common_file}")


def main():
    """메인 함수"""
    print("=" * 70)
    print("대규모 리팩토링 실행")
    print("=" * 70)
 print()
 
 # 1. 중복 코드 제거
    print("[1/4] 중복 코드 제거 중...")
 duplicate_extractor = DuplicateCodeExtractor()
    report_path = PROJECT_ROOT / "REFACTORING_ANALYSIS_REPORT.md"
 duplicates = duplicate_extractor.analyze_duplicates(report_path)
 
 if duplicates:
        utils_dir = PROJECT_ROOT / "utils"
 utility_file = duplicate_extractor.extract_to_utility(duplicates, utils_dir)
        print(f"  - {len(duplicates)}개 중복 함수 발견")
        print(f"  - 공통 유틸리티 생성: {utility_file}")
 else:
        print("  - 중복 함수를 찾을 수 없습니다.")
 print()
 
 # 2. 파일 구조 재구성
    print("[2/4] 파일 구조 재구성 중...")
 reorganizer = FileStructureReorganizer()
    plan_path = PROJECT_ROOT / "LARGE_SCALE_REFACTORING_PLAN.md"
 structure = reorganizer.read_refactoring_plan(plan_path)
 
 if structure:
        backup_dir = PROJECT_ROOT / "backup_before_refactoring"
 reorganizer.reorganize_files(structure, backup_dir)
        print(f"  - {len(structure)}개 디렉토리 구조 준비")
 else:
        print("  - 리팩토링 계획을 찾을 수 없습니다.")
 print()
 
 # 3. 클래스 분리
    print("[3/4] 클래스 분리 중...")
 splitter = ClassSplitter()
 
 # CombatManager 분리
    combat_file = PROJECT_ROOT / "combat_manager.py"
 if combat_file.exists():
        combat_output = PROJECT_ROOT / "combat"
 groups = splitter.split_combat_manager(combat_file, combat_output)
        print(f"  - CombatManager 분리 완료: {len(groups)}개 그룹")
 
 # ReplayDownloader 분리 (파일이 있는 경우)
    replay_files = list(PROJECT_ROOT.glob("*replay*.py"))
 for replay_file in replay_files:
        if "download" in replay_file.name.lower():
            replay_output = PROJECT_ROOT / "replay"
 # ReplayDownloader 클래스 찾기 및 분리
            print(f"  - {replay_file.name} 분석 중...")
 print()
 
 # 4. 의존성 최적화
    print("[4/4] 의존성 최적화 중...")
 optimizer = DependencyOptimizer()
 circular = optimizer.find_circular_dependencies(PROJECT_ROOT)
 
 if circular:
        print(f"  - {len(circular)}개 순환 의존성 발견:")
 for cycle in circular[:5]: # 처음 5개만 출력
            print(f"    {' -> '.join(cycle)}")
 else:
        print("  - 순환 의존성을 찾을 수 없습니다.")
 
    utils_dir = PROJECT_ROOT / "utils"
 optimizer.create_common_utilities(utils_dir)
 print()
 
    print("=" * 70)
    print("대규모 리팩토링 완료!")
    print("=" * 70)
 print()
    print("다음 단계:")
    print("  1. 생성된 공통 유틸리티 함수 구현")
    print("  2. 파일 구조 재구성 적용")
    print("  3. 분리된 클래스 통합")
    print("  4. 순환 의존성 제거")


if __name__ == "__main__":
 main()