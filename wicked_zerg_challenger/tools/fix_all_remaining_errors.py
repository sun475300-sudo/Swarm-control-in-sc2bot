#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix all remaining syntax errors automatically"""

import ast
import re
from pathlib import Path
import sys


def fix_try_except_block(content: str, file_path: Path) -> tuple[str, int]:
    """Fix try-except blocks with missing except/finally"""
    lines = content.split('\n')
    fixed_lines = []
    fixes = 0

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()

        # Check if line starts with 'try:'
        if stripped.startswith('try:'):
            # Find matching except/finally
            indent = len(line) - len(stripped)
            try_indent = indent

            # Look ahead for except/finally
            found_except = False
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                if not next_line.strip():
                    j += 1
                    continue

                next_indent = len(next_line) - len(next_line.lstrip())

                # If we found a line with same or less indent that's not empty
                if next_indent <= try_indent:
                    if next_line.lstrip().startswith(
                            'except') or next_line.lstrip().startswith('finally'):
                        found_except = True
                    break

                # If next line has proper indentation, check if it's code or
                # except
                if next_indent > try_indent:
                    if next_line.lstrip().startswith(
                            'except') or next_line.lstrip().startswith('finally'):
                        found_except = True
                        break

                j += 1

            # If no except/finally found and next line is empty or has wrong
            # indent, add except
            if not found_except:
                # Check if there's code after try:
                has_code = False
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    if not next_line.strip():
                        j += 1
                        continue
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent <= try_indent:
                        break
                    if next_indent > try_indent:
                        has_code = True
                        break
                    j += 1

                if not has_code:
                    # Add pass after try:
                    fixed_lines.append(line)
                    fixed_lines.append(' ' * (try_indent + 4) + 'pass')
                    fixes += 1
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)

        i += 1

    return '\n'.join(fixed_lines), fixes


def fix_missing_indented_block(
        content: str, file_path: Path) -> tuple[str, int]:
    """Fix missing indented blocks after function/class/try definitions"""
    lines = content.split('\n')
    fixed_lines = []
    fixes = 0

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()

        # Check for definitions that need a body
        if (stripped.endswith(':') and
            (stripped.startswith('def ') or stripped.startswith('class ') or
             stripped.startswith('if ') or stripped.startswith('elif ')
             or stripped.startswith('else:') or stripped.startswith('try:')
             or stripped.startswith('except') or stripped.startswith('finally:')
             or stripped.startswith('for ') or stripped.startswith('while '))):

            indent = len(line) - len(stripped)
            fixed_lines.append(line)

            # Check next line
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if not next_line.strip():
                    # Empty line - check if next non-empty line has proper
                    # indentation
                    j = i + 2
                    while j < len(lines) and not lines[j].strip():
                        j += 1

                    if j < len(lines):
                        next_non_empty = lines[j]
                        next_indent = len(next_non_empty) - \
                            len(next_non_empty.lstrip())
                        expected_indent = indent + 4

                        if next_indent < expected_indent:
                            # Missing indentation - add pass
                            fixed_lines.append('')
                            fixed_lines.append(' ' * expected_indent + 'pass')
                            fixes += 1
                else:
                    # Next line exists - check if it's properly indented
                    next_indent = len(next_line) - len(next_line.lstrip())
                    expected_indent = indent + 4

                    if next_indent < expected_indent and not next_line.lstrip().startswith('#'):
                        # Missing indentation - add pass before next line
                        fixed_lines.append(' ' * expected_indent + 'pass')
                        fixed_lines.append(next_line)
                        fixes += 1
                        i += 1  # Skip next line as we already added it
                    else:
                        # Proper indentation, continue
                        pass
            else:
                # No next line - add pass
                fixed_lines.append(' ' * (indent + 4) + 'pass')
                fixes += 1
        else:
            fixed_lines.append(line)

        i += 1

    return '\n'.join(fixed_lines), fixes


def fix_unindent_errors(content: str, file_path: Path) -> tuple[str, int]:
    """Fix unindent does not match any outer indentation level"""
    # Use AST to parse and fix indentation issues
    try:
        ast.parse(content)
        # No syntax errors
        return content, 0
    except SyntaxError as e:
        if 'unindent' in str(e).lower():
            # Try to fix by checking indentation levels
            lines = content.split('\n')
            fixed_lines = []
            fixes = 0
            indent_stack = [0]  # Track indentation levels

            for i, line in enumerate(lines):
                if not line.strip():
                    fixed_lines.append(line)
                    continue

                current_indent = len(line) - len(line.lstrip())
                stripped = line.lstrip()

                # Check if line should dedent
                if current_indent < indent_stack[-1]:
                    # Find matching indent level
                    while indent_stack and current_indent < indent_stack[-1]:
                        indent_stack.pop()

                # Check if indent matches expected level
                if indent_stack and current_indent > indent_stack[-1] + 4:
                    # Too much indent - reduce to expected + 4
                    expected_indent = indent_stack[-1] + 4
                    fixed_line = ' ' * expected_indent + stripped
                    fixed_lines.append(fixed_line)
                    fixes += 1
                elif indent_stack and current_indent < indent_stack[-1] and current_indent not in indent_stack:
                    # Indent doesn't match any level - adjust to closest
                    closest_indent = min(
                        indent_stack, key=lambda x: abs(
                            x - current_indent))
                    if abs(current_indent - closest_indent) <= 2:
                        # Close enough - use closest
                        fixed_line = ' ' * closest_indent + stripped
                        fixed_lines.append(fixed_line)
                        fixes += 1
                    else:
                        fixed_lines.append(line)
                else:
                    fixed_lines.append(line)
                    # Add to indent stack if it's a new level
                    if stripped.endswith(':'):
                        if current_indent not in indent_stack:
                            indent_stack.append(current_indent)

            return '\n'.join(fixed_lines), fixes

        return content, 0


def fix_file(file_path: Path) -> tuple[bool, int]:
    """Fix all errors in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception:
        try:
            with open(file_path, 'r', encoding='cp949', errors='replace') as f:
                content = f.read()
        except Exception:
            return False, 0

    original_content = content
    total_fixes = 0

    # Fix try-except blocks
    content, fixes = fix_try_except_block(content, file_path)
    total_fixes += fixes

    # Fix missing indented blocks
    content, fixes = fix_missing_indented_block(content, file_path)
    total_fixes += fixes

    # Fix unindent errors
    content, fixes = fix_unindent_errors(content, file_path)
    total_fixes += fixes

    if total_fixes > 0:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, total_fixes
        except Exception:
            return False, 0

    return False, 0


def main():
    """Main function"""
    project_root = Path(__file__).parent.parent

    print("=" * 70)
    print("Fixing All Remaining Syntax Errors")
    print("=" * 70)
    print()

    # Get all Python files
    python_files = []
    for py_file in project_root.rglob('*.py'):
        if '__pycache__' in str(py_file) or '.git' in str(py_file):
            continue
        python_files.append(py_file)

    print(f"Found {len(python_files)} Python files")
    print("Fixing syntax errors...")
    print()

    fixed_count = 0
    total_fixes = 0

    for py_file in python_files:
        fixed, fixes = fix_file(py_file)
        if fixed:
            fixed_count += 1
            total_fixes += fixes
            print(
                f"  Fixed: {py_file.relative_to(project_root)} ({fixes} fixes)")

    print()
    print("=" * 70)
    print(f"Total files fixed: {fixed_count}")
    print(f"Total fixes applied: {total_fixes}")
    print("=" * 70)


if __name__ == "__main__":
    main()
