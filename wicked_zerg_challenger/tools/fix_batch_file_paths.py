#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Batch File Path Errors

모든 배치 파일의 경로 오류를 수정하는 스크립트입니다.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# Add parent directory to path
script_dir = Path(__file__).parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

PROJECT_ROOT = script_dir


def fix_batch_file_paths(bat_file: Path) -> Tuple[bool, List[str]]:
    """Fix path errors in a batch file"""
    if not bat_file.exists():
        return False, [f"File not found: {bat_file}"]

    try:
        with open(bat_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        original_content = content
        changes = []

        # Fix 1: Ensure UTF-8 encoding at the start
        if not content.startswith('@echo off\nchcp 65001 > nul'):
            if content.startswith('@echo off'):
                content = content.replace(
                    '@echo off', '@echo off\nchcp 65001 > nul', 1)
                changes.append("Added UTF-8 encoding")

        # Fix 2: Ensure proper directory change with error checking
        cd_pattern = r'cd /d "%~dp0\.\.\"'
        if 'cd /d "%~dp0\\.."' in content:
            # Add validation after cd
            if 'if not exist "tools"' not in content and 'if not exist "tools\\"' not in content:
                # Add after first cd command
                cd_match = re.search(r'(cd /d "%~dp0\.\.")\s*\n', content)
                if cd_match:
                    insert_pos = cd_match.end()
                    validation = '\nif not exist "tools" (\n    echo [ERROR] tools directory not found. Current directory: %CD%\n    exit /b 1\n)\n'
                    content = content[:insert_pos] + \
                        validation + content[insert_pos:]
                    changes.append("Added tools directory validation")

        # Fix 3: Fix Python script paths (use backslash consistently)
        # Replace forward slashes with backslashes in Python commands
        python_pattern = r'python ([^\\s]+/)([^\\s]+)'
        matches = re.finditer(python_pattern, content)
        for match in reversed(list(matches)):
            old_path = match.group(0)
            dir_part = match.group(1).replace('/', '\\')
            file_part = match.group(2)
            new_path = f'python {dir_part}{file_part}'
            content = content[:match.start()] + new_path + \
                content[match.end():]
            if new_path != old_path:
                changes.append(f"Fixed path: {old_path} -> {new_path}")

        # Fix 4: Add file existence checks before Python execution
        python_commands = re.finditer(
            r'python (tools\\[^\s]+|local_training\\[^\s]+|bat\\[^\s]+)', content)
        for match in reversed(list(python_commands)):
            script_path = match.group(1)
            script_name = Path(script_path).name

            # Check if 'if exist' check exists before this command
            before_match = content[:match.start()]
            if f'if exist "{script_path}"' not in before_match and f'if exist "{script_path.replace(chr(92), chr(92) + chr(92))}"' not in before_match:
                # Add existence check
                indent = len(before_match) - len(before_match.rstrip('\n')) - \
                    (len(before_match.rsplit('\n', 1)[-1]) if '\n' in before_match else 0)
                check_block = f'\nif exist "{script_path}" (\n    {match.group(0)}\n    if %%ERRORLEVEL%% NEQ 0 (\n        echo [WARNING] {script_name} failed\n    )\n) else (\n    echo [WARNING] {script_path} not found\n)\n'
                content = content[:match.start()] + check_block + \
                    content[match.end():]
                changes.append(f"Added existence check for {script_path}")

        # Fix 5: Ensure PYTHONPATH is set after cd
        if 'set PYTHONPATH=%CD%' not in content:
            # Add after cd command
            cd_match = re.search(r'(cd /d "%~dp0\.\.")\s*\n', content)
            if cd_match:
                insert_pos = cd_match.end()
                # Check if already has validation
                after_cd = content[insert_pos:insert_pos + 200]
                if 'if not exist "tools"' in after_cd:
                    # Insert after validation
                    validation_end = content.find('\n)\n', insert_pos)
                    if validation_end > 0:
                        insert_pos = validation_end + 3

                pythonpath_line = 'set PYTHONPATH=%CD%\n'
                if 'set PYTHONPATH' not in content[:insert_pos + 100]:
                    content = content[:insert_pos] + \
                        pythonpath_line + content[insert_pos:]
                    changes.append("Added PYTHONPATH setting")

        # Fix 6: Fix path separators in echo statements
        # This is less critical but helps consistency

        # Only write if there are changes
        if content != original_content:
            with open(bat_file, 'w', encoding='utf-8', newline='\r\n') as f:
                f.write(content)
            return True, changes

        return False, []

    except Exception as e:
        return False, [f"Error processing {bat_file}: {str(e)}"]


def main():
    """Main function"""
    print("\n" + "=" * 70)
    print("FIX BATCH FILE PATH ERRORS")
    print("=" * 70)
    print()

    bat_dir = PROJECT_ROOT / "bat"

    if not bat_dir.exists():
        print(f"[ERROR] bat directory not found: {bat_dir}")
        return

    bat_files = list(bat_dir.glob("*.bat"))

    if not bat_files:
        print("[WARNING] No batch files found")
        return

    print(f"[INFO] Found {len(bat_files)} batch files")
    print()

    fixed_count = 0
    total_changes = []

    for bat_file in sorted(bat_files):
        print(f"[PROCESSING] {bat_file.name}...")
        fixed, changes = fix_batch_file_paths(bat_file)

        if fixed:
            fixed_count += 1
            total_changes.extend(changes)
            print(f"  [FIXED] {len(changes)} changes:")
            for change in changes:
                print(f"    - {change}")
        else:
            if changes:
                print(f"  [ERROR] {changes[0]}")
            else:
                print(f"  [OK] No changes needed")
        print()

    print("=" * 70)
    print("BATCH FILE PATH FIX COMPLETE")
    print("=" * 70)
    print(f"\nSummary:")
    print(f"  - Total files: {len(bat_files)}")
    print(f"  - Fixed files: {fixed_count}")
    print(f"  - Total changes: {len(total_changes)}")
    print()

    if total_changes:
        print("Changes made:")
        for change in total_changes[:20]:  # Show first 20
            print(f"  - {change}")
        if len(total_changes) > 20:
            print(f"  ... and {len(total_changes) - 20} more")
    print("=" * 70)


if __name__ == "__main__":
    main()
