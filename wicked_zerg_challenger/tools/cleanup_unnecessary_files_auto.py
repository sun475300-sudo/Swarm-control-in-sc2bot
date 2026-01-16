#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cleanup Unnecessary Files (Auto)

프로젝트에서 불필요한 파일들을 자동으로 찾아 삭제하는 스크립트입니다.
"""

import os
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).parent.parent

# 보존할 중요한 파일들
KEEP_FILES = {
    "CODE_CHECK_SUMMARY.md",
    "CODE_OPTIMIZATION_SUMMARY.md",
    "GIT_COMMIT_ISSUES_FIXED.md",
    "PROJECT_OPTIMIZATION_COMPLETE.md",
    "CODE_STYLE_UNIFICATION_COMPLETE.md",
    "FULL_CODE_CHECK_COMPLETE.md",
    "README.md",
    "README_ko.md",
    "README_한국어.md",
    "README_BOT.md",
    "README_GITHUB_UPLOAD.md",
    "SETUP_GUIDE.md",
    "LICENSE",
    "requirements.txt",
}

# 삭제할 파일 패턴
DELETE_PATTERNS = [
    # 중복 파일
    "*_fixed.py",
    "*_old.py",
    "*_backup.py",
    "*_copy.py",

    # 중복 문서 (중요한 것 제외)
    "*_COMPLETE.md",
    "*_READY.md",
    "*_RESULT.md",
    "*_SUMMARY.md",
    "*_STATUS.md",
    "*_REPORT.md",
    "*_GUIDE.md",
    "*_ANALYSIS.md",
    "*_PLAN.md",
    "*_SUGGESTIONS.md",
    "*_CHECKLIST.md",
    "*_EXPLANATION.md",
    "*_FIXED.md",
    "*_START.md",
    "*_STARTED.md",
    "*_APPLIED.md",
]


def find_files_to_delete() -> List[Path]:
    """Find files that should be deleted"""
    files_to_delete: List[Path] = []

    # Find duplicate fixed files
    for pattern in ["*_fixed.py", "*_old.py", "*_backup.py", "*_copy.py"]:
        for file_path in PROJECT_ROOT.rglob(pattern):
            if file_path.is_file() and file_path.name not in KEEP_FILES:
                files_to_delete.append(file_path)

    # Find redundant documentation files
    for file_path in PROJECT_ROOT.rglob("*.md"):
        if file_path.name in KEEP_FILES:
            continue

        # Check if it matches redundant patterns
        for pattern in DELETE_PATTERNS:
            if pattern.startswith("*") and pattern.endswith(".md"):
                pattern_base = pattern.replace("*", "").replace(".md", "")
                if pattern_base in file_path.name:
                    # But keep important ones
                    if any(keep in file_path.name for keep in [
                        "CODE_CHECK", "CODE_OPTIMIZATION", "GIT_COMMIT",
                        "PROJECT_OPTIMIZATION", "FULL_CODE_CHECK",
                        "README", "SETUP", "LICENSE"
                    ]):
                        continue
                    files_to_delete.append(file_path)
                    break

    return files_to_delete


def main():
    """Main function"""
    print("=" * 70)
    print("CLEANUP UNNECESSARY FILES (AUTO)")
    print("=" * 70)
    print()

    files_to_delete = find_files_to_delete()

    if not files_to_delete:
        print("No unnecessary files found.")
        return

    # Remove duplicates
    files_to_delete = list(set(files_to_delete))

    print(f"Found {len(files_to_delete)} files to delete:")
    print()

    # Group by type
    duplicate_files = [f for f in files_to_delete if f.suffix == ".py"]
    redundant_docs = [f for f in files_to_delete if f.suffix == ".md"]

    print(f"  Duplicate Python files: {len(duplicate_files)}")
    print(f"  Redundant documentation: {len(redundant_docs)}")
    print()

    # Show files
    print("Files to be deleted:")
    for file_path in sorted(files_to_delete):
        rel_path = file_path.relative_to(PROJECT_ROOT)
        print(f"  - {rel_path}")

    print()
    print("Deleting files...")

    deleted_count = 0
    failed_count = 0

    for file_path in files_to_delete:
        try:
            file_path.unlink()
            deleted_count += 1
            print(f"[DELETED] {file_path.relative_to(PROJECT_ROOT)}")
        except Exception as e:
            failed_count += 1
            print(
                f"[ERROR] Failed to delete {file_path.relative_to(PROJECT_ROOT)}: {e}")

    print()
    print("=" * 70)
    print("CLEANUP COMPLETE")
    print("=" * 70)
    print(f"  Deleted: {deleted_count} files")
    print(f"  Failed: {failed_count} files")
    print(f"  Total: {len(files_to_delete)} files")
    print("=" * 70)


if __name__ == "__main__":
    main()
