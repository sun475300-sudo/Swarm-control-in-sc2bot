#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cleanup Unnecessary Batch Files

�Ʒÿ� �ʿ��� ��ġ ���ϸ� ����� �������� �����ϴ� ��ũ��Ʈ�Դϴ�.
"""

import sys
from pathlib import Path

# Add parent directory to path
script_dir = Path(__file__).parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

PROJECT_ROOT = script_dir
BAT_DIR = PROJECT_ROOT / "bat"

# �Ʒÿ� �ʿ��� ��ġ ���� ���
REQUIRED_BATCH_FILES = {
    # �Ʒ� ����
    "start_local_training.bat",
    "training_with_post_learning.bat",

    # �Ʒ� �� �н�
    "post_training_learning.bat",

    # �� �� �н�
    "compare_and_learn.bat",
    "compare_pro_vs_training.bat",
    "run_comparison_and_apply_learning.bat",
    "apply_differences_and_learn.bat",

    # �н� ������ ����ȭ
    "optimize_learning_data.bat",
    "apply_optimized_params.bat",

    # ���÷��� �н�
    "start_replay_learning.bat",
    "start_replay_comparison.bat",

    # ���� ���� (������)
    "daily_improvement.bat",
}


def main():
    """Main function"""
    print("\n" + "=" * 70)
    print("CLEANUP UNNECESSARY BATCH FILES")
    print("=" * 70)
    print()

    if not BAT_DIR.exists():
        print(f"[ERROR] bat directory not found: {BAT_DIR}")
        return

    # ��� ��ġ ���� ã��
    all_bat_files = list(BAT_DIR.glob("*.bat"))

    print(f"[INFO] Found {len(all_bat_files)} batch files")
    print()

    # ������ ���� ã��
    files_to_remove = []
    files_to_keep = []

    for bat_file in all_bat_files:
        if bat_file.name in REQUIRED_BATCH_FILES:
            files_to_keep.append(bat_file)
        else:
            files_to_remove.append(bat_file)

    print(f"[INFO] Files to keep: {len(files_to_keep)}")
    print(f"[INFO] Files to remove: {len(files_to_remove)}")
    print()

    # ������ ���� ��� ǥ��
    if files_to_remove:
        print("Files to remove:")
        for bat_file in sorted(files_to_remove):
            print(f"  - {bat_file.name}")
        print()

    # ������ ���� ��� ǥ��
    print("Files to keep:")
    for bat_file in sorted(files_to_keep):
        print(f"  - {bat_file.name}")
    print()

    # Ȯ��
    print("=" * 70)
    response = input(
        f"Remove {len(files_to_remove)} unnecessary batch files? (yes/no): ")

    if response.lower() != "yes":
        print("[CANCELLED] Cleanup cancelled by user")
        return

    # ���� ����
    removed_count = 0
    for bat_file in files_to_remove:
        try:
            bat_file.unlink()
            removed_count += 1
            print(f"[REMOVED] {bat_file.name}")
        except Exception as e:
            print(f"[ERROR] Failed to remove {bat_file.name}: {e}")

    print()
    print("=" * 70)
    print("CLEANUP COMPLETE")
    print("=" * 70)
    print(f"\nSummary:")
    print(f"  - Total files: {len(all_bat_files)}")
    print(f"  - Kept: {len(files_to_keep)}")
    print(f"  - Removed: {removed_count}")
    print()
    print("Remaining batch files:")
    remaining_files = list(BAT_DIR.glob("*.bat"))
    for bat_file in sorted(remaining_files):
        print(f"  - {bat_file.name}")
    print("=" * 70)


if __name__ == "__main__":
    main()
