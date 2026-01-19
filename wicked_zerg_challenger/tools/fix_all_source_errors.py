# -*- coding: utf-8 -*-
"""
��ü �ҽ��ڵ� ���� ���� ����

�鿩���� ����, ���� ����, ���ڵ� ���� ���� �ڵ����� ã�Ƽ� ����
"""

import ast
import re
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Set
from typing import Any
from typing import Union

PROJECT_ROOT = Path(__file__).parent.parent


class SourceErrorFixer:
    """�ҽ��ڵ� ���� ������"""

def __init__(self):
    self.stats = {
    "files_fixed": 0,
    "indentation_errors": 0,
    "syntax_errors": 0,
    "encoding_errors": 0,
    "total_errors": 0
 }
 self.error_files = []

def detect_errors(self, file_path: Path) -> List[str]:
    """������ ���� ����"""
 errors = []

 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     # ���ڵ� �õ�
     encodings = ['utf-8', 'cp949', 'latin-1', 'utf-8-sig']
 content = None
 used_encoding = None

 for encoding in encodings:
     try:
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         with open(file_path, 'r', encoding=encoding) as f:
 content = f.read()
 used_encoding = encoding
 break
 except UnicodeDecodeError:
     continue

 if content is None:
     errors.append("ENCODING_ERROR")
 return errors

 # UTF-8�� ��ȯ �ʿ��
     if used_encoding != 'utf-8':
         pass
     try:
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         pass
     with open(file_path, 'w', encoding='utf-8') as f:
 f.write(content)
 except Exception:
     pass

 # ���� ���� üũ
 try:
     ast.parse(content, filename=str(file_path))
 except SyntaxError as e:
     errors.append(f"SYNTAX_ERROR: {e.msg} at line {e.lineno}")

 # �鿩���� ���� üũ
 lines = content.splitlines()
 indent_stack = [0] # �鿩���� ���� ����

 for i, line in enumerate(lines, 1):
     stripped = line.lstrip()
     if not stripped or stripped.startswith('#'):
         pass
     continue

 # ���� ���� �鿩����
 current_indent = len(line) - len(stripped)

 # ���� ������ ����
     if '\t' in line:
         pass
     errors.append(f"INDENTATION_ERROR: Tab character at line {i}")

 # �鿩���� ����ġ üũ (������ ����)
     if stripped.startswith(('def ', 'class ', 'if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except', 'finally:', 'with ')):
     # ���� �鿩����� ��
 if indent_stack and current_indent > indent_stack[-1] + 4:
     # �ʹ� ���� �鿩����
 pass
 elif indent_stack and current_indent < indent_stack[-1]:
     # �鿩���� ���Ҵ� ����
 while indent_stack and current_indent < indent_stack[-1]:
     pass
 indent_stack.pop()

 if not indent_stack or current_indent == indent_stack[-1]:
     indent_stack.append(current_indent)

 except Exception as e:
     errors.append(f"UNKNOWN_ERROR: {str(e)}")

 return errors

def fix_indentation(self, file_path: Path) -> bool:
    """�鿩���� ���� ����"""
 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()

 lines = content.splitlines()
 fixed_lines = []
 changed = False

 for line in lines:
     original = line

 # ���� 4 spaces�� ��ȯ
     if '\t' in line:
         pass
     leading_tabs = len(line) - len(line.lstrip('\t'))
     line = ' ' * (leading_tabs * 4) + line.lstrip('\t')
 if line != original:
     changed = True
     self.stats["indentation_errors"] += 1

 fixed_lines.append(line)

 if changed:
     # ��� ����
     backup_path = file_path.with_suffix(file_path.suffix + '.bak')
 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     with open(backup_path, 'w', encoding='utf-8') as f:
 f.write(content)
 except Exception:
     pass

 # ������ ���� ����
     with open(file_path, 'w', encoding='utf-8') as f:
     f.write('\n'.join(fixed_lines))

 return True

 except Exception as e:
     return False

 return False

