# -*- coding: utf-8 -*-
"""
�ڵ� ǰ�� ���� �ڵ�ȭ ����

1. �ߺ� �ڵ� ����
2. ������� �ʴ� import ����
3. �ڵ� ��Ÿ�� ����
4. Ÿ�� ��Ʈ �߰�
"""

import ast
import os
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).parent.parent


class CodeQualityImprover:
    """�ڵ� ǰ�� ������"""
 
 def __init__(self):
 self.unused_imports: Dict[str, List[str]] = {}
 self.duplicate_code: List[Dict] = []
 self.style_issues: Dict[str, List[str]] = {}
 
 def remove_unused_imports(self, file_path: Path) -> Tuple[bool, List[str]]:
        """������� �ʴ� import ����"""
 try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 lines = content.splitlines()
 
 tree = ast.parse(content, filename=str(file_path))
 
 # Import ã��
 imports = []
 import_lines = {}
 for node in ast.walk(tree):
 if isinstance(node, ast.Import):
 for alias in node.names:
 imports.append(alias.name)
 import_lines[alias.name] = node.lineno
 elif isinstance(node, ast.ImportFrom):
 if node.module:
 for alias in node.names:
                            full_name = f"{node.module}.{alias.name}"
 imports.append(alias.name)
 imports.append(full_name)
 import_lines[alias.name] = node.lineno
 import_lines[full_name] = node.lineno
 
 # ���� �̸� ã��
 used_names = set()
 for node in ast.walk(tree):
 if isinstance(node, ast.Name):
 used_names.add(node.id)
 elif isinstance(node, ast.Attribute):
 if isinstance(node.value, ast.Name):
 used_names.add(node.value.id)
 
 # ������� �ʴ� import ã��
 unused = []
 for imp in imports:
                base_name = imp.split('.')[0]
 if base_name not in used_names and imp not in used_names:
 # ǥ�� ���̺귯���� ���� (���� ��� ����)
                    if base_name not in ['os', 'sys', 'json', 'pathlib', 'typing', 
                                        'collections', 'datetime', 'logging', 'time',
                                        'random', 'math', 're', 'subprocess']:
 unused.append(imp)
 
 if unused:
 # ������ import ���� ����
 new_lines = []
 skip_lines = set()
 for imp in unused:
 if imp in import_lines:
 skip_lines.add(import_lines[imp] - 1) # 0-based index
 
 for i, line in enumerate(lines):
 if i not in skip_lines:
 new_lines.append(line)
 
 # ���� ����
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new_lines))
 
 return True, unused
 
 return False, []
 
 except Exception as e:
            return False, [f"Error: {str(e)}"]
 
 def check_code_style(self, file_path: Path) -> List[str]:
        """�ڵ� ��Ÿ�� �˻�"""
 issues = []
 
 try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 lines = f.readlines()
 
 # PEP 8 �⺻ �˻�
 for i, line in enumerate(lines, 1):
 # �� ���� �˻� (100�� �ʰ�)
 if len(line.rstrip()) > 100:
                    issues.append(f"Line {i}: Line too long ({len(line.rstrip())} characters)")
 
 # �鿩���� �˻� (�� ���)
                if line.startswith('\t'):
                    issues.append(f"Line {i}: Tab character used (use spaces)")
 
 # ���� �˻�
                if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                    if '  ' in line:  # ���ӵ� ����
                        issues.append(f"Line {i}: Multiple spaces found")
 
 return issues
 
 except Exception as e:
            return [f"Error reading file: {str(e)}"]
 
 def fix_code_style(self, file_path: Path) -> bool:
        """�ڵ� ��Ÿ�� �ڵ� ����"""
 try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 lines = content.splitlines()
 
 fixed_lines = []
 for line in lines:
 # ���� �������� ��ȯ
                fixed_line = line.replace('\t', '    ')
 
 # ���ӵ� ���� ���� (��, ���ڿ� ���δ� ����)
                if '  ' in fixed_line and '"' not in fixed_line and "'" not in fixed_line:
                    fixed_line = re.sub(r' {2,}', ' ', fixed_line)
 
 fixed_lines.append(fixed_line)
 
 # ���� ����
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(fixed_lines))
 
 return True
 
 except Exception as e:
            print(f"Error fixing style in {file_path}: {e}")
 return False
 
 def find_duplicate_functions(self, all_files: List[Path]) -> List[Dict]:
        """�ߺ� �Լ� ã�� (������ ����)"""
 function_signatures: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
 
 for file_path in all_files:
 try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 tree = ast.parse(content, filename=str(file_path))
 
 for node in ast.walk(tree):
 if isinstance(node, ast.FunctionDef):
 # �Լ� �ñ״�ó ����
                        sig = f"{node.name}({len(node.args.args)} args)"
 function_signatures[sig].append((
 str(file_path.relative_to(PROJECT_ROOT)),
 node.lineno
 ))
 except Exception:
 continue
 
 duplicates = []
 for sig, occurrences in function_signatures.items():
 if len(occurrences) > 1:
 duplicates.append({
                    "signature": sig,
                    "occurrences": occurrences,
                    "count": len(occurrences)
 })
 
        return sorted(duplicates, key=lambda x: x["count"], reverse=True)


