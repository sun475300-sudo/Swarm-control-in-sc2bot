#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix All Syntax Errors in Python Files

������Ʈ ��ü�� Python ���Ͽ��� ���� ������ ã�� �����ϴ� ��ũ��Ʈ�Դϴ�.
"""

import ast
import subprocess
import sys
from pathlib import Path
from typing import List
import Tuple

# Add parent directory to path
script_dir = Path(__file__).parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))


def find_python_files(root_dir: Path) -> List[Path]:
    """Find all Python files in the project"""
    python_files = []
    for path in root_dir.rglob("*.py"):
        # Skip virtual environments and cache
        if any(
            skip in str(path) for skip in [
                "__pycache__",
                "venv",
                ".venv",
                "env",
                ".env"]):
            continue
        python_files.append(path)
    return python_files


def check_syntax(file_path: Path) -> Tuple[bool, str]:
    """Check if a Python file has syntax errors"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        ast.parse(source, filename=str(file_path))
        return True, ""
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)


def fix_with_autopep8(file_path: Path) -> bool:
    """Try to fix syntax errors using autopep8"""
    try:
        result = subprocess.run(["python",
                                 "-m",
                                 "autopep8",
                                 "--in-place",
                                 "--aggressive",
                                 "--aggressive",
                                 "--max-line-length=120",
                                 str(file_path)],
                                capture_output=True,
                                text=True,
                                timeout=30)
        return result.returncode == 0
    except Exception:
        return False


def main():
    """Main function"""
    print("=" * 70)
    print("FIXING ALL SYNTAX ERRORS IN PYTHON FILES")
    print("=" * 70)
    print()

    project_root = Path(__file__).parent.parent
    python_files = find_python_files(project_root)

    print(f"Found {len(python_files)} Python files")
    print()

    errors_found = []
    errors_fixed = []

    for file_path in python_files:
        is_valid, error_msg = check_syntax(file_path)
        if not is_valid:
            errors_found.append((file_path, error_msg))
            print(
                f"[ERROR] {file_path.relative_to(project_root)}: {error_msg}")

            # Try to fix with autopep8
            print(f"[FIXING] Attempting to fix {file_path.name}...")
            if fix_with_autopep8(file_path):
                # Check again
                is_valid_after, _ = check_syntax(file_path)
                if is_valid_after:
                    errors_fixed.append(file_path)
                    print(f"[FIXED] {file_path.name}")
                else:
                    print(f"[FAILED] Could not fix {file_path.name}")
            else:
                print(f"[FAILED] autopep8 failed for {file_path.name}")

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total files checked: {len(python_files)}")
    print(f"Errors found: {len(errors_found)}")
    print(f"Errors fixed: {len(errors_fixed)}")
    print(f"Errors remaining: {len(errors_found) - len(errors_fixed)}")

    if errors_found:
        print("\nFiles with errors:")
        for file_path, error_msg in errors_found:
            if file_path not in errors_fixed:
                print(f"  - {file_path.relative_to(project_root)}: {error_msg}")

    if len(errors_found) == len(errors_fixed):
        print("\n? All syntax errors fixed!")
        return 0
    else:
        print("\n?? Some errors could not be automatically fixed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