def fix_syntax_errors(self, file_path: Path) -> bool:
    """���� ���� ���� �õ�"""
 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()

 lines = content.splitlines()
 fixed_lines = []
 changed = False

 for i, line in enumerate(lines, 1):
     original = line
 new_line = line

 # �� try/except/finally ���� ����
     if re.match(r'^\s*try:\s*$', line):
     # ���� ���� ����ְų� �鿩���Ⱑ ������ pass �߰�
 if i < len(lines):
     next_line = lines[i] if i < len(lines) else ""
     if not next_line.strip() or not next_line.startswith(' '):
     # pass �߰��� ���� �ٿ��� ó��
 pass

 # �� if/for/while ���� ����
     if re.match(r'^\s*(if|for|while|elif|else|except|finally)\s+.*:\s*$', line):
     # ���� ���� ����ְų� �鿩���Ⱑ ������ pass �߰�
 if i < len(lines):
     next_line = lines[i] if i < len(lines) else ""
     if next_line.strip() and not next_line.startswith(' ') and not next_line.startswith('\t'):
     # pass �߰� �ʿ�
 indent = len(line) - len(line.lstrip())
 fixed_lines.append(line)
     fixed_lines.append(' ' * (indent + 4) + 'pass')
 changed = True
     self.stats["syntax_errors"] += 1
 continue

 fixed_lines.append(new_line)

 if changed:
     # ��� ����
     backup_path = file_path.with_suffix(file_path.suffix + '.bak')
 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     with open(backup_path, 'w', encoding='utf-8') as f:
 f.write(content)
 except Exception:
     pass

 # ������ ���� ����
     with open(file_path, 'w', encoding='utf-8') as f:
     f.write('\n'.join(fixed_lines))

 return True

 except Exception as e:
     return False

 return False

def fix_file(self, file_path: Path) -> bool:
    """������ ��� ���� ����"""
 fixed = False

 # 1. �鿩���� ���� ����
 if self.fix_indentation(file_path):
     fixed = True

 # 2. ���� ���� ���� �õ�
 if self.fix_syntax_errors(file_path):
     fixed = True

 if fixed:
     self.stats["files_fixed"] += 1
 return True

 return False

def scan_and_fix_all(self) -> Dict:
    """��ü ������Ʈ ��ĵ �� ����"""
    print("=" * 70)
    print("��ü �ҽ��ڵ� ���� ���� ����")
    print("=" * 70)
 print()

 # Python ���� ã��
    python_files = list(PROJECT_ROOT.glob("**/*.py"))
 python_files = [
 f for f in python_files
    if not f.name.startswith('_')
    and 'test' not in f.name.lower()
    and f.parent.name != '__pycache__'
    and '.bak' not in f.name
 ]

    print(f"[INFO] {len(python_files)}���� Python ������ ��ĵ�մϴ�...")
 print()

 # 1�ܰ�: ���� ����
    print("[1/3] ���� ���� ��...")
 error_files = []

 for i, file_path in enumerate(python_files, 1):
     if i % 50 == 0:
         print(f"  ���� ��... ({i}/{len(python_files)})")

 errors = self.detect_errors(file_path)
 if errors:
     error_files.append((file_path, errors))
 rel_path = file_path.relative_to(PROJECT_ROOT)
     print(f"  [ERROR] {rel_path}: {len(errors)}�� ����")
 for error in errors[:3]: # ó�� 3���� ǥ��
     print(f"    - {error}")

     print(f"  �� {len(error_files)}�� ���Ͽ��� ���� �߰�")
 print()

 # 2�ܰ�: ���� ����
     print("[2/3] ���� ���� ��...")
 fixed_count = 0

 for file_path, errors in error_files:
     if self.fix_file(file_path):
         fixed_count += 1
 rel_path = file_path.relative_to(PROJECT_ROOT)
     print(f"  [FIXED] {rel_path}")

     print(f"  {fixed_count}�� ���� ���� �Ϸ�")
 print()

 # 3�ܰ�: �����
     print("[3/3] ����� ��...")
 remaining_errors = 0

 for file_path, _ in error_files:
     errors = self.detect_errors(file_path)
 if errors:
     remaining_errors += len(errors)
 rel_path = file_path.relative_to(PROJECT_ROOT)
     print(f"  [WARNING] {rel_path}: ������ {len(errors)}�� ���� ����")

 if remaining_errors == 0:
     print("  ��� ������ �����Ǿ����ϴ�!")
 else:
     print(f"  {remaining_errors}�� ������ �����ֽ��ϴ� (���� ���� �ʿ�)")

 print()

 return {
     "total_files": len(python_files),
     "error_files": len(error_files),
     "fixed_files": fixed_count,
     "remaining_errors": remaining_errors,
     "stats": self.stats
 }


def main():
    """���� �Լ�"""
 fixer = SourceErrorFixer()
 result = fixer.scan_and_fix_all()

    print("=" * 70)
    print("���� ���� �Ϸ�!")
    print("=" * 70)
    print(f"  ��ü ����: {result['total_files']}��")
    print(f"  ���� ����: {result['error_files']}��")
    print(f"  ���� �Ϸ�: {result['fixed_files']}��")
    print(f"  ���� ����: {result['remaining_errors']}��")
 print()
    print("���:")
    print(f"  �鿩���� ����: {result['stats']['indentation_errors']}�� ����")
    print(f"  ���� ����: {result['stats']['syntax_errors']}�� ����")
 print()


if __name__ == "__main__":
    main()
