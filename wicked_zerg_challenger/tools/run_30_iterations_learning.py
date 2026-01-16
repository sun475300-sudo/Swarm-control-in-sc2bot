#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run 30 Iterations of Learning

ΰ̸ ÷ н 30ȸ  н ÷   м  н 30ȸ
"""

import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

# Add parent directory to path
script_dir = Path(__file__).parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

PROJECT_ROOT = script_dir


def run_replay_learning(iteration: int, max_replays: int = 300) -> bool:
    """Run replay learning from pro gamer replays"""
    print(f"\n[ITERATION {iteration}] Running replay learning...")
    print("-" * 70)

    try:
        from local_training.scripts.replay_build_order_learner import (
            ReplayBuildOrderExtractor
        )
        import os

        # Use flexible path detection
        default_replay_dir = os.environ.get("REPLAY_ARCHIVE_DIR")
        if not default_replay_dir or not os.path.exists(default_replay_dir):
            possible_paths = [
                Path("D:/replays/replays"),
                Path(__file__).parent.parent.parent / "replays_archive",
                Path.home() / "replays" / "replays",
                Path.home() / "replays",
                Path("replays_archive"),
            ]
            for path in possible_paths:
                if path.exists():
                    default_replay_dir = str(path)
                    break
            else:
                default_replay_dir = "D:/replays/replays"

        extractor = ReplayBuildOrderExtractor(replay_dir=default_replay_dir)
        learned_params = extractor.learn_from_replays(max_replays=max_replays)

        if learned_params:
            extractor.save_learned_parameters(learned_params)
            print(
                f"[SUCCESS] Iteration {iteration}: Learned {len(learned_params)} parameters")
            return True
        else:
            print(f"[WARNING] Iteration {iteration}: No parameters learned")
            return False

    except Exception as e:
        print(f"[ERROR] Iteration {iteration}: Replay learning failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_comparison_and_learning(iteration: int) -> bool:
    """Run comparison analysis and learning"""
    print(f"\n[ITERATION {iteration}] Running comparison and learning...")
    print("-" * 70)

    try:
        # Run comparison and apply learning script
        script_path = PROJECT_ROOT / "tools" / "run_comparison_and_apply_learning.py"

        if not script_path.exists():
            print(f"[ERROR] Script not found: {script_path}")
            return False

        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )

        if result.returncode == 0:
            print(
                f"[SUCCESS] Iteration {iteration}: Comparison and learning completed")
            return True
        else:
            print(
                f"[ERROR] Iteration {iteration}: Comparison and learning failed")
            if result.stderr:
                print(f"Error output: {result.stderr[:500]}")
            return False

    except Exception as e:
        print(f"[ERROR] Iteration {iteration}: Failed to run comparison: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function"""
    print("\n" + "=" * 70)
    print("30 ITERATIONS OF LEARNING")
    print("=" * 70)
    print()
    print("This will execute:")
    print("  1. Pro gamer replay learning: 30 iterations")
    print("  2. Comparison analysis and learning: 30 iterations")
    print()

    total_iterations = 30
    replay_learning_success = 0
    comparison_learning_success = 0

    start_time = datetime.now()

    # Step 1: Run replay learning 30 times
    print("\n" + "=" * 70)
    print("STEP 1: PRO GAMER REPLAY LEARNING (30 ITERATIONS)")
    print("=" * 70)

    for i in range(1, total_iterations + 1):
        success = run_replay_learning(i, max_replays=300)
        if success:
            replay_learning_success += 1

        # Brief pause between iterations
        if i < total_iterations:
            time.sleep(2)

    # Step 2: Run comparison and learning 30 times
    print("\n" + "=" * 70)
    print("STEP 2: COMPARISON ANALYSIS AND LEARNING (30 ITERATIONS)")
    print("=" * 70)

    for i in range(1, total_iterations + 1):
        success = run_comparison_and_learning(i)
        if success:
            comparison_learning_success += 1

        # Brief pause between iterations
        if i < total_iterations:
            time.sleep(2)

    # Summary
    end_time = datetime.now()
    duration = end_time - start_time

    print("\n" + "=" * 70)
    print("30 ITERATIONS COMPLETE")
    print("=" * 70)
    print(f"\nSummary:")
    print(
        f"  - Replay learning: {replay_learning_success}/{total_iterations} successful")
    print(
        f"  - Comparison learning: {comparison_learning_success}/{total_iterations} successful")
    print(f"  - Total duration: {duration}")
    print(f"  - Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  - End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("[INFO] All iterations completed")
    print("[INFO] Check learned_build_orders.json for updated parameters")
    print("=" * 70)


if __name__ == "__main__":
    main()
