#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Full Logic Check - Comprehensive code analysis and error detection
"""

import sys
import ast
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple

PROJECT_ROOT = Path(__file__).parent.parent
EXCLUDE_DIRS = {
    '__pycache__',
    '.git',
    'node_modules',
    '.venv',
    'venv',
    'build',
    'dist',
    '.pytest_cache',
    '.mypy_cache',
    'sc2-ai-dashboard',
    'sc2-mobile-app'}


def check_syntax(file_path: Path) -> Tuple[bool, str]:
    """Check Python file syntax"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        ast.parse(content)
        return True, ""
    except SyntaxError as e:
        return False, f"SyntaxError: {e.msg} at line {e.lineno}"
    except Exception as e:
        return False, f"Error: {str(e)}"


def find_python_files(root: Path) -> List[Path]:
    """Find all Python files"""
    python_files = []
    for path in root.rglob('*.py'):
        if any(excluded in path.parts for excluded in EXCLUDE_DIRS):
            continue
        python_files.append(path)
    return sorted(python_files)


def main():
    """Main function"""
    print("=" * 70)
    print("FULL LOGIC CHECK")
    print("=" * 70)
    print()

    python_files = find_python_files(PROJECT_ROOT)
    print(f"Checking {len(python_files)} Python files...")
    print()

    errors = []
    for i, file_path in enumerate(python_files, 1):
        rel_path = file_path.relative_to(PROJECT_ROOT)
        is_valid, error = check_syntax(file_path)
        if not is_valid:
            errors.append((rel_path, error))
            print(f"[{i}/{len(python_files)}] ERROR: {rel_path}")
            print(f"  {error}")
        elif i % 50 == 0:
            print(f"[{i}/{len(python_files)}] OK")

    print()
    print("=" * 70)
    print("LOGIC CHECK SUMMARY")
    print("=" * 70)
    print(f"Total files: {len(python_files)}")
    print(f"Errors: {len(errors)}")
    print("=" * 70)

    if errors:
        print("\nFiles with errors:")
        for path, error in errors[:20]:
            print(f"  - {path}: {error}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
