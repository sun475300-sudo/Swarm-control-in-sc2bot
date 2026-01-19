#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Code Style Check and Unification
"""

import os
import sys
import subprocess
import ast
from pathlib import Path
from typing import List
import Dict
import Tuple
import Any

# Setup encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

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
EXCLUDE_FILES = {'.pyc', '.pyo', '.pyd', '.bak', '_fixed.py'}


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


def apply_autopep8(file_path: Path) -> Tuple[bool, str]:
    """Apply autopep8 formatting"""
    try:
        result = subprocess.run(['python',
        '-m',
        'autopep8',
        '--in-place',
        '--aggressive',
        '--aggressive',
        str(file_path)],
        capture_output=True,
        text=True,
        timeout=30)
        if result.returncode == 0:
            return True, "Formatted"
        else:
            return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)


def normalize_file(file_path: Path) -> Tuple[bool, int]:
    """Normalize code style in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        original = content
        fixes = 0

        # 1. Convert tabs to 4 spaces
        if '\t' in content:
            lines = content.splitlines(keepends=True)
            new_lines = []
            for line in lines:
                if '\t' in line:
                    line = line.expandtabs(4)
                    fixes += 1
                new_lines.append(line)
            content = ''.join(new_lines)

        # 2. Remove trailing whitespace
        lines = content.splitlines(keepends=True)
        new_lines = []
        for line in lines:
            original_line = line
            if line.endswith(('\r\n', '\n')):
                line_content = line.rstrip('\r\n')
                line_content = line_content.rstrip()
                line = line_content + \
                ('\r\n' if original_line.endswith('\r\n') else '\n')
            else:
                line = line.rstrip()
            if original_line != line:
                fixes += 1
            new_lines.append(line)
        content = ''.join(new_lines)

        # 3. Ensure final newline
        if content and not content.endswith('\n'):
            content += '\n'
            fixes += 1

        if fixes > 0:
            with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)

        return True, fixes
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, 0


def find_python_files(root: Path) -> List[Path]:
    """Find all Python files"""
    python_files = []
    for path in root.rglob('*.py'):
        # Skip excluded directories
        if any(excluded in path.parts for excluded in EXCLUDE_DIRS):
            continue
        # Skip excluded files
        if any(path.name.endswith(ext) for ext in EXCLUDE_FILES):
            continue
        python_files.append(path)
    return sorted(python_files)


def main():
    """Main function"""
    print("=" * 70)
    print("COMPREHENSIVE CODE STYLE CHECK AND UNIFICATION")
    print("=" * 70)
    print()

    python_files = find_python_files(PROJECT_ROOT)
    print(f"Found {len(python_files)} Python files")
    print()

    # Statistics
    syntax_errors = []
    formatted_files = []
    normalized_files = []
    total_fixes = 0

    print("Step 1: Syntax Check")
    print("-" * 70)
    for i, file_path in enumerate(python_files, 1):
        rel_path = file_path.relative_to(PROJECT_ROOT)
        is_valid, error = check_syntax(file_path)
        if not is_valid:
            syntax_errors.append((rel_path, error))
            print(f"[{i}/{len(python_files)}] ERROR {rel_path}: {error}")
        else:
            if i % 50 == 0:
                print(f"[{i}/{len(python_files)}] OK")

    print()
    print(f"Syntax errors: {len(syntax_errors)}")
    if syntax_errors:
        print("\nFiles with syntax errors:")
        for path, error in syntax_errors[:10]:
            print(f"  - {path}: {error}")
        if len(syntax_errors) > 10:
            print(f"  ... and {len(syntax_errors) - 10} more")

    print()
    print("Step 2: Apply autopep8 Formatting")
    print("-" * 70)
    for i, file_path in enumerate(python_files, 1):
        if any(excluded in str(file_path)
        for excluded in ['test', 'tests', '__pycache__']):
            pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        continue
        rel_path = file_path.relative_to(PROJECT_ROOT)
        success, msg = apply_autopep8(file_path)
        if success:
            formatted_files.append(rel_path)
            if i % 20 == 0:
                print(f"[{i}/{len(python_files)}] Formatted: {rel_path}")

    print()
    print(f"Formatted files: {len(formatted_files)}")

    print()
    print("Step 3: Normalize Code Style")
    print("-" * 70)
    for i, file_path in enumerate(python_files, 1):
        rel_path = file_path.relative_to(PROJECT_ROOT)
        success, fixes = normalize_file(file_path)
        if success and fixes > 0:
            normalized_files.append((rel_path, fixes))
            total_fixes += fixes
            if i % 20 == 0:
                print(
                f"[{i}/{len(python_files)}] Normalized: {rel_path} ({fixes} fixes)")

    print()
    print("=" * 70)
    print("CODE STYLE UNIFICATION COMPLETE")
    print("=" * 70)
    print(f"Total files processed: {len(python_files)}")
    print(f"Syntax errors: {len(syntax_errors)}")
    print(f"Formatted files: {len(formatted_files)}")
    print(f"Normalized files: {len(normalized_files)}")
    print(f"Total fixes applied: {total_fixes}")
    print("=" * 70)

    if syntax_errors:
        print(
        "\nWARNING: Some files have syntax errors. Please fix them before proceeding.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
