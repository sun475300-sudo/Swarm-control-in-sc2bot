#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integrated Training Pipeline - Replay processing and training automation

This script handles:
1. Replay collection and validation
2. Training execution
3. Learning tracking and cleanup
"""

import sys
import subprocess
import shutil
import os
from datetime import datetime
from pathlib import Path
import argparse

PYTHON_EXECUTABLE = sys.executable


def get_replay_dir() -> Path:
    """Get replay directory - default to D:\\replays"""
    replay_dir_env = os.environ.get("REPLAY_DIR")
    if replay_dir_env and Path(replay_dir_env).exists():
        return Path(replay_dir_env)

    default_path = Path("D:/replays")
    if default_path.exists() or sys.platform == "win32":
        return default_path

    possible_paths = [
        Path(__file__).parent / "replays",
        Path("replays"),
    ]
    for path in possible_paths:
        if path.exists():
            return path

    return default_path


LOCAL_REPLAY_DIR = get_replay_dir()


def validate_replays(replays: list) -> list:
    """Validate replay files using sc2reader if available."""
    try:
        import sc2reader
        sc2reader_available = True
    except ImportError:
        print("   [WARNING] sc2reader not installed. Skipping metadata validation.")
        return replays

    validated = []
    LOTV_RELEASE_DATE = datetime(2015, 11, 10)
    MIN_GAME_TIME_SECONDS = 300

    for replay_path in replays:
        try:
            replay = sc2reader.load_replay(str(replay_path), load_map=True)

            # Check if replay has players
            if not hasattr(replay, 'players') or len(replay.players) < 2:
                continue

            # Check if at least one player is Zerg
            has_zerg = any(
                hasattr(p, 'play_race') and str(p.play_race).lower() == "zerg"
                for p in replay.players
            )
            if not has_zerg:
                continue

            # Check game time
            if hasattr(replay, 'length'):
                if replay.length.seconds < MIN_GAME_TIME_SECONDS:
                    continue

            # Check LotV patch
            if hasattr(replay, 'date'):
                if replay.date < LOTV_RELEASE_DATE:
                    continue

            validated.append(replay_path)
        except Exception:
            continue

    print(f"   [VALIDATE] Valid: {len(validated)}, Skipped: {len(replays) - len(validated)}")
    return validated


def copy_replays(source_folder: Path, target_dir: Path) -> int:
    """Copy replays from source to target directory."""
    if not source_folder.exists():
        return 0

    source_files = list(source_folder.glob("*.SC2Replay"))
    print(f"   [SOURCE] Found {len(source_files)} replays in source. Copying...")

    count = 0
    for src in source_files:
        dst = target_dir / src.name
        if not dst.exists():
            try:
                shutil.copy2(src, dst)
                count += 1
            except (OSError, PermissionError, FileNotFoundError):
                pass

    print(f"   [OK] Copied {count} new replays to workspace")
    return count


def run_training(epochs: int) -> bool:
    """Run the training script."""
    hybrid_learning_script = None

    possible_locations = [
        Path("hybrid_learning.py"),
        Path(__file__).parent / "hybrid_learning.py",
        Path(__file__).parent.parent / "hybrid_learning.py",
        Path("scripts") / "hybrid_learning.py",
    ]

    for location in possible_locations:
        if location.exists():
            hybrid_learning_script = location
            break

    if not hybrid_learning_script:
        print("   [ERROR] hybrid_learning.py not found!")
        return False

    cmd = [PYTHON_EXECUTABLE, str(hybrid_learning_script), "--epochs", str(epochs)]
    print(f"   [EXEC] Executing: {' '.join(cmd)}")

    script_dir = hybrid_learning_script.parent if hybrid_learning_script.parent != Path(".") else Path.cwd()
    result = subprocess.run(cmd, cwd=str(script_dir))

    return result.returncode == 0


def cleanup_replays(replays: list, target_dir: Path) -> int:
    """Move processed replays to completed directory."""
    target_dir.mkdir(parents=True, exist_ok=True)
    moved_count = 0

    for rp in replays:
        try:
            target = target_dir / rp.name
            if not target.exists():
                shutil.move(str(rp), str(target))
                moved_count += 1
        except (OSError, PermissionError, FileNotFoundError):
            pass

    return moved_count


def main():
    parser = argparse.ArgumentParser(description="Integrated training pipeline")
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs")

    default_source = os.environ.get("REPLAY_SOURCE_DIR")
    if not default_source or not os.path.exists(default_source):
        possible_paths = [
            Path("D:/replays/replays"),
            Path(__file__).parent.parent / "replays_archive",
            Path.home() / "replays" / "replays",
            Path("replays_archive"),
        ]
        for path in possible_paths:
            if path.exists():
                default_source = str(path)
                break
        else:
            default_source = "D:/replays/replays"

    parser.add_argument("--source-replays", default=default_source, help="Source replays folder")
    parser.add_argument("--cleanup", action="store_true", help="Move processed files")
    parser.add_argument("--validate-only", action="store_true", help="Only validate, no training")
    args = parser.parse_args()

    print(f"\n{'='*80}")
    print("WICKED ZERG TRAINING PIPELINE STARTED")
    print(f"{'='*80}")

    # Step 1: Prepare Replays
    print(f"\n[STEP 1] PREPARE REPLAYS")
    LOCAL_REPLAY_DIR.mkdir(parents=True, exist_ok=True)

    source_folder = Path(args.source_replays).resolve()
    copy_replays(source_folder, LOCAL_REPLAY_DIR)

    current_replays = list(LOCAL_REPLAY_DIR.glob("*.SC2Replay"))
    print(f"   [TARGET] Total replays found: {len(current_replays)}")

    # Validate replays
    current_replays = validate_replays(current_replays)
    print(f"   [TARGET] Total validated replays ready for training: {len(current_replays)}")

    if len(current_replays) == 0:
        print(f"   [ERROR] No valid replays found!")
        if not args.validate_only:
            sys.exit(1)

    # Step 2: Run Training
    if not args.validate_only:
        print(f"\n{'='*80}")
        print("[STEP 2] RUN TRAINING (SUPERVISED)")
        print(f"{'='*80}")

        if not run_training(args.epochs):
            print(f"\n   [ERROR] TRAINING FAILED!")
            sys.exit(1)
        else:
            print(f"\n   [OK] TRAINING COMPLETED SUCCESSFULLY")

    # Step 3: Cleanup
    if args.cleanup:
        print(f"\n{'='*80}")
        print("[STEP 3] LEARNING TRACKING AND CLEANUP")
        print(f"{'='*80}")

        completed_dir = Path("D:/replays/replays/completed")
        moved_count = cleanup_replays(current_replays, completed_dir)
        print(f"   [SUMMARY] Moved {moved_count} replays to {completed_dir}")

    print(f"\n{'='*80}")
    print("PIPELINE COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