def find_all_python_files() -> List[Path]:
    """��� Python ���� ã��"""
 python_files = []
    exclude_dirs = {'__pycache__', '.git', 'node_modules', '.venv', 'venv', 'models'}
 
 for root, dirs, files in os.walk(PROJECT_ROOT):
 dirs[:] = [d for d in dirs if d not in exclude_dirs]
 
 for file in files:
            if file.endswith('.py'):
 python_files.append(Path(root) / file)
 
 return python_files


def main():
    """���� �Լ�"""
 import argparse
 
    parser = argparse.ArgumentParser(description="�ڵ� ǰ�� ���� ����")
    parser.add_argument("--remove-unused", action="store_true", help="������� �ʴ� import ����")
    parser.add_argument("--fix-style", action="store_true", help="�ڵ� ��Ÿ�� �ڵ� ����")
    parser.add_argument("--check-style", action="store_true", help="�ڵ� ��Ÿ�� �˻�")
    parser.add_argument("--all", action="store_true", help="��� ���� �۾� ����")
 
 args = parser.parse_args()
 
 if not any([args.remove_unused, args.fix_style, args.check_style, args.all]):
 parser.print_help()
 return
 
    print("=" * 70)
    print("�ڵ� ǰ�� ���� ����")
    print("=" * 70)
 print()
 
 improver = CodeQualityImprover()
 python_files = find_all_python_files()
 
    print(f"�� {len(python_files)}���� Python ������ ã�ҽ��ϴ�.")
 print()
 
 if args.all or args.remove_unused:
        print("������� �ʴ� import ���� ��...")
 removed_count = 0
 for i, file_path in enumerate(python_files, 1):
 if i % 20 == 0:
                print(f"  ���� ��: {i}/{len(python_files)}")
 success, unused = improver.remove_unused_imports(file_path)
 if success and unused:
 removed_count += len(unused)
 rel_path = file_path.relative_to(PROJECT_ROOT)
                print(f"  [FIXED] {rel_path}: {len(unused)}�� import ����")
        print(f"�� {removed_count}���� ������� �ʴ� import�� �����߽��ϴ�.")
 print()
 
 if args.all or args.check_style:
        print("�ڵ� ��Ÿ�� �˻� ��...")
 total_issues = 0
 for i, file_path in enumerate(python_files, 1):
 if i % 20 == 0:
                print(f"  ���� ��: {i}/{len(python_files)}")
 issues = improver.check_code_style(file_path)
 if issues:
 total_issues += len(issues)
 rel_path = file_path.relative_to(PROJECT_ROOT)
                print(f"  [ISSUES] {rel_path}: {len(issues)}�� ���� �߰�")
        print(f"�� {total_issues}���� ��Ÿ�� ������ �߰��߽��ϴ�.")
 print()
 
 if args.all or args.fix_style:
        print("�ڵ� ��Ÿ�� �ڵ� ���� ��...")
 fixed_count = 0
 for i, file_path in enumerate(python_files, 1):
 if i % 20 == 0:
                print(f"  ���� ��: {i}/{len(python_files)}")
 if improver.fix_code_style(file_path):
 fixed_count += 1
        print(f"�� {fixed_count}�� ������ ��Ÿ���� �����߽��ϴ�.")
 print()
 
    print("=" * 70)
    print("�۾� �Ϸ�!")
    print("=" * 70)


if __name__ == "__main__":
 main()