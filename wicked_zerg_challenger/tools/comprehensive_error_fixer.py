#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Error Fixer - Fix all common Python errors automatically
"""

import ast
import re
from pathlib import Path
from typing import List, Tuple
import sys

PROJECT_ROOT = Path(__file__).parent.parent
EXCLUDE_DIRS = {
    '__pycache__', '.git', 'node_modules', '.venv', 'venv',
    'build', 'dist', '.pytest_cache', '.mypy_cache'}


def fix_import_errors(content: str) -> Tuple[str, int]:
    """Fix common import errors"""
    fixes = 0
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        original_line = line
        
        # Fix: import List -> from typing import List
        if re.match(r'^\s*import\s+(List|Dict|Tuple|Optional|Any|Union|Set)$', line):
            line = line.replace('import ', 'from typing import ')
            fixes += 1
        
        # Fix: import HTTPException -> from fastapi import HTTPException
        if re.match(r'^\s*import\s+(HTTPException|Depends|WebSocket)$', line):
            line = line.replace('import HTTPException', 'from fastapi import HTTPException')
            line = line.replace('import Depends', 'from fastapi import Depends')
            line = line.replace('import WebSocket', 'from fastapi import WebSocket')
            if 'fastapi' in line:
                fixes += 1
        
        # Fix: import status -> from starlette import status
        if re.match(r'^\s*import\s+status$', line) and 'starlette' not in line:
            line = line.replace('import status', 'from starlette import status')
            fixes += 1
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines), fixes


def fix_indentation_errors(content: str) -> Tuple[str, int]:
    """Fix common indentation errors"""
    fixes = 0
    lines = content.split('\n')
    fixed_lines = []
    indent_stack = [0]
    
    for i, line in enumerate(lines):
        if not line.strip():
            fixed_lines.append(line)
            continue
        
        stripped = line.lstrip()
        current_indent = len(line) - len(stripped)
        
        # Fix lines starting with space before import/class/def
        if stripped.startswith(('import ', 'from ', 'class ', 'def ', '@')):
            if current_indent > 0 and i > 0:
                # Check if previous line should have this indentation
                prev_line = lines[i-1] if i > 0 else ''
                if not prev_line.strip().endswith(':') or prev_line.strip().startswith('#'):
                    # Remove incorrect indentation
                    fixed_lines.append(stripped)
                    fixes += 1
                    continue
        
        # Fix inconsistent indentation for class fields
        if stripped and not stripped.startswith('#'):
            # Check if this is a class field with wrong indent
            if (i > 0 and lines[i-1].strip().endswith(':') and
                'class' in lines[i-1] and current_indent > 0 and current_indent % 4 != 0):
                # Fix to proper 4-space indentation
                proper_indent = (indent_stack[-1] + 4) if indent_stack else 0
                fixed_lines.append(' ' * proper_indent + stripped)
                fixes += 1
                continue
        
        fixed_lines.append(line)
        
        # Update indent stack
        if stripped.endswith(':'):
            indent_stack.append(current_indent + 4)
        elif current_indent < indent_stack[-1]:
            while indent_stack and current_indent < indent_stack[-1]:
                indent_stack.pop()
    
    return '\n'.join(fixed_lines), fixes


def fix_try_except_errors(content: str) -> Tuple[str, int]:
    """Fix try-except block errors"""
    fixes = 0
    lines = content.split('\n')
    fixed_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        
        # Check for try: without except/finally
        if stripped == 'try:':
            indent = len(line) - len(stripped)
            fixed_lines.append(line)
            
            # Look ahead for except/finally
            found_except = False
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                if not next_line.strip():
                    j += 1
                    continue
                
                next_stripped = next_line.lstrip()
                next_indent = len(next_line) - len(next_stripped)
                
                if next_indent <= indent and (next_stripped.startswith('except') or 
                                               next_stripped.startswith('finally')):
                    found_except = True
                    break
                if next_indent <= indent:
                    break
                j += 1
            
            # If no except found, add one
            if not found_except:
                # Check if there's code in try block
                has_code = False
                for k in range(i+1, min(j, len(lines))):
                    check_line = lines[k]
                    check_indent = len(check_line) - len(check_line.lstrip())
                    if check_line.strip() and check_indent > indent:
                        has_code = True
                        break
                
                if has_code:
                    # Add except block
                    fixed_lines.append(' ' * indent + 'pass')  # Ensure try has body
                    fixed_lines.append('')
                    fixed_lines.append(' ' * indent + 'except Exception:')
                    fixed_lines.append(' ' * (indent + 4) + 'pass')
                    fixes += 1
        else:
            fixed_lines.append(line)
        
        i += 1
    
    return '\n'.join(fixed_lines), fixes


def fix_file(file_path: Path) -> Tuple[bool, int]:
    """Fix errors in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception:
        return False, 0
    
    original_content = content
    total_fixes = 0
    
    # Fix import errors
    content, fixes = fix_import_errors(content)
    total_fixes += fixes
    
    # Fix indentation errors
    content, fixes = fix_indentation_errors(content)
    total_fixes += fixes
    
    # Fix try-except errors
    content, fixes = fix_try_except_errors(content)
    total_fixes += fixes
    
    # Write back if changed
    if content != original_content and total_fixes > 0:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, total_fixes
        except Exception:
            return False, 0
    
    return False, 0


def main():
    """Main function"""
    print("=" * 70)
    print("COMPREHENSIVE ERROR FIXER")
    print("=" * 70)
    print()
    
    python_files = []
    for path in PROJECT_ROOT.rglob('*.py'):
        if any(excluded in path.parts for excluded in EXCLUDE_DIRS):
            continue
        python_files.append(path)
    
    python_files = sorted(python_files)
    print(f"Found {len(python_files)} Python files")
    print()
    
    total_fixed = 0
    total_fixes = 0
    
    for i, file_path in enumerate(python_files, 1):
        rel_path = file_path.relative_to(PROJECT_ROOT)
        
        # First check if file has syntax errors
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            ast.parse(content)
            # No syntax errors, skip
            continue
        except (SyntaxError, IndentationError):
            # Has errors, try to fix
            fixed, fixes = fix_file(file_path)
            if fixed:
                total_fixed += 1
                total_fixes += fixes
                print(f"[{i}/{len(python_files)}] FIXED: {rel_path} ({fixes} fixes)")
        except Exception:
            continue
        
        if i % 50 == 0:
            print(f"[{i}/{len(python_files)}] Processed...")
    
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Files fixed: {total_fixed}")
    print(f"Total fixes: {total_fixes}")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
