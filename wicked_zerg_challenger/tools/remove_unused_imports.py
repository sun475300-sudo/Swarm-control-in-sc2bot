# -*- coding: utf-8 -*-
"""
사용하지 않는 import 자동 제거 도구

주의: 자동 제거는 위험할 수 있으므로 백업 후 사용하세요.
"""

import ast
import os
from pathlib import Path
import shutil

PROJECT_ROOT = Path(__file__).parent.parent


def find_unused_imports_in_file(file_path: Path) -> List[str]:
    """파일에서 사용하지 않는 import 찾기"""
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
                    imports.append(('import', alias.name, node.lineno))
 elif isinstance(node, ast.ImportFrom):
 if node.module:
 if node.names:
 for alias in node.names:
                            imports.append(('from', f"{node.module}.{alias.name}", node.lineno, alias.name))
 else:
                        imports.append(('from', node.module, node.lineno))
 
 # 사용된 이름 찾기
 if isinstance(node, ast.Name):
 used_names.add(node.id)
 elif isinstance(node, ast.Attribute):
 if isinstance(node.value, ast.Name):
 used_names.add(node.value.id)
 
 # 사용하지 않는 import 찾기
 unused = []
 for imp in imports:
            if imp[0] == 'import':
                base_name = imp[1].split('.')[0]
 if base_name not in used_names and imp[1] not in used_names:
 # 표준 라이브러리는 제외
                    if base_name not in ['os', 'sys', 'json', 'pathlib', 'typing', 'collections', 
                                         'datetime', 'logging', 'subprocess', 're', 'ast']:
 unused.append(imp)
            elif imp[0] == 'from':
 if len(imp) > 3:
 # from module import name
 if imp[3] not in used_names:
 unused.append(imp)
 
 return unused
 except Exception as e:
        print(f"[ERROR] {file_path}: {e}")
 return []


def remove_unused_imports(file_path: Path, unused_imports: List, dry_run: bool = True) -> bool:
    """사용하지 않는 import 제거"""
 try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 lines = f.readlines()
 
 # 제거할 라인 번호 수집
 lines_to_remove = set()
 for imp in unused_imports:
 lines_to_remove.add(imp[2] - 1) # 0-based index
 
 if not lines_to_remove:
 return False
 
 if dry_run:
            print(f"[DRY RUN] {file_path}: {len(lines_to_remove)}개 import 제거 예정")
 return True
 
 # 백업 생성
        backup_path = file_path.with_suffix(file_path.suffix + '.bak')
 shutil.copy2(file_path, backup_path)
 
 # 라인 제거
 new_lines = [line for i, line in enumerate(lines) if i not in lines_to_remove]
 
 # 파일 쓰기
        with open(file_path, 'w', encoding='utf-8', errors='replace') as f:
 f.writelines(new_lines)
 
        print(f"[REMOVED] {file_path}: {len(lines_to_remove)}개 import 제거 완료")
 return True
 except Exception as e:
        print(f"[ERROR] {file_path}: {e}")
 return False


def main():
    """메인 함수"""
 import argparse
 
    parser = argparse.ArgumentParser(description="사용하지 않는 import 제거")
    parser.add_argument("--dry-run", action="store_true", help="실제 제거하지 않고 미리보기만")
    parser.add_argument("--file", help="특정 파일만 처리")
 
 args = parser.parse_args()
 
    print("=" * 70)
    print("사용하지 않는 Import 제거 도구")
    print("=" * 70)
 print()
 
 if args.dry_run:
        print("[DRY RUN 모드] 실제로 제거하지 않습니다.")
 else:
        print("[주의] 실제로 import를 제거합니다. 백업이 생성됩니다.")
        response = input("계속하시겠습니까? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("취소되었습니다.")
 return
 
 print()
 
 files_to_process = []
 if args.file:
 file_path = PROJECT_ROOT / args.file
 if file_path.exists():
 files_to_process = [file_path]
 else:
            print(f"[ERROR] 파일을 찾을 수 없습니다: {args.file}")
 return
 else:
 # 모든 Python 파일 찾기
 for root, dirs, files in os.walk(PROJECT_ROOT):
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'node_modules', '.venv', 'venv', 'models'}]
 for file in files:
                if file.endswith('.py'):
 files_to_process.append(Path(root) / file)
 
    print(f"총 {len(files_to_process)}개 파일을 분석합니다...")
 print()
 
 total_removed = 0
 for file_path in files_to_process:
 unused = find_unused_imports_in_file(file_path)
 if unused:
 if remove_unused_imports(file_path, unused, dry_run=args.dry_run):
 total_removed += len(unused)
 
 print()
    print("=" * 70)
    print(f"완료! 총 {total_removed}개 import 제거 {'예정' if args.dry_run else '완료'}")
    print("=" * 70)


if __name__ == "__main__":
 main()