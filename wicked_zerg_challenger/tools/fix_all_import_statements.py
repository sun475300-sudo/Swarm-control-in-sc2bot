#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix all broken import statements - Merge 'from X' and 'import Y' into one line"""

import re
from pathlib import Path


def fix_import_statements(file_path: Path) -> tuple[bool, int]:
    """Fix import statements that are split across lines"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except Exception:
        try:
            with open(file_path, 'r', encoding='cp949', errors='replace') as f:
                lines = f.readlines()
        except Exception:
            return False, 0

    fixed_lines = []
    fixes = 0
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check if this is "from X" followed by "import Y" on next line
        if stripped.startswith('from ') and ' import ' not in stripped and not stripped.endswith(':'):
            # Check next non-empty line
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1

            if j < len(lines):
                next_line = lines[j]
                next_stripped = next_line.strip()

                # Check if next line starts with "import"
                if next_stripped.startswith('import'):
                    # Merge: "from X" + "import Y" -> "from X import Y"
                    indent = len(line) - len(line.lstrip())
                    module = stripped.replace('from', '').strip()
                    imports = next_stripped.replace('import', '').strip()

                    # Preserve comments from both lines
                    comment1 = ''
                    comment2 = ''
                    if '#' in line:
                        comment1 = ' ' + line[line.index('#'):].strip()
                    if '#' in next_line:
                        comment2 = ' ' + next_line[next_line.index('#'):].strip()

                    merged = f"{' ' * indent}from {module} import {imports}{comment2 or comment1}\n"
                    fixed_lines.append(merged)
                    fixes += 1
                    i = j + 1  # Skip next line
                    continue

        fixed_lines.append(line)
        i += 1

    if fixes > 0:
        fixed_content = ''.join(fixed_lines)
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
    print("FIXING ALL IMPORT STATEMENTS")
    print("=" * 70)
    print()

    # Get all Python files
    python_files = []
    for py_file in project_root.rglob('*.py'):
        if '__pycache__' in str(py_file) or '.git' in str(py_file):
            continue
        python_files.append(py_file)

    print(f"Found {len(python_files)} Python files")
    print("Fixing broken import statements...")
    print()

    fixed_count = 0
    total_fixes = 0

    for py_file in python_files:
        fixed, fixes = fix_import_statements(py_file)
        if fixed:
            fixed_count += 1
            total_fixes += fixes
            if fixes > 0:
                print(f"  Fixed: {py_file.relative_to(project_root)} ({fixes} fixes)")

    print()
    print("=" * 70)
    print(f"Total files fixed: {fixed_count}")
    print(f"Total fixes applied: {total_fixes}")
    print("=" * 70)


if __name__ == "__main__":
    main()
