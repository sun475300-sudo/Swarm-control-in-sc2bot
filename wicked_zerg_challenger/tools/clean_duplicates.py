#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clean Duplicates - Maintenance Script for Project Cleanup

This script removes duplicate files, cleans up temporary files,
and organizes the project structure for better maintainability.

Usage:
    python tools/clean_duplicates.py [--dry-run] [--verbose]
"""

import os
import sys
import hashlib
import argparse
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Tuple


def calculate_file_hash(file_path: Path, chunk_size: int = 8192) -> str:
    """Calculate MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except (IOError, PermissionError) as e:
        print(f"[WARNING] Cannot read {file_path}: {e}")
        return ""


def find_duplicate_files(directory: Path, verbose: bool = False) -> Dict[str, List[Path]]:
    """Find duplicate files by content hash."""
    hash_to_files: Dict[str, List[Path]] = defaultdict(list)
    
    # Common file extensions to check
    extensions = {'.py', '.txt', '.md', '.json', '.yaml', '.yml', '.bat', '.ps1', '.sh'}
    
    # Exclude directories
    exclude_dirs = {'.git', '__pycache__', '.venv', 'venv', 'node_modules', 'build', 'dist', '.pytest_cache'}
    
    print(f"[SCAN] Scanning directory: {directory}")
    file_count = 0
    
    for root, dirs, files in os.walk(directory):
        # Remove excluded directories from dirs list (modify in-place)
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            file_path = Path(root) / file
            
            # Skip if not in extensions or is too small
            if file_path.suffix.lower() not in extensions:
                continue
            
            if file_path.stat().st_size < 100:  # Skip very small files
                continue
            
            file_count += 1
            if verbose and file_count % 100 == 0:
                print(f"[SCAN] Processed {file_count} files...")
            
            file_hash = calculate_file_hash(file_path)
            if file_hash:
                hash_to_files[file_hash].append(file_path)
    
    print(f"[SCAN] Scanned {file_count} files")
    
    # Filter to only duplicates (2+ files with same hash)
    duplicates = {h: files for h, files in hash_to_files.items() if len(files) > 1}
    
    return duplicates


def remove_duplicates(duplicates: Dict[str, List[Path]], dry_run: bool = True, verbose: bool = False) -> Tuple[int, int]:
    """Remove duplicate files, keeping the first one."""
    removed_count = 0
    total_size_freed = 0
    
    for file_hash, files in duplicates.items():
        # Sort by path length (keep shorter paths) and then alphabetically
        files_sorted = sorted(files, key=lambda p: (len(str(p)), str(p)))
        
        # Keep first file, remove others
        keep_file = files_sorted[0]
        remove_files = files_sorted[1:]
        
        if verbose:
            print(f"\n[DUPLICATE] Hash: {file_hash[:8]}...")
            print(f"  [KEEP] {keep_file}")
        
        for remove_file in remove_files:
            file_size = remove_file.stat().st_size
            total_size_freed += file_size
            
            if dry_run:
                print(f"  [WOULD REMOVE] {remove_file} ({file_size} bytes)")
            else:
                try:
                    remove_file.unlink()
                    print(f"  [REMOVED] {remove_file} ({file_size} bytes)")
                    removed_count += 1
                except (IOError, PermissionError) as e:
                    print(f"  [ERROR] Cannot remove {remove_file}: {e}")
    
    return removed_count, total_size_freed


def clean_temp_files(directory: Path, dry_run: bool = True) -> int:
    """Clean temporary files (.tmp, .bak, .log, etc.)."""
    temp_patterns = ['*.tmp', '*.bak', '*.swp', '*.log', '*.pyc', '*.pyo']
    temp_dirs = ['__pycache__', '.pytest_cache', '.mypy_cache']
    
    removed_count = 0
    
    # Remove temp files
    for pattern in temp_patterns:
        for temp_file in directory.rglob(pattern):
            if dry_run:
                print(f"[WOULD REMOVE] {temp_file}")
            else:
                try:
                    temp_file.unlink()
                    print(f"[REMOVED] {temp_file}")
                    removed_count += 1
                except (IOError, PermissionError) as e:
                    print(f"[ERROR] Cannot remove {temp_file}: {e}")
    
    # Remove temp directories
    for temp_dir_name in temp_dirs:
        for temp_dir in directory.rglob(temp_dir_name):
            if dry_run:
                print(f"[WOULD REMOVE DIR] {temp_dir}")
            else:
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                    print(f"[REMOVED DIR] {temp_dir}")
                    removed_count += 1
                except (IOError, PermissionError) as e:
                    print(f"[ERROR] Cannot remove {temp_dir}: {e}")
    
    return removed_count


def main():
    parser = argparse.ArgumentParser(description="Clean duplicate files and temporary files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be removed without actually removing")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--directory", type=str, default=".", help="Directory to clean (default: current directory)")
    parser.add_argument("--temp-only", action="store_true", help="Only clean temporary files, not duplicates")
    parser.add_argument("--duplicates-only", action="store_true", help="Only find duplicates, not temp files")
    
    args = parser.parse_args()
    
    directory = Path(args.directory).resolve()
    
    if not directory.exists():
        print(f"[ERROR] Directory does not exist: {directory}")
        sys.exit(1)
    
    print("=" * 70)
    print("CLEAN DUPLICATES - Project Maintenance Script")
    print("=" * 70)
    print(f"Directory: {directory}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("=" * 70)
    
    total_removed = 0
    total_size_freed = 0
    
    # Clean duplicates
    if not args.temp_only:
        print("\n[STEP 1] Finding duplicate files...")
        duplicates = find_duplicate_files(directory, verbose=args.verbose)
        
        if duplicates:
            print(f"\n[FOUND] {len(duplicates)} sets of duplicate files")
            total_duplicate_files = sum(len(files) - 1 for files in duplicates.values())
            print(f"[FOUND] {total_duplicate_files} duplicate files to remove")
            
            removed, size_freed = remove_duplicates(duplicates, dry_run=args.dry_run, verbose=args.verbose)
            total_removed += removed
            total_size_freed += size_freed
        else:
            print("[OK] No duplicate files found")
    
    # Clean temp files
    if not args.duplicates_only:
        print("\n[STEP 2] Cleaning temporary files...")
        temp_removed = clean_temp_files(directory, dry_run=args.dry_run)
        total_removed += temp_removed
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Files removed: {total_removed}")
    print(f"Space freed: {total_size_freed / (1024 * 1024):.2f} MB")
    print("=" * 70)
    
    if args.dry_run:
        print("\n[INFO] This was a dry run. Use without --dry-run to actually remove files.")


if __name__ == "__main__":
    main()
