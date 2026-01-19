#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprehensive code optimization - Fix all errors and optimize code"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def main():
    """Main optimization workflow"""
    print("=" * 70)
    print("COMPREHENSIVE CODE OPTIMIZATION")
    print("=" * 70)
    print()

    # Step 1: Fix remaining syntax errors
    print("[STEP 1] Fixing remaining syntax errors...")
    try:
        result = subprocess.run(
            [sys.executable, "tools/fix_all_remaining_errors.py"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=600
        )
        if result.returncode == 0:
            print("  ? Syntax errors fixed")
        else:
            print(f"  ? Some issues: {result.stderr[:200]}")
    except Exception as e:
        print(f"  ? Error: {e}")

    print()

    # Step 2: Apply autopep8 formatting
    print("[STEP 2] Applying autopep8 code formatting...")
    try:
        result = subprocess.run([sys.executable,
                                 "-m",
                                 "autopep8",
                                 "--in-place",
                                 "--recursive",
                                 "--aggressive",
                                 "--aggressive",
                                 "."],
                                cwd=PROJECT_ROOT,
                                capture_output=True,
                                text=True,
                                timeout=600)
        if result.returncode == 0:
            print("  ? Code formatted with autopep8")
        else:
            print(f"  ? Some issues: {result.stderr[:200]}")
    except Exception as e:
        print(f"  ? Error: {e}")

    print()

    # Step 3: Remove unused imports
    print("[STEP 3] Removing unused imports...")
    try:
        result = subprocess.run([sys.executable,
                                 "-m",
                                 "autoflake",
                                 "--in-place",
                                 "--remove-all-unused-imports",
                                 "--recursive",
                                 "."],
                                cwd=PROJECT_ROOT,
                                capture_output=True,
                                text=True,
                                timeout=600)
        if result.returncode == 0:
            print("  ? Unused imports removed")
        else:
            print(f"  ? Some issues: {result.stderr[:200]}")
    except Exception as e:
        print(f"  ? Error (autoflake not installed): {e}")

    print()

    # Step 4: Sort imports
    print("[STEP 4] Sorting imports...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "isort", ".", "--skip", "__pycache__"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=600
        )
        if result.returncode == 0:
            print("  ? Imports sorted")
        else:
            print(f"  ? Some issues: {result.stderr[:200]}")
    except Exception as e:
        print(f"  ? Error (isort not installed): {e}")

    print()

    # Step 5: Final syntax check
    print("[STEP 5] Running final syntax check...")
    try:
        result = subprocess.run(
            [sys.executable, "tools/full_logic_check.py"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300
        )
        output_lines = result.stdout.split('\n')
        for line in output_lines:
            if "Total files:" in line or "Errors:" in line:
                print(f"  {line}")
    except Exception as e:
        print(f"  ? Error: {e}")

    print()
    print("=" * 70)
    print("CODE OPTIMIZATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
