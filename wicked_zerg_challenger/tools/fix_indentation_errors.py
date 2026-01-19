#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix indentation errors in Python files"""

import re
from pathlib import Path
import sys


def fix_file_indentation(file_path: Path) -> tuple[bool, int]:
    """
    Fix indentation errors in a Python file.
    Returns (fixed, errors_found)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='cp949') as f:
                lines = f.readlines()
        except Exception:
            return False, 0

    fixed_lines = []
    fixes_count = 0

    for i, line in enumerate(lines, 1):
        original_line = line
        stripped = line.lstrip()

        # Skip empty lines
        if not stripped:
            fixed_lines.append(line)
            continue

        # Check for common indentation errors:
        # 1. Method/function definitions with only 1 space (should be 4)
        # 2. Code inside methods with only 1 space (should be 8)

        # Pattern: line starts with single space followed by 'def ' or 'class '
        if re.match(r'^ def ', line) or re.match(r'^ class ', line):
            # Fix: Replace single space at start with 4 spaces
            fixed_line = line.replace(' def ', '    def ', 1)
            fixed_line = fixed_line.replace(' class ', '    class ', 1)
            if fixed_line != line:
                fixes_count += 1
                fixed_lines.append(fixed_line)
                continue

        # Pattern: line starts with single space (likely inside method)
        # But we need to be careful - only fix if it looks like code inside a
        # method
        if line.startswith(' ') and not line.startswith('    '):
            # Check if previous non-empty line was a method/class definition
            prev_idx = len(fixed_lines) - 1
            while prev_idx >= 0 and not fixed_lines[prev_idx].strip():
                prev_idx -= 1

            if prev_idx >= 0:
                prev_line = fixed_lines[prev_idx]
                # If previous line is a method/class definition ending with ':'
                if prev_line.strip().endswith(':') and (
                        'def ' in prev_line or 'class ' in prev_line):
                    # Fix: Replace single space at start with 8 spaces
                    fixed_line = '        ' + stripped
                    if fixed_line != line:
                        fixes_count += 1
                        fixed_lines.append(fixed_line)
                        continue

        fixed_lines.append(line)

    if fixes_count > 0:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(fixed_lines)
            return True, fixes_count
        except Exception as e:
            print(f"Error writing {file_path}: {e}")
            return False, 0

    return False, 0


def fix_specific_patterns(file_path: Path) -> tuple[bool, int]:
    """
    Fix specific indentation patterns found in the codebase.
    Returns (fixed, errors_found)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='cp949') as f:
                content = f.read()
        except Exception:
            return False, 0

    original_content = content
    fixes_count = 0

    # Fix pattern: ' def ' at start of line (should be '    def ')
    # But only if it's after a class definition
    lines = content.split('\n')
    fixed_lines = []
    in_class = False

    for i, line in enumerate(lines):
        # Check if we're in a class
        if 'class ' in line and line.strip().startswith('class '):
            in_class = True
            fixed_lines.append(line)
            continue

        # Check if we've left the class (new top-level definition)
        if in_class and line.strip().startswith('def ') and not line.startswith(' '):
            in_class = False

        # Fix: Method definitions inside class with single space
        if in_class and re.match(r'^ def ', line):
            fixed_line = line.replace(' def ', '    def ', 1)
            fixes_count += 1
            fixed_lines.append(fixed_line)
            continue

        # Fix: Code inside method with single space (after method def)
        if i > 0 and fixed_lines:
            prev_line = fixed_lines[-1]
            if prev_line.strip().endswith(':') and (
                    'def ' in prev_line or 'if ' in prev_line or 'for ' in prev_line or 'try:' in prev_line or 'except' in prev_line):
                # Current line should be indented 4 more spaces than prev_line
                if line.startswith(' ') and not line.startswith('    '):
                    # Calculate correct indentation
                    prev_indent = len(prev_line) - len(prev_line.lstrip())
                    correct_indent = ' ' * (prev_indent + 4)
                    fixed_line = correct_indent + line.lstrip()
                    if fixed_line != line:
                        fixes_count += 1
                        fixed_lines.append(fixed_line)
                        continue

        fixed_lines.append(line)

    if fixes_count > 0:
        fixed_content = '\n'.join(fixed_lines)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return True, fixes_count
        except Exception as e:
            print(f"Error writing {file_path}: {e}")
            return False, 0

    return False, 0


def main():
    """Main function to fix indentation errors"""
    project_root = Path(__file__).parent.parent

    # Get list of Python files with syntax errors from the workflow output
    # We'll process all Python files and fix indentation issues
    python_files = []
    for py_file in project_root.rglob('*.py'):
        # Skip __pycache__ and other excluded directories
        if '__pycache__' in str(py_file) or '.git' in str(py_file):
            continue
        python_files.append(py_file)

    print(f"Found {len(python_files)} Python files")
    print("Fixing indentation errors...")

    total_fixed = 0
    total_errors = 0

    for py_file in python_files:
        # Try specific pattern fixing first
        fixed, errors = fix_specific_patterns(py_file)
        if fixed:
            total_fixed += 1
            total_errors += errors
            print(
                f"  Fixed: {py_file.relative_to(project_root)} ({errors} fixes)")

    print(f"\nTotal files fixed: {total_fixed}")
    print(f"Total indentation fixes: {total_errors}")


if __name__ == "__main__":
    main()
