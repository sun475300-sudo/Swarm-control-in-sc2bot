# -*- coding: utf-8 -*-
"""Remove cleanup target files"""
from pathlib import Path
import shutil

base_dir = Path(__file__).parent.parent

# Files to remove
files_to_remove = [
    ".git\\hooks\\pre-commit.sh.backup",
    "local_training\\logs\\training_log.log",
    "CLEANUP_ANALYSIS_REPORT.md",
    "CODE_DIET_ANALYSIS_REPORT.md",
    "ENCODING_FIX_SUMMARY.md",
]

print("Removing files...")
for file_path in files_to_remove:
 full_path = base_dir / file_path
 try:
 if full_path.is_file():
 full_path.unlink()
            print(f"Removed: {file_path}")
 elif full_path.is_dir():
 shutil.rmtree(full_path)
            print(f"Removed directory: {file_path}")
 except Exception as e:
        print(f"Failed to remove {file_path}: {e}")

print("\nCleanup complete!")