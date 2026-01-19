#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix broken imports - Separate import statements that are on same line"""

import re
from pathlib import Path


def fix_broken_imports(file_path: Path) -> tuple[bool, int]:
    """Fix import statements that are on same line"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception:
        return False, 0

    lines = content.split('\n')
    fixed_lines = []
    fixes = 0

    for line in lines:
        # Check for patterns like "
import X
import Y" or "
from X import Y
from Z import W"
        if re.search(r'(import|from)\s+\S+\s*(import|from)', line):
            # Split the line into multiple imports
            # Pattern:
import X
import Y ->
import X\n
import Y
            # Pattern:
from X import Y
from Z import W ->
from X import Y\n
from Z import W

            # Find all import statements on this line
            parts = re.split(r'(?=import\s+|from\s+)', line)
            for part in parts:
                if part.strip():
                    # Get indentation from original line
                    indent = len(line) - len(line.lstrip())
                    fixed_lines.append(' ' * indent + part.strip())
                    fixes += 1
        else:
            fixed_lines.append(line)

    if fixes > 0:
        fixed_content = '\n'.join(fixed_lines)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return True, fixes
        except Exception:
            return False, 0

    return False, 0


def main():
    """Main function"""
    project_root = Path(__file__).parent.parent

    print("=" * 70)
    print("FIXING BROKEN IMPORTS")
    print("=" * 70)
    print()

    # Get all Python files
    python_files = []
    for py_file in project_root.rglob('*.py'):
        if '__pycache__' in str(py_file) or '.git' in str(py_file):
            continue
        python_files.append(py_file)

    print(f"Found {len(python_files)} Python files")
    print("Fixing broken imports...")
    print()

    fixed_count = 0
    total_fixes = 0

    for py_file in python_files:
        fixed, fixes = fix_broken_imports(py_file)
        if fixed:
            fixed_count += 1
            total_fixes += fixes
            print(f"  Fixed: {py_file.relative_to(project_root)} ({fixes} fixes)")

    print()
    print("=" * 70)
    print(f"Total files fixed: {fixed_count}")
    print(f"Total fixes applied: {total_fixes}")
    print("=" * 70)


if __name__ == "__main__":
    main()
