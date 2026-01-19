# -*- coding: utf-8 -*-
"""
Organize Root Directory Files

Organizes files in project root directory
- Moves markdown documentation files to docs/archive/
- Keeps only important files in root
"""

import shutil
from pathlib import Path
from typing import List, Set
import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent

# Files to keep in root
KEEP_IN_ROOT = {
    "README.md",
    "README_한국어.md",
    "SETUP.md",
    "CONTRIBUTING.md",
    "requirements_new_structure.txt",
    "main.py",
    "setup.ps1",
    "setup.sh",
    "fix_git_hook.ps1",
    ".gitignore",
}

# Personal files (exclude from organization)
PERSONAL_FILES = {
    "인공지능에게_물어본_나의_인생고민.md",
    "부모님_연구보고서.md",
    "프로젝트_설명문.md",
    "프로젝트_전체_진행_보고서.md",
    "스타크래프트_2_AI_고도화_기획안.md",
}


def should_archive(file_path: Path) -> bool:
    """Check if file should be moved to archive"""
    if file_path.name in KEEP_IN_ROOT:
        return False
    
    if file_path.name in PERSONAL_FILES:
        return False
    
    # Pattern matching
    name = file_path.name
    if name.endswith('.md'):
        patterns = [
            '_FIX.md', '_GUIDE.md', '_SUMMARY.md', '_ANALYSIS.md',
            '_COMPLETE.md', '_STATUS.md', '_VERIFICATION.md', '_IMPROVEMENT.md',
            '_ERROR', '_CHECK.md', '_REVIEW.md',
            'ARCHITECTURE', 'BUILD_ORDER', 'CI_', 'CLEANUP', 'CLEAR_',
            'CODE_', 'CONNECTION_', 'CRITICAL_', 'ENCODING_', 'FINAL_',
            'GIT_', 'GITHUB_', 'HYBRID_', 'LEARNED_', 'LEARNING_',
            'LOCAL_', 'MAX_', 'MODEL_', 'PACKAGE_', 'PARALLEL_',
            'PROJECT_', 'QUEEN_', 'QUICK_', 'REQUIREMENTS_', 'RUN_',
            'TELEMETRY_', 'TRAINING_', 'AWAIT_', 'ARENA_', 'CACHE_',
            'COMPLETE_', 'remove_', 'README_PROJECT'
        ]
        for pattern in patterns:
            if pattern in name:
                return True
    
    # Other files
    if name.startswith('test_') and name.endswith('.py'):
        return True
    if name.startswith('telemetry_') and (name.endswith('.csv') or name.endswith('.json')):
        return True
    if name == '5.9.0':
        return True
    
    return False


def organize_files(dry_run=True):
    """Organize files"""
    archive_dir = PROJECT_ROOT / "docs" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    files_to_move = []
    files_to_keep = []
    personal_files = []
    
    for file_path in PROJECT_ROOT.iterdir():
        if not file_path.is_file():
            continue
        
        if file_path.name in PERSONAL_FILES:
            personal_files.append(file_path.name)
            continue
        
        if file_path.name in KEEP_IN_ROOT:
            files_to_keep.append(file_path.name)
            continue
        
        if should_archive(file_path):
            files_to_move.append(file_path)
        else:
            files_to_keep.append(file_path.name)
    
    result = {
        "to_move": len(files_to_move),
        "to_keep": len(files_to_keep),
        "personal": len(personal_files),
        "moved": [],
        "errors": []
    }
    
    if not dry_run:
        for file_path in files_to_move:
            try:
                dest = archive_dir / file_path.name
                if dest.exists():
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    dest = archive_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}"
                
                shutil.move(str(file_path), str(dest))
                result["moved"].append((file_path.name, str(dest)))
            except Exception as e:
                result["errors"].append((file_path.name, str(e)))
    
    return result, files_to_move


def main():
    """Main function"""
    print("=" * 70)
    print("Root Directory File Organization")
    print("=" * 70)
    print()
    
    # Dry run
    print("[DRY RUN] Analyzing files...")
    result, files_to_move = organize_files(dry_run=True)
    
    print(f"Files to move to docs/archive/: {result['to_move']}")
    print(f"Files to keep in root: {result['to_keep']}")
    print(f"Personal files (excluded): {result['personal']}")
    print()
    
    if result['to_move'] > 0:
        print("Files to be moved:")
        for file_path in files_to_move[:20]:  # Show first 20
            print(f"  - {file_path.name}")
        if len(files_to_move) > 20:
            print(f"  ... and {len(files_to_move) - 20} more files")
        print()
        
        # Auto-move (no prompt for automation)
        print("[MOVING] Moving files...")
        result = organize_files(dry_run=False)
        
        print(f"Moved: {len(result['moved'])} files")
        if result['errors']:
            print(f"Errors: {len(result['errors'])} files")
            for file_name, error in result['errors']:
                print(f"  - {file_name}: {error}")
    else:
        print("No files to move.")
    
    print()
    print("=" * 70)
    print("Organization complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
