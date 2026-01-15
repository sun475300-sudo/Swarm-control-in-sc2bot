# -*- coding: utf-8 -*-
"""
���� �ڵ� ǰ�� ���� ����

������� �ʴ� import ���� �� ��Ÿ�� ������ ����
"""

import ast
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


class FocusedCodeQualityImprover:
    """���� �ڵ� ǰ�� ������"""
 
 def __init__(self):
 self.stats = {
            "unused_imports_removed": 0,
            "files_modified": 0,
            "style_issues_fixed": 0
 }
 
 def remove_unused_imports(self, file_path: Path) -> int:
        """������� �ʴ� import ����"""
 removed_count = 0
 
 try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 
 original_content = content
 
 try:
 tree = ast.parse(content)
 except SyntaxError:
 # ���� ������ �ִ� ������ �ǳʶ�
 return 0
 
 # Import ����
 import_lines = []
 imports = set()
 import_from_lines = []
 import_from_modules = set()
 
 for node in ast.walk(tree):
 if isinstance(node, ast.Import):
 for alias in node.names:
                        imports.add(alias.name.split('.')[0])
 import_lines.append((node.lineno - 1, alias.name))
 elif isinstance(node, ast.ImportFrom):
 if node.module:
                        import_from_modules.add(node.module.split('.')[0])
 import_from_lines.append((node.lineno - 1, node.module))
 
 # ���� �̸� ����
 used_names = set()
 for node in ast.walk(tree):
 if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Store):
 used_names.add(node.id)
 elif isinstance(node, ast.Attribute):
 # attribute ���ٵ� ���� (��: json.load)
 if isinstance(node.value, ast.Name):
 used_names.add(node.value.id)
 
 # ������� �ʴ� import ã��
 lines = content.splitlines()
 modified_lines = []
 removed_lines = set()
 
 for i, line in enumerate(lines):
 should_remove = False
 
 # import �� Ȯ��
 for lineno, import_name in import_lines:
 if i == lineno:
                        module_name = import_name.split('.')[0]
 if module_name not in used_names:
 should_remove = True
 removed_count += 1
 removed_lines.add(i)
 break
 
 # from ... import Ȯ��
 if not should_remove:
 for lineno, module_name in import_from_lines:
 if i == lineno:
                            module_base = module_name.split('.')[0]
 if module_base not in used_names:
 # �� ��Ȯ�� üũ �ʿ������� �ϴ� �����ϰ�
 should_remove = True
 removed_count += 1
 removed_lines.add(i)
 break
 
 if not should_remove:
 modified_lines.append(line)
 
 if removed_count > 0:
 # ��� ����
                backup_path = file_path.with_suffix(file_path.suffix + '.bak')
 try:
                    with open(backup_path, 'w', encoding='utf-8') as f:
 f.write(original_content)
 except Exception:
 pass # ��� �����ص� ���
 
 # ������ ���� ����
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(modified_lines))
 
                self.stats["files_modified"] += 1
 
 except Exception as e:
 # ������ �־ ��� ����
 pass
 
 return removed_count
 
 def fix_style_issues(self, file_path: Path) -> int:
        """��Ÿ�� ���� ����"""
 fixed_count = 0
 
 try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 
 original_content = content
 lines = content.splitlines()
 modified_lines = []
 
 for line in lines:
 original_line = line
 new_line = line
 
 # ���� 4 spaces�� ��ȯ
                if '\t' in new_line:
                    leading_tabs = len(new_line) - len(new_line.lstrip('\t'))
                    new_line = ' ' * (leading_tabs * 4) + new_line.lstrip('\t')
 if new_line != original_line:
 fixed_count += 1
 
 # ������ �ֺ� ���� (���� ����)
 # =, ==, !=, <, >, <=, >= �ֺ� ����
                if re.search(r'\w[=!<>]+\w', new_line) and not re.search(r'["\'].*[=!<>]+.*["\']', new_line):
 # ���ڿ� ���ΰ� �ƴ� ��츸
                    new_line = re.sub(r'(\w)([=!<>]+)(\w)', r'\1 \2 \3', new_line)
 if new_line != original_line:
 fixed_count += 1
 
 # �� �� ���� ����
 new_line = new_line.rstrip()
                if new_line != original_line and original_line.endswith(' '):
 fixed_count += 1
 
 modified_lines.append(new_line)
 
 if fixed_count > 0:
 # ��� ����
                backup_path = file_path.with_suffix(file_path.suffix + '.bak')
 try:
                    with open(backup_path, 'w', encoding='utf-8') as f:
 f.write(original_content)
 except Exception:
 pass
 
 # ������ ���� ����
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(modified_lines))
 
 except Exception as e:
 # ������ �־ ��� ����
 pass
 
 return fixed_count


def main():
    """���� �Լ�"""
    print("=" * 70)
    print("���� �ڵ� ǰ�� ���� ����")
    print("=" * 70)
 print()
    print("�۾� ����:")
    print("  1. ������� �ʴ� import ����")
    print("  2. ��Ÿ�� ���� ���� (�ǡ�spaces, ���� ����)")
 print()
 
 improver = FocusedCodeQualityImprover()
 
 # Python ���� ã��
    python_files = list(PROJECT_ROOT.glob("**/*.py"))
 python_files = [
 f for f in python_files 
        if not f.name.startswith('_') 
        and 'test' not in f.name.lower()
        and f.parent.name != '__pycache__'
 ]
 
    print(f"[INFO] {len(python_files)}���� Python ������ �м��մϴ�...")
 print()
 
 # 1. ������� �ʴ� import ����
    print("[1/2] ������� �ʴ� import ���� ��...")
 total_unused_imports = 0
 files_with_unused = 0
 
 for i, file_path in enumerate(python_files, 1):
 if i % 50 == 0:
            print(f"  ���� ��... ({i}/{len(python_files)})")
 
 count = improver.remove_unused_imports(file_path)
 if count > 0:
 files_with_unused += 1
 total_unused_imports += count
 
    improver.stats["unused_imports_removed"] = total_unused_imports
    print(f"  - {total_unused_imports}�� ������� �ʴ� import ���� ({files_with_unused}�� ����)")
 print()
 
 # 2. ��Ÿ�� ���� ����
    print("[2/2] ��Ÿ�� ���� ���� ��...")
 total_style_issues = 0
 
 for i, file_path in enumerate(python_files, 1):
 if i % 50 == 0:
            print(f"  ���� ��... ({i}/{len(python_files)})")
 
 count = improver.fix_style_issues(file_path)
 total_style_issues += count
 
    improver.stats["style_issues_fixed"] = total_style_issues
    print(f"  - {total_style_issues}�� ��Ÿ�� ���� ����")
 print()
 
    print("=" * 70)
    print("�ڵ� ǰ�� ���� �Ϸ�!")
    print("=" * 70)
    print(f"  ������� �ʴ� import: {total_unused_imports}�� ���� ({files_with_unused}�� ����)")
    print(f"  ��Ÿ�� ����: {total_style_issues}�� ����")
    print(f"  ������ ����: {improver.stats['files_modified']}��")
 print()


if __name__ == "__main__":
 main()