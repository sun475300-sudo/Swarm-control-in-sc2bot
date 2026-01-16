#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cleanup Unnecessary Files - Auto Mode

Automatically removes unnecessary files without user confirmation.
"""

import os
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).parent.parent

# Files to keep (important documentation)
KEEP_FILES = {
    "CODE_CHECK_SUMMARY.md",
    "CODE_OPTIMIZATION_SUMMARY.md",
    "GIT_COMMIT_ISSUES_FIXED.md",
    "PROJECT_OPTIMIZATION_COMPLETE.md",
    "CODE_STYLE_UNIFICATION_COMPLETE.md",
    "FULL_CODE_CHECK_COMPLETE.md",
    "README.md",
    "README_BOT.md",
    "README_ko.md",
    "SETUP_GUIDE.md",
    "LICENSE",
    "requirements.txt",
}

# Patterns for files to delete
DELETE_PATTERNS = {
    # Backup and temporary files
    "extensions": [".bak", ".tmp", ".old", ".orig", ".swp"],
    # Duplicate Python files
    "suffixes": ["_fixed.py", "_old.py", "_backup.py", "_copy.py"],
    # Redundant documentation patterns
    "doc_patterns": [
        "COMPLETE.md",
        "SUMMARY.md",
        "_COMPLETE.md",
        "_SUMMARY.md",
        "_REPORT.md",
        "FIXES_COMPLETE.md",
        "FIXED.md",
        "STARTED.md",
        "READY.md",
        "GUIDE.md",  # Keep only important guides
    ]
}


def find_files_to_delete() -> List[Path]:
    """Find files that should be deleted"""
    files_to_delete: List[Path] = []

    # Find backup files
    for ext in DELETE_PATTERNS["extensions"]:
        for file_path in PROJECT_ROOT.rglob(f"*{ext}"):
            if file_path.is_file():
                files_to_delete.append(file_path)

    # Find duplicate Python files
    for suffix in DELETE_PATTERNS["suffixes"]:
        for file_path in PROJECT_ROOT.rglob(f"*{suffix}"):
            if file_path.is_file():
                files_to_delete.append(file_path)

    # Find redundant documentation files
    for file_path in PROJECT_ROOT.rglob("*.md"):
        # Skip if in keep list
        if file_path.name in KEEP_FILES:
            continue

        # Skip important files
        if any(important in file_path.name for important in [
            "README", "SETUP", "LICENSE", "CONTRIBUTING", "CHANGELOG"
        ]):
            continue

        # Check if matches delete patterns
        for pattern in DELETE_PATTERNS["doc_patterns"]:
            if pattern in file_path.name:
                # But keep some important ones
                if any(keep in file_path.name for keep in [
                    "CODE_CHECK", "CODE_OPTIMIZATION", "GIT_COMMIT",
                    "PROJECT_OPTIMIZATION", "TRAINING_MONITORING"
                ]):
                    continue
                files_to_delete.append(file_path)
                break

    return files_to_delete


def main():
    """Main function"""
    print("=" * 70)
    print("CLEANUP UNNECESSARY FILES (AUTO MODE)")
    print("=" * 70)
    print()

    files_to_delete = find_files_to_delete()

    if not files_to_delete:
        print("No unnecessary files found.")
        return

    print(f"Found {len(files_to_delete)} files to delete:")
    print()

    # Group by type
    backup_files = [
        f for f in files_to_delete if f.suffix in [
            ".bak",
            ".tmp",
            ".old",
            ".orig",
            ".swp"]]
    duplicate_files = [
        f for f in files_to_delete if any(
            suffix in f.name for suffix in [
                "_fixed",
                "_old",
                "_backup",
                "_copy"])]
    redundant_docs = [f for f in files_to_delete if f.suffix == ".md"]

    print(f"  Backup files: {len(backup_files)}")
    print(f"  Duplicate files: {len(duplicate_files)}")
    print(f"  Redundant docs: {len(redundant_docs)}")
    print()

    # Show first 20 files
    print("Files to be deleted (showing first 20):")
    for i, file_path in enumerate(sorted(files_to_delete)[:20], 1):
        rel_path = file_path.relative_to(PROJECT_ROOT)
        print(f"  {i}. {rel_path}")

    if len(files_to_delete) > 20:
        print(f"  ... and {len(files_to_delete) - 20} more files")

    print()
    print("Deleting files...")
    print()

    deleted_count = 0
    failed_count = 0

    for file_path in sorted(files_to_delete):
        try:
            file_path.unlink()
            deleted_count += 1
            if deleted_count <= 10:  # Show first 10 deletions
                print(f"[DELETED] {file_path.relative_to(PROJECT_ROOT)}")
        except Exception as e:
            failed_count += 1
            if failed_count <= 5:  # Show first 5 errors
                print(
                    f"[ERROR] Failed to delete {file_path.relative_to(PROJECT_ROOT)}: {e}")

    print()
    print("=" * 70)
    print("CLEANUP COMPLETE")
    print("=" * 70)
    print(f"Deleted: {deleted_count} files")
    if failed_count > 0:
        print(f"Failed: {failed_count} files")
    print()


if __name__ == "__main__":
    main()
