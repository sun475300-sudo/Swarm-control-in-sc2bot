#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Optimize Project Size

������Ʈ ũ�� ����ȭ: ���ʿ��� ���� ����, ĳ�� ����, �ߺ� ����
"""

import os
import shutil
import sys
from pathlib import Path
from typing import List
import Dict
import Tuple
from collections import defaultdict

# Add parent directory to path
script_dir = Path(__file__).parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

PROJECT_ROOT = script_dir


class ProjectSizeOptimizer:
    """������Ʈ ũ�� ����ȭ��"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.files_to_remove: List[Path] = []
        self.dirs_to_remove: List[Path] = []
        self.stats = {
            "files_removed": 0,
            "dirs_removed": 0,
            "space_freed_mb": 0.0,
            "cache_files": 0,
            "log_files": 0,
            "backup_files": 0,
            "duplicate_files": 0,
        }

    def find_cache_files(self) -> List[Path]:
        """ĳ�� ���� ã��"""
        cache_files = []
        cache_patterns = [
            "**/__pycache__/**",
            "**/*.pyc",
            "**/*.pyo",
            "**/.pytest_cache/**",
            "**/.mypy_cache/**",
            "**/.ruff_cache/**",
            "**/.tox/**",
            "**/*.egg-info/**",
        ]

        exclude_dirs = {'.git', 'node_modules', 'venv', '.venv'}

        for pattern in cache_patterns:
            for file_path in PROJECT_ROOT.rglob(pattern.replace("**/", "")):
                if any(ex in str(file_path) for ex in exclude_dirs):
                    continue
                if file_path.is_file():
                    cache_files.append(file_path)
                elif file_path.is_dir() and file_path.name in ['__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache']:
                    cache_files.append(file_path)

        return list(set(cache_files))

    def find_log_files(self) -> List[Path]:
        """�α� ���� ã��"""
        log_files = []
        log_patterns = ["*.log", "*.log.*", "*.txt"]

        exclude_dirs = {
            '.git',
            'node_modules',
            'venv',
            '.venv',
            'data',
            'models'}

        for pattern in log_patterns:
            for file_path in PROJECT_ROOT.rglob(pattern):
                if any(ex in str(file_path) for ex in exclude_dirs):
                    continue
                # Keep important files
                if file_path.name in ['requirements.txt', 'README.txt']:
                    continue
                if file_path.is_file():
                    # Check if it's in logs directory (keep recent ones)
                    if 'logs' in str(file_path) and file_path.stat(
                    ).st_size < 10 * 1024 * 1024:  # Keep files < 10MB
                        continue
                    log_files.append(file_path)

        return log_files

    def find_backup_files(self) -> List[Path]:
        """��� ���� ã��"""
        backup_files = []
        backup_patterns = [
            "*.bak",
            "*.backup",
            "*.old",
            "*.orig",
            "*.tmp",
            "*.temp",
            "*~"]

        for pattern in backup_patterns:
            for file_path in PROJECT_ROOT.rglob(pattern):
                if file_path.is_file():
                    backup_files.append(file_path)

        return backup_files

    def find_duplicate_files(self) -> List[Path]:
        """�ߺ� ���� ã��"""
        duplicate_files = []
        duplicate_patterns = [
            "*_fixed.py",
            "*_old.py",
            "*_backup.py",
            "*_copy.py",
            "*_test.py",
        ]

        for pattern in duplicate_patterns:
            for file_path in PROJECT_ROOT.rglob(pattern):
                if file_path.is_file():
                    # Check if original exists
                    original_name = file_path.name
                    for dup_suffix in [
                            '_fixed', '_old', '_backup', '_copy', '_test']:
                        if original_name.endswith(f"{dup_suffix}.py"):
                            base_name = original_name.replace(
                                f"{dup_suffix}.py", ".py")
                            original_path = file_path.parent / base_name
                            if original_path.exists():
                                duplicate_files.append(file_path)
                                break

        return duplicate_files

    def find_large_files(
            self, min_size_mb: float = 10.0) -> List[Tuple[Path, float]]:
        """��뷮 ���� ã��"""
        large_files = []
        min_size_bytes = min_size_mb * 1024 * 1024

        exclude_dirs = {
            '.git',
            'node_modules',
            'venv',
            '.venv',
            'models',
            'data',
            'replays'}

        for file_path in PROJECT_ROOT.rglob("*"):
            if any(ex in str(file_path) for ex in exclude_dirs):
                continue
            if file_path.is_file():
                try:
                    size = file_path.stat().st_size
                    if size >= min_size_bytes:
                        size_mb = size / (1024 * 1024)
                        large_files.append((file_path, size_mb))
                except (OSError, PermissionError):
                    pass

        return sorted(large_files, key=lambda x: x[1], reverse=True)

    def find_empty_dirs(self) -> List[Path]:
        """�� ���丮 ã��"""
        empty_dirs = []
        exclude_dirs = {'.git', 'node_modules', 'venv', '.venv', '__pycache__'}

        for dir_path in PROJECT_ROOT.rglob("*"):
            if any(ex in str(dir_path) for ex in exclude_dirs):
                continue
            if dir_path.is_dir():
                try:
                    if not any(dir_path.iterdir()):
                        empty_dirs.append(dir_path)
                except (OSError, PermissionError):
                    pass

        return empty_dirs

    def scan_project(self):
        """������Ʈ ��ĵ"""
        print("\n[STEP 1] Scanning project for optimization targets...")
        print("-" * 70)

        # Find all types of files to remove
        cache_files = self.find_cache_files()
        log_files = self.find_log_files()
        backup_files = self.find_backup_files()
        duplicate_files = self.find_duplicate_files()
        empty_dirs = self.find_empty_dirs()

        # Add to removal list
        self.files_to_remove.extend(cache_files)
        self.files_to_remove.extend(log_files)
        self.files_to_remove.extend(backup_files)
        self.files_to_remove.extend(duplicate_files)
        self.dirs_to_remove.extend(empty_dirs)

        # Remove duplicates
        self.files_to_remove = list(set(self.files_to_remove))
        self.dirs_to_remove = list(set(self.dirs_to_remove))

        # Update stats
        self.stats["cache_files"] = len(cache_files)
        self.stats["log_files"] = len(log_files)
        self.stats["backup_files"] = len(backup_files)
        self.stats["duplicate_files"] = len(duplicate_files)

        print(f"[FOUND] Cache files: {len(cache_files)}")
        print(f"[FOUND] Log files: {len(log_files)}")
        print(f"[FOUND] Backup files: {len(backup_files)}")
        print(f"[FOUND] Duplicate files: {len(duplicate_files)}")
        print(f"[FOUND] Empty directories: {len(empty_dirs)}")
        print(f"[TOTAL] Files to remove: {len(self.files_to_remove)}")
        print(f"[TOTAL] Directories to remove: {len(self.dirs_to_remove)}")

    def calculate_space(self) -> float:
        """������ ���ϵ��� �� ũ�� ��� (MB)"""
        total_size = 0.0

        for file_path in self.files_to_remove:
            try:
                if file_path.exists() and file_path.is_file():
                    total_size += file_path.stat().st_size
            except (OSError, PermissionError):
                pass

        for dir_path in self.dirs_to_remove:
            try:
                if dir_path.exists() and dir_path.is_dir():
                    for file_path in dir_path.rglob("*"):
                        if file_path.is_file():
                            try:
                                total_size += file_path.stat().st_size
                            except (OSError, PermissionError):
                                pass
            except (OSError, PermissionError):
                pass

        return total_size / (1024 * 1024)  # MB

    def optimize(self):
        """����ȭ ����"""
        self.scan_project()

        space_freed = self.calculate_space()
        self.stats["space_freed_mb"] = space_freed

        print("\n[STEP 2] Optimization Summary")
        print("-" * 70)
        print(f"Files to remove: {len(self.files_to_remove)}")
        print(f"Directories to remove: {len(self.dirs_to_remove)}")
        print(f"Space to free: {space_freed:.2f} MB")
        print()

        if self.dry_run:
            print("[DRY RUN] No files will be removed")
            return

        print("[STEP 3] Removing files and directories...")
        print("-" * 70)

        # Remove files
        for file_path in self.files_to_remove:
            try:
                if file_path.exists():
                    size = file_path.stat().st_size if file_path.is_file() else 0
                    file_path.unlink()
                    self.stats["files_removed"] += 1
                    self.stats["space_freed_mb"] += size / (1024 * 1024)
                    print(f"[REMOVED] {file_path.relative_to(PROJECT_ROOT)}")
            except Exception as e:
                print(f"[ERROR] Failed to remove {file_path}: {e}")

        # Remove directories
        for dir_path in sorted(
                self.dirs_to_remove,
                key=lambda x: len(
                    str(x)),
                reverse=True):
            try:
                if dir_path.exists():
                    shutil.rmtree(dir_path)
                    self.stats["dirs_removed"] += 1
                    print(f"[REMOVED] {dir_path.relative_to(PROJECT_ROOT)}/")
            except Exception as e:
                print(f"[ERROR] Failed to remove {dir_path}: {e}")

        print("\n" + "=" * 70)
        print("OPTIMIZATION COMPLETE")
        print("=" * 70)
        print(f"Files removed: {self.stats['files_removed']}")
        print(f"Directories removed: {self.stats['dirs_removed']}")
        print(f"Space freed: {self.stats['space_freed_mb']:.2f} MB")
        print("=" * 70)

        # Show large files
        large_files = self.find_large_files(min_size_mb=5.0)
        if large_files:
            print("\n[INFO] Large files (>5MB) found:")
            for file_path, size_mb in large_files[:10]:
                print(
                    f"  - {file_path.relative_to(PROJECT_ROOT)}: {size_mb:.2f} MB")


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Optimize project size")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode (don't remove files)")
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("PROJECT SIZE OPTIMIZATION")
    print("=" * 70)
    print()

    optimizer = ProjectSizeOptimizer(dry_run=args.dry_run)
    optimizer.optimize()


if __name__ == "__main__":
    main()
