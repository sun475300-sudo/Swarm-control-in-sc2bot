#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete Workflow: Code Style, Replay Learning, Game Training, Comparison, and Logic Check
"""

import sys
import subprocess
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def run_command(cmd: list, description: str, timeout: int = 3600) -> bool:
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
            timeout=timeout
        )
        if result.returncode == 0:
            print(f"SUCCESS: {description}")
            if result.stdout:
                lines = result.stdout.split('\n')
                print('\n'.join(lines[-50:]))  # Last 50 lines
            return True
        else:
            print(f"ERROR: {description}")
            if result.stderr:
                lines = result.stderr.split('\n')
                print('\n'.join(lines[-50:]))  # Last 50 lines
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
    print("COMPLETE WORKFLOW")
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
        # Step 1: Code style unification (quick check only)
        (['python', 'tools/comprehensive_code_style_check.py'],
         "Code Style Unification", 600),

        # Step 2: Replay learning
        (['python', 'local_training/scripts/replay_build_order_learner.py'],
         "Replay Learning", 7200),

        # Step 3: Replay comparison analysis
        (['python', 'tools/compare_pro_vs_training_replays.py'],
         "Replay Comparison Analysis", 600),

        # Step 4: Apply differences and learn
        (['python', 'tools/apply_differences_and_learn.py'],
         "Apply Differences and Learn", 600),

        # Step 5: Full logic check
        (['python', 'tools/full_logic_check.py'],
         "Full Logic Check", 300),
    ]

    results = []
    for cmd, desc, timeout in steps:
        success = run_command(cmd, desc, timeout)
        results.append((desc, success))
        if not success and desc != "Code Style Unification":
            print(f"\nWARNING: {desc} failed, but continuing...")
        time.sleep(2)

    print("\n" + "=" * 70)
    print("WORKFLOW SUMMARY")
    print("=" * 70)
    for desc, success in results:
        status = "SUCCESS" if success else "FAILED"
        print(f"{desc}: {status}")
    print("=" * 70)

    # Game training is separate and should be started manually after this
    print("\n" + "=" * 70)
    print("NEXT STEP: Start Game Training")
    print("=" * 70)
    print("Run: python run_with_training.py")
    print("Or: bat\\start_local_training.bat")
    print("=" * 70)

    return 0 if all(s for _, s in results) else 1


if __name__ == "__main__":
    sys.exit(main())
