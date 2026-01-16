#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add Encoding Declaration to Python Files

인코딩 선언이 없는 Python 파일에 인코딩 선언을 추가하는 스크립트입니다.
"""

import sys
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def has_encoding(content: str) -> bool:
    """Check if file has encoding declaration"""
    lines = content.split('\n')[:2]
    for line in lines:
        if re.search(r'coding[:=]\s*utf-8', line, re.IGNORECASE):
            return True
        if re.search(r'coding[:=]\s*utf8', line, re.IGNORECASE):
            return True
    return False


def add_encoding(content: str) -> str:
    """Add encoding declaration"""
    if has_encoding(content):
        return content

    if content.startswith('#!'):
        lines = content.split('\n')
        if len(lines) > 1:
            lines.insert(1, '# -*- coding: utf-8 -*-')
        else:
            lines.append('# -*- coding: utf-8 -*-')
        return '\n'.join(lines)
    else:
        return '# -*- coding: utf-8 -*-\n' + content


def main():
    """Main function"""
    print("\n" + "=" * 70)
    print("ADD ENCODING DECLARATIONS")
    print("=" * 70)
    print()

    files_to_fix = [
        'tools/api_key_access_control.py',
        'tools/api_key_monitoring.py',
        'tools/api_key_usage_limiter.py',
        'tools/arena_update.py',
        'tools/auto_git_push.py',
        'tools/check_replay_selection.py',
        'tools/cleanup_artifacts.py',
        'tools/cleanup_deploy.py',
        'tools/merge_training_stats.py',
        'tools/prune_updates.py',
        'tools/replay_lifecycle_manager.py',
        'tools/runtime_check.py',
        'tools/summarize_training_stats.py',
        'tools/upload_report.py',
        'tools/upload_to_aiarena.py',
    ]

    fixed_count = 0

    for file_path_str in files_to_fix:
        file_path = PROJECT_ROOT / file_path_str

        if not file_path.exists():
            print(f"[SKIP] {file_path_str} not found")
            continue

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            if not has_encoding(content):
                new_content = add_encoding(content)
                with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(new_content)
                print(f"[FIXED] {file_path_str}")
                fixed_count += 1
            else:
                print(f"[OK] {file_path_str} already has encoding")

        except Exception as e:
            print(f"[ERROR] {file_path_str}: {e}")

    print()
    print("=" * 70)
    print("ENCODING DECLARATIONS ADDED")
    print("=" * 70)
    print(f"\nSummary:")
    print(f"  - Files fixed: {fixed_count}")
    print(f"  - Total files: {len(files_to_fix)}")
    print("=" * 70)


if __name__ == "__main__":
    main()
