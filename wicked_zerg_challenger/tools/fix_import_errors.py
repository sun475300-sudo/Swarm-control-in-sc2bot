#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix import errors - Add missing imports and fix import statements"""

import ast
import re
from pathlib import Path
import sys
from typing import Set, List, Tuple


def get_all_python_files(project_root: Path) -> List[Path]:
    """Get all Python files in project"""
    python_files = []
    for py_file in project_root.rglob('*.py'):
        if '__pycache__' in str(py_file) or '.git' in str(py_file):
            continue
        python_files.append(py_file)
    return python_files


def analyze_imports(file_path: Path) -> Tuple[Set[str], Set[str]]:
    """Analyze imports in a file - returns (imported_modules, used_names)"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception:
        return set(), set()

    imported_modules = set()
    used_names = set()

    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            # Collect imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_modules.add(node.module.split('.')[0])

            # Collect used names (variables, functions, classes)
            if isinstance(node, ast.Name):
                used_names.add(node.id)
    except SyntaxError:
        # If file has syntax errors, skip AST analysis
        pass

    return imported_modules, used_names


def find_missing_imports(file_path: Path, project_root: Path) -> List[str]:
    """Find missing imports in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except Exception:
        return []

    missing_imports = []
    content = ''.join(lines)

    # Check for common patterns that indicate missing imports
    patterns = [
        (r'\bDict\b', 'typing'),
        (r'\bList\b', 'typing'),
        (r'\bOptional\b', 'typing'),
        (r'\bTuple\b', 'typing'),
        (r'\bSet\b', 'typing'),
        (r'\bAny\b', 'typing'),
        (r'\bUnion\b', 'typing'),
        (r'\bPath\b', 'pathlib'),
        (r'\bjson\.', 'json'),
        (r'\bos\.', 'os'),
        (r'\bsys\.', 'sys'),
        (r'\bre\.', 're'),
        (r'\basyncio\.', 'asyncio'),
        (r'\blogging\.', 'logging'),
        (r'\bsubprocess\.', 'subprocess'),
        (r'\bdatetime\.', 'datetime'),
        (r'\btime\.', 'time'),
        (r'\brandom\.', 'random'),
    ]

    # Check if file already has these imports
    existing_imports = set()
    for line in lines[:50]:  # Check first 50 lines for imports
        if 'import' in line or 'from' in line:
            for module in ['typing', 'pathlib', 'json', 'os', 'sys', 're',
                           'asyncio', 'logging', 'subprocess', 'datetime', 'time', 'random']:
                if module in line:
                    existing_imports.add(module)

    # Check for patterns
    for pattern, module in patterns:
        if re.search(pattern, content) and module not in existing_imports:
            # Check if it's actually used (not in comments or strings)
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('#'):
                    continue
                if re.search(pattern, line) and 'import' not in line.lower():
                    missing_imports.append(module)
                    break

    return list(set(missing_imports))


def add_missing_imports(file_path: Path) -> Tuple[bool, int]:
    """Add missing imports to a file"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except Exception:
        return False, 0

    missing_imports = find_missing_imports(file_path, file_path.parent.parent)
    if not missing_imports:
        return False, 0

    # Find insertion point (after existing imports)
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('#'):
            continue
        if 'import' in line or 'from' in line:
            insert_idx = i + 1
        elif line.strip() and insert_idx > 0:
            break

    # Generate import statements
    import_map = {
        'typing': '
from typing import Dict, List, Optional, Tuple, Set, Any, Union',
        'pathlib': '
from pathlib import Path',
        'json': 'import json',
        'os': 'import os',
        'sys': 'import sys',
        're': 'import re',
        'asyncio': 'import asyncio',
        'logging': 'import logging',
        'subprocess': 'import subprocess',
        'datetime': '
from datetime import datetime',
        'time': 'import time',
        'random': 'import random',
    }

    imports_to_add = []
    for module in set(missing_imports):
        if module in import_map:
            imports_to_add.append(import_map[module])

    if not imports_to_add:
        return False, 0

    # Insert imports (one per line)
    import_lines = [imp + '\n' for imp in imports_to_add]
    new_lines = lines[:insert_idx] + ['\n'] + import_lines + lines[insert_idx:]
    content = ''.join(new_lines)

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, len(imports_to_add)
    except Exception:
        return False, 0


def fix_import_statements(file_path: Path) -> Tuple[bool, int]:
    """Fix common import statement issues"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception:
        return False, 0

    original_content = content
    fixes = 0

    # Fix:
from . import -> relative s
    # Fix: import errors in try-except blocks
    lines = content.split('\n')
    fixed_lines = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Skip if already has proper import
        if 'import' in stripped and 'from' in stripped:
            fixed_lines.append(line)
            continue

        # Fix common patterns
        # Pattern:
from typing import Dict
import List(missing Optional
import etc.)
        if stripped.startswith('
from typing import '):
            # Check what's actually used in the file
            used_types = set()
            for remaining_line in lines[i:]:
                if 'Dict[' in remaining_line or ' -> Dict' in remaining_line:
                    used_types.add('Dict')
                if 'List[' in remaining_line or ' -> List' in remaining_line:
                    used_types.add('List')
                if 'Optional[' in remaining_line or ' -> Optional' in remaining_line:
                    used_types.add('Optional')
                if 'Tuple[' in remaining_line or ' -> Tuple' in remaining_line:
                    used_types.add('Tuple')
                if 'Set[' in remaining_line or ' -> Set' in remaining_line:
                    used_types.add('Set')
                if 'Any' in remaining_line and 'Any' not in stripped:
                    used_types.add('Any')

            if used_types:
                # Add missing types
                current_imports = stripped.replace('
from typing import ', '').strip().split(', ')
                current_imports = [imp.strip() for imp in current_imports]
                all_imports = sorted(set(current_imports) | used_types)
                if len(all_imports) > len(current_imports):
                    fixed_line = '
from typing import ' + '
import '.join(all_imports)
                    fixed_lines.append(' ' * (len(line) - len(line.lstrip())) + fixed_line)
                    fixes += 1
                    continue

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
    print("FIXING IMPORT ERRORS")
    print("=" * 70)
    print()

    python_files = get_all_python_files(project_root)
    print(f"Found {len(python_files)} Python files")
    print("Analyzing and fixing import errors...")
    print()

    fixed_count = 0
    total_fixes = 0

    for py_file in python_files:
        # Add missing imports
        fixed, fixes = add_missing_imports(py_file)
        if fixed:
            fixed_count += 1
            total_fixes += fixes
            print(f"  Added imports: {py_file.relative_to(project_root)} ({fixes} imports)")

        # Fix import statements
        fixed, fixes = fix_import_statements(py_file)
        if fixed:
            if py_file not in [f[0] for f in [(pf, fixes) for pf in python_files if pf == py_file]]:
                fixed_count += 1
            total_fixes += fixes
            print(f"  Fixed imports: {py_file.relative_to(project_root)} ({fixes} fixes)")

    print()
    print("=" * 70)
    print(f"Total files fixed: {fixed_count}")
    print(f"Total import fixes: {total_fixes}")
    print("=" * 70)


if __name__ == "__main__":
    main()
