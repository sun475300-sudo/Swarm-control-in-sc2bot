# -*- coding: utf-8 -*-
"""Move project description files from wicked_zerg_challenger to root directory"""

import shutil
from pathlib import Path

# Get paths
root = Path(__file__).parent
wicked_dir = root / "wicked_zerg_challenger"

# Files to move (source, destination)
files_to_move = [
    ("README_한국어.md", "README_한국어.md"),
    ("README_PROJECT_HISTORY.md", "README_PROJECT_HISTORY.md"),
    ("PROJECT_HISTORY_AND_ISSUES_RESOLVED.md", "PROJECT_HISTORY_AND_ISSUES_RESOLVED.md"),
    ("PROJECT_CLEANUP_COMPLETE.md", "PROJECT_CLEANUP_COMPLETE.md"),
    ("프로젝트 설명문", "프로젝트_설명문"),
]

moved = []
skipped = []

for src_name, dst_name in files_to_move:
    src = wicked_dir / src_name
    dst = root / dst_name
    
    if src.exists():
        if dst.exists():
            skipped.append(f"{src_name} (destination exists)")
        else:
            shutil.move(str(src), str(dst))
            moved.append(f"{src_name} -> {dst_name}")
    else:
        skipped.append(f"{src_name} (not found)")

print("=" * 60)
print("File Move Summary")
print("=" * 60)
print(f"\n? Moved ({len(moved)}):")
for item in moved:
    print(f"  - {item}")

if skipped:
    print(f"\n??  Skipped ({len(skipped)}):")
    for item in skipped:
        print(f"  - {item}")

print(f"\n? Total: {len(moved)} files moved")
