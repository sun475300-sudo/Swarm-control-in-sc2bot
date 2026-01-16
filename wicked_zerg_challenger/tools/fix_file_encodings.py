#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix File Encodings

각 소스코드 파일에 맞는 인코딩을 적용하는 스크립트입니다.
"""

import sys
import re
from pathlib import Path
from typing import List, Tuple

# Add parent directory to path
script_dir = Path(__file__).parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

PROJECT_ROOT = script_dir


def has_encoding_declaration(content: str) -> bool:
    """Check if file has encoding declaration"""
    # Check first two lines for encoding declaration
    lines = content.split('\n')[:2]
    for line in lines:
        if re.search(r'coding[:=]\s*utf-8', line, re.IGNORECASE):
            return True
        if re.search(r'coding[:=]\s*utf8', line, re.IGNORECASE):
            return True
    return False


def add_encoding_declaration(content: str, file_path: Path) -> str:
    """Add encoding declaration to Python file"""
    if has_encoding_declaration(content):
        return content

    # Check if file starts with shebang
    if content.startswith('#!'):
        # Insert encoding after shebang
        lines = content.split('\n')
        if len(lines) > 0:
            if len(lines) > 1 and lines[1].strip():
                # Insert after first line
                lines.insert(1, '# -*- coding: utf-8 -*-')
            else:
                # Insert on second line
                lines.insert(1, '# -*- coding: utf-8 -*-')
        return '\n'.join(lines)
    else:
        # Insert at the beginning
        return '# -*- coding: utf-8 -*-\n' + content


def fix_file_encoding(file_path: Path) -> Tuple[bool, List[str]]:
    """Fix encoding for a single file"""
    changes = []

    try:
        # Read file with error handling
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            encoding_ok = True
        except UnicodeDecodeError:
            # Try with different encodings
            for enc in ['cp949', 'latin-1', 'iso-8859-1']:
                try:
                    with open(file_path, 'r', encoding=enc) as f:
                        content = f.read()
                    encoding_ok = False
                    changes.append(f"Converted from {enc} to UTF-8")
                    break
                except UnicodeDecodeError:
                    continue
            else:
                # If all encodings fail, skip file
                return False, [f"Could not decode file: {file_path.name}"]

        # Fix encoding declaration for Python files
        if file_path.suffix == '.py':
            if not has_encoding_declaration(content):
                content = add_encoding_declaration(content, file_path)
                changes.append("Added UTF-8 encoding declaration")

            # Write back with UTF-8
            if not encoding_ok or changes:
                with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(content)
                changes.append("Saved as UTF-8")
                return True, changes

        # For other files, just ensure UTF-8 encoding
        elif file_path.suffix in ['.bat', '.txt', '.md', '.json']:
            if not encoding_ok:
                with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(content)
                changes.append("Converted to UTF-8")
                return True, changes

        return False, changes

    except Exception as e:
        return False, [f"Error: {str(e)}"]


def main():
    """Main function"""
    print("\n" + "=" * 70)
    print("FIX FILE ENCODINGS")
    print("=" * 70)
    print()

    # Files to check
    file_patterns = {
        '*.py': ['tools', 'local_training'],
        '*.bat': ['bat'],
        '*.md': ['.'],
        '*.json': ['local_training'],
    }

    fixed_count = 0
    total_changes = []

    for pattern, dirs in file_patterns.items():
        for dir_name in dirs:
            if dir_name == '.':
                search_dir = PROJECT_ROOT
            else:
                search_dir = PROJECT_ROOT / dir_name

            if not search_dir.exists():
                continue

            files = list(search_dir.rglob(pattern))

            for file_path in files:
                # Skip __pycache__ and .git
                if '__pycache__' in str(file_path) or '.git' in str(file_path):
                    continue

                fixed, changes = fix_file_encoding(file_path)

                if fixed and changes:
                    fixed_count += 1
                    total_changes.extend(
                        [f"{file_path.relative_to(PROJECT_ROOT)}: {c}" for c in changes])
                    print(f"[FIXED] {file_path.relative_to(PROJECT_ROOT)}")
                    for change in changes:
                        print(f"  - {change}")
                elif changes:
                    print(
                        f"[WARNING] {file_path.relative_to(PROJECT_ROOT)}: {changes[0]}")

    print()
    print("=" * 70)
    print("ENCODING FIX COMPLETE")
    print("=" * 70)
    print(f"\nSummary:")
    print(f"  - Files fixed: {fixed_count}")
    print(f"  - Total changes: {len(total_changes)}")
    print()

    if total_changes:
        print("Changes made:")
        for change in total_changes[:30]:  # Show first 30
            print(f"  - {change}")
        if len(total_changes) > 30:
            print(f"  ... and {len(total_changes) - 30} more")
    print("=" * 70)


if __name__ == "__main__":
    main()
