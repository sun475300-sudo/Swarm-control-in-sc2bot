#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
�ڵ� �鿩���� ���� ����
Python ������ �鿩���⸦ 4 spaces�� ����
"""

import re
import sys
from pathlib import Path


def fix_file_indentation(file_path: Path) -> bool:
    """������ �鿩���⸦ ����"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        fixed_lines = []
        indent_stack = [0]  # �鿩���� ���� ����

        for i, line in enumerate(lines):
            stripped = line.lstrip()
            if not stripped:  # �� ��
                fixed_lines.append('\n')
                continue

            # ���� ���� ���� �鿩���� ���
            original_indent = len(line) - len(stripped)

            # �鿩���� Ű���� ����
            if stripped.startswith(
                ('def ',
                 'class ',
                 'if ',
                 'elif ',
                 'else:',
                 'for ',
                 'while ',
                 'try:',
                 'except ',
                 'finally:',
                 'with ',
                 'async def ')):
                # Ű���� ���� ���� ������ ����
                current_indent = indent_stack[-1]
                fixed_lines.append(' ' * current_indent + stripped)
                # ���� ���� +1 ����
                if not stripped.endswith(':'):
                    # : �� ������ ���� ���� +1
                    indent_stack.append(current_indent + 4)
            elif stripped.startswith('#'):
                # �ּ��� ���� ������ ����
                current_indent = indent_stack[-1]
                fixed_lines.append(' ' * current_indent + stripped)
            else:
                # �Ϲ� �ڵ�
                current_indent = indent_stack[-1]
                fixed_lines.append(' ' * current_indent + stripped)
                # �� ���� : �̸� ���� ���� +1
                if stripped.endswith(':'):
                    indent_stack.append(current_indent + 4)
                # ���� pass, return, break, continue ���̸� �鿩���� ���� ����
                elif stripped.startswith(('pass', 'return', 'break', 'continue', 'raise')):
                    pass  # ���� ����
                # ���� except, finally ���̸� ���� ����
                elif stripped.startswith(('except ', 'finally:', 'else:', 'elif ')):
                    if len(indent_stack) > 1:
                        indent_stack.pop()
                    current_indent = indent_stack[-1]
                    fixed_lines[-1] = ' ' * current_indent + stripped

        # ���� ����
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)

        return True
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_indentation.py <file1> [file2] ...")
        sys.exit(1)

    for file_path in sys.argv[1:]:
        path = Path(file_path)
        if path.exists():
            print(f"Fixing {path}...")
            if fix_file_indentation(path):
                print(f"  ? Fixed {path}")
            else:
                print(f"  ? Failed to fix {path}")
        else:
            print(f"  ? File not found: {path}")
