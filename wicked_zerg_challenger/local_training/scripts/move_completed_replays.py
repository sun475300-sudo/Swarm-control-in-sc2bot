#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Move Completed Replays Script
Move completed replays to D:\replays\replays\completed folder
"""

import sys
import shutil
from pathlib import Path

# Add script directory to sys.path
script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

try:
    from replay_learning_manager import ReplayLearningTracker
    from learning_status_manager import LearningStatusManager
    TRACKER_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Learning tracker modules not available: {e}")
    TRACKER_AVAILABLE = False

def move_completed_replays(replay_dir: Path = None, completed_dir: Path = None, dry_run: bool = False):
    """
    Move completed replays to completed folder
    
    Args:
        replay_dir: Source directory with replays (default: D:\replays\replays)
        completed_dir: Destination directory for completed replays (default: D:\replays\replays\completed)
        dry_run: If True, only show what would be moved without actually moving
    """
    if replay_dir is None:
        replay_dir = Path("D:/replays/replays")
    if completed_dir is None:
        completed_dir = replay_dir / "completed"
    
    # Ensure directories exist
    replay_dir = Path(replay_dir)
    completed_dir = Path(completed_dir)
    completed_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("MOVE COMPLETED REPLAYS")
    print("=" * 70)
    print(f"Source directory: {replay_dir}")
    print(f"Completed directory: {completed_dir}")
    print(f"Mode: {'DRY RUN' if dry_run else 'MOVE'}")
    print()
    
    if not replay_dir.exists():
        print(f"[ERROR] Source directory does not exist: {replay_dir}")
        return
    
    # Get all replay files
    all_replays = list(replay_dir.glob("*.SC2Replay"))
    print(f"[INFO] Found {len(all_replays)} replay files in source directory")
    
    if not TRACKER_AVAILABLE:
        print("[WARNING] Learning tracker not available. Cannot determine completion status.")
        print("[INFO] Use --force to move all replays (not recommended)")
        return
    
    # Initialize trackers
    tracking_file = replay_dir / ".learning_tracking.json"
    status_file = replay_dir / "learning_status.json"
    
    tracker = ReplayLearningTracker(tracking_file, min_iterations=5)
    status_manager = LearningStatusManager(status_file, min_iterations=5) if status_file.exists() else None
    
    # Find completed replays
    completed_replays = []
    in_progress_replays = []
    
    for replay_path in all_replays:
        # Skip if already in completed folder
        if completed_dir in replay_path.parents:
            continue
        
        # Check completion status from both trackers
        is_completed_tracker = tracker.is_completed(replay_path)
        is_completed_status = status_manager.is_completed(replay_path) if status_manager else False
        
        # Use both trackers for confirmation
        is_completed = is_completed_tracker or is_completed_status
        
        if is_completed:
            count_tracker = tracker.get_learning_count(replay_path)
            count_status = status_manager.get_learning_count(replay_path) if status_manager else 0
            max_count = max(count_tracker, count_status)
            completed_replays.append((replay_path, max_count))
        else:
            count_tracker = tracker.get_learning_count(replay_path)
            count_status = status_manager.get_learning_count(replay_path) if status_manager else 0
            max_count = max(count_tracker, count_status)
            in_progress_replays.append((replay_path, max_count))
    
    # Print summary
    print(f"[INFO] Completed replays: {len(completed_replays)}")
    print(f"[INFO] In progress replays: {len(in_progress_replays)}")
    print()
    
    if completed_replays:
        print("Completed replays to move:")
        for replay_path, count in completed_replays:
            print(f"  - {replay_path.name} ({count} iterations)")
        print()
    
    if in_progress_replays and len(in_progress_replays) <= 10:
        print("In progress replays (not moving):")
        for replay_path, count in in_progress_replays[:10]:
            print(f"  - {replay_path.name} ({count}/5 iterations)")
        if len(in_progress_replays) > 10:
            print(f"  ... and {len(in_progress_replays) - 10} more")
        print()
    
    # Move completed replays
    if completed_replays:
        moved_count = 0
        failed_count = 0
        
        for replay_path, count in completed_replays:
            try:
                dest_path = completed_dir / replay_path.name
                
                if dest_path.exists():
                    print(f"  [SKIP] {replay_path.name} - Already exists in completed folder")
                    # Remove source if destination exists
                    if not dry_run:
                        replay_path.unlink()
                    moved_count += 1
                else:
                    if dry_run:
                        print(f"  [WOULD MOVE] {replay_path.name} -> completed/ ({count} iterations)")
                    else:
                        shutil.move(str(replay_path), str(dest_path))
                        print(f"  [MOVED] {replay_path.name} -> completed/ ({count} iterations)")
                    moved_count += 1
            except Exception as e:
                print(f"  [ERROR] Failed to move {replay_path.name}: {e}")
                failed_count += 1
        
        print()
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Completed replays found: {len(completed_replays)}")
        print(f"Successfully moved: {moved_count}")
        if failed_count > 0:
            print(f"Failed to move: {failed_count}")
        print()
    else:
        print("[INFO] No completed replays to move")
        print()

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Move completed replays to completed folder")
    parser.add_argument("--source", type=str, default="D:/replays/replays",
                       help="Source directory with replays (default: D:/replays/replays)")
    parser.add_argument("--completed", type=str, default=None,
                       help="Completed directory (default: <source>/completed)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be moved without actually moving")
    parser.add_argument("--force", action="store_true",
                       help="Force move all replays (not recommended)")
    
    args = parser.parse_args()
    
    if args.force:
        print("[WARNING] Force mode: Moving all replays regardless of completion status")
        replay_dir = Path(args.source)
        completed_dir = Path(args.completed) if args.completed else replay_dir / "completed"
        completed_dir.mkdir(parents=True, exist_ok=True)
        
        all_replays = list(replay_dir.glob("*.SC2Replay"))
        print(f"[INFO] Found {len(all_replays)} replay files")
        
        for replay_path in all_replays:
            if completed_dir in replay_path.parents:
                continue
            try:
                dest_path = completed_dir / replay_path.name
                if not dest_path.exists():
                    if args.dry_run:
                        print(f"  [WOULD MOVE] {replay_path.name}")
                    else:
                        shutil.move(str(replay_path), str(dest_path))
                        print(f"  [MOVED] {replay_path.name}")
            except Exception as e:
                print(f"  [ERROR] Failed to move {replay_path.name}: {e}")
    else:
        move_completed_replays(
            replay_dir=Path(args.source),
            completed_dir=Path(args.completed) if args.completed else None,
            dry_run=args.dry_run
        )

if __name__ == "__main__":
    main()
