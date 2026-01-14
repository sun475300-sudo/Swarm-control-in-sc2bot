#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Cleanup Script
Cleanup tasks:
1. Move report files from root to docs/reports
2. Delete backup folders
3. Check and remove duplicate files
4. Delete wrong paths (tools/D/)
"""

import os
import shutil
from pathlib import Path
from typing import List, Set

# Core files to keep in root
CORE_FILES = {
    "README.md",
    "README_ko.md",
    "SETUP_GUIDE.md",
    "requirements.txt",
    ".gitignore",
    "run.py",
    "LICENSE",
}

# Report file patterns to move
REPORT_PATTERNS = [
    "*_REPORT.md",
    "*_STATUS.md",
    "*_SUMMARY.md",
    "*CHECK.md",
    "*ANALYSIS.md",
    "*PLAN.md",
    "*VERIFICATION.md",
    "BACKUP_*.md",
    "CLEANUP_*.md",
    "CODE_*.md",
    "DUPLICATE_*.md",
    "FINAL_*.md",
    "WORK_SUMMARY_*.md",
    "GAME_*.md",
    "LEARNING_*.md",
    "REPLAY_*.md",
    "ERROR_*.md",
    "BUG_*.md",
    "STATUS_*.md",
    "IMPLEMENTATION_*.md",
    "ARCHITECTURE_*.md",
    "AUTHENTICATION_*.md",
    "FEATURE_*.md",
    "MONITORING_*.md",
    "SCIPY_*.md",
    "ENCODING_*.md",
    "CRITICAL_*.md",
    "SELF_HEALING_*.md",
    "GITHUB_*.md",
    "PROJECT_*.md",
    "COMPREHENSIVE_*.md",
    "ENGINEERING_*.md",
    "THREE_*.md",
    "IMPORT_*.md",
    "LOCAL_*.md",
    "MISSING_*.md",
    "MODELS_*.md",
    "FOLDER_*.md",
    "FULL_*.md",
    "SOURCE_*.md",
    "CURSORIGNORE",
]

def find_files_to_move(root_dir: Path) -> List[Path]:
    """Find files to move from root directory"""
    files_to_move = []
    
    for pattern in REPORT_PATTERNS:
        for file_path in root_dir.glob(pattern):
            if file_path.name not in CORE_FILES:
                files_to_move.append(file_path)
    
    return files_to_move

def find_backup_folders(root_dir: Path) -> List[Path]:
    """Find backup folders"""
    backup_folders = []
    
    for backup_dir in root_dir.rglob("backups"):
        if backup_dir.is_dir():
            backup_folders.append(backup_dir)
    
    return backup_folders

def find_duplicate_files(root_dir: Path) -> List[Path]:
    """Find duplicate files"""
    duplicates = []
    
    # chat_manager_utf8.py vs chat_manager.py
    chat_utf8 = root_dir / "chat_manager_utf8.py"
    chat_main = root_dir / "chat_manager.py"
    
    if chat_utf8.exists() and chat_main.exists():
        try:
            with open(chat_main, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'chat_manager_utf8' in content:
                    print(f"[INFO] chat_manager.py references chat_manager_utf8.py")
                    print(f"[INFO] Both files should be kept or merged")
        except Exception as e:
            print(f"[WARNING] Could not check chat_manager.py: {e}")
    
    # package_for_aiarena_clean.py vs package_for_aiarena.py
    package_clean = root_dir / "tools" / "package_for_aiarena_clean.py"
    package_main = root_dir / "tools" / "package_for_aiarena.py"
    
    if package_clean.exists() and package_main.exists():
        print(f"[INFO] Found duplicate: package_for_aiarena_clean.py and package_for_aiarena.py")
        print(f"[INFO] Recommend keeping one and removing the other")
    
    return duplicates

def find_wrong_paths(root_dir: Path) -> List[Path]:
    """Find wrong paths (tools/D/)"""
    wrong_paths = []
    
    tools_d = root_dir / "tools" / "D"
    if tools_d.exists():
        wrong_paths.append(tools_d)
    
    return wrong_paths

def main():
    """Main cleanup function"""
    root_dir = Path(__file__).parent.parent
    
    print("=" * 70)
    print("PROJECT CLEANUP SCRIPT")
    print("=" * 70)
    print(f"Root directory: {root_dir}")
    print()
    
    # 1. Create docs/reports folder
    reports_dir = root_dir / "docs" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Created/verified: {reports_dir}")
    print()
    
    # 2. Find files to move
    files_to_move = find_files_to_move(root_dir)
    print(f"[INFO] Found {len(files_to_move)} files to move to docs/reports/")
    
    # Actually move files
    moved_count = 0
    for file_path in files_to_move:
        try:
            dest = reports_dir / file_path.name
            if dest.exists():
                # Handle duplicate filenames
                counter = 1
                while dest.exists():
                    stem = file_path.stem
                    suffix = file_path.suffix
                    dest = reports_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
            
            shutil.move(str(file_path), str(dest))
            moved_count += 1
            print(f"  [MOVED] {file_path.name} -> docs/reports/{dest.name}")
        except Exception as e:
            print(f"  [ERROR] Failed to move {file_path.name}: {e}")
    
    print(f"[OK] Moved {moved_count} files to docs/reports/")
    print()
    
    # 3. Find and delete backup folders
    backup_folders = find_backup_folders(root_dir)
    print(f"[INFO] Found {len(backup_folders)} backup folders")
    
    deleted_backups = 0
    for backup_dir in backup_folders:
        try:
            shutil.rmtree(str(backup_dir))
            deleted_backups += 1
            print(f"  [DELETED] {backup_dir.relative_to(root_dir)}")
        except Exception as e:
            print(f"  [ERROR] Failed to delete {backup_dir}: {e}")
    
    print(f"[OK] Deleted {deleted_backups} backup folders")
    print()
    
    # 4. Check for duplicate files
    duplicates = find_duplicate_files(root_dir)
    print(f"[INFO] Checked for duplicate files")
    print()
    
    # 5. Delete wrong paths
    wrong_paths = find_wrong_paths(root_dir)
    print(f"[INFO] Found {len(wrong_paths)} wrong paths")
    
    deleted_paths = 0
    for wrong_path in wrong_paths:
        try:
            if wrong_path.is_dir():
                shutil.rmtree(str(wrong_path))
            else:
                wrong_path.unlink()
            deleted_paths += 1
            print(f"  [DELETED] {wrong_path.relative_to(root_dir)}")
        except Exception as e:
            print(f"  [ERROR] Failed to delete {wrong_path}: {e}")
    
    print(f"[OK] Deleted {deleted_paths} wrong paths")
    print()
    
    # 6. Clean up JSON files (replay_links_*.json)
    json_files = list(root_dir.glob("replay_links_*.json"))
    if json_files:
        json_dir = reports_dir / "json_backups"
        json_dir.mkdir(exist_ok=True)
        
        moved_json = 0
        for json_file in json_files:
            try:
                dest = json_dir / json_file.name
                shutil.move(str(json_file), str(dest))
                moved_json += 1
                print(f"  [MOVED] {json_file.name} -> docs/reports/json_backups/")
            except Exception as e:
                print(f"  [ERROR] Failed to move {json_file.name}: {e}")
        
        print(f"[OK] Moved {moved_json} JSON files to docs/reports/json_backups/")
        print()
    
    # Summary
    print("=" * 70)
    print("CLEANUP SUMMARY")
    print("=" * 70)
    print(f"Files moved to docs/reports/: {moved_count}")
    print(f"Backup folders deleted: {deleted_backups}")
    print(f"Wrong paths deleted: {deleted_paths}")
    print(f"JSON files moved: {len(json_files)}")
    print()
    print("[OK] Cleanup completed!")
    print("=" * 70)

if __name__ == "__main__":
    main()
