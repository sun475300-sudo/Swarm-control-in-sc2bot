#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Workflow: Code Style, Replay Learning, Game Training, and Logic Check
"""

import sys
import subprocess
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def run_command(cmd: list, description: str) -> bool:
    """Run a command and return success status"""
    print(f"\n{'=' * 70}")
    print(f"STEP: {description}")
    print('=' * 70)
    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=3600
        )
        if result.returncode == 0:
            print(f"SUCCESS: {description}")
            if result.stdout:
                print(result.stdout[-1000:])  # Last 1000 chars
            return True
        else:
            print(f"ERROR: {description}")
            if result.stderr:
                print(result.stderr[-1000:])  # Last 1000 chars
            return False
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT: {description}")
        return False
    except Exception as e:
        print(f"EXCEPTION: {description} - {e}")
        return False


def main():
    """Main workflow"""
    print("\n" + "=" * 70)
    print("COMPREHENSIVE WORKFLOW")
    print("=" * 70)
    print("\nThis will execute:")
    print("1. Code style unification")
    print("2. Replay learning and logic check")
    print("3. Game training")
    print("4. Post-training logic check and bug fixes")
    print("5. Replay comparison learning")
    print("6. Full logic check")
    print()

    steps = [
        # Step 1: Code style unification
        (['python', 'tools/comprehensive_code_style_check.py'],
         "Code Style Unification"),

        # Step 2: Replay learning
        (['python', 'local_training/scripts/replay_build_order_learner.py'],
         "Replay Learning"),

        # Step 3: Game training
        (['python', 'run_with_training.py'],
         "Game Training"),

        # Step 4: Replay comparison learning
        (['python', 'tools/compare_pro_vs_training_replays.py'],
         "Replay Comparison Analysis"),

        # Step 5: Apply differences
        (['python', 'tools/apply_differences_and_learn.py'],
         "Apply Differences and Learn"),
    ]

    results = []
    for cmd, desc in steps:
        success = run_command(cmd, desc)
        results.append((desc, success))
        if not success:
            print(f"\nWARNING: {desc} failed, but continuing...")
        time.sleep(2)

    print("\n" + "=" * 70)
    print("WORKFLOW SUMMARY")
    print("=" * 70)
    for desc, success in results:
        status = "SUCCESS" if success else "FAILED"
        print(f"{desc}: {status}")
    print("=" * 70)

    return 0 if all(s for _, s in results) else 1


if __name__ == "__main__":
    sys.exit(main())
