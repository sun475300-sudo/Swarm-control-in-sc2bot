#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete Training Workflow

This script orchestrates the entire training workflow:
1. Start game training
2. Post-training logic check and error fixing
3. Full file logic check
4. Replay comparison learning and data application
5. Replay learning data comparison analysis and learning
6. Process cleanup and data organization
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent


def run_command(
        cmd: list,
        description: str,
        cwd: Optional[Path] = None) -> bool:
    """Run a command and return success status"""
    print("\n" + "=" * 70)
    print(description)
    print("=" * 70)
    print()

    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else str(PROJECT_ROOT),
            check=False
        )
        success = result.returncode == 0
        if success:
            print(f"\n[SUCCESS] {description} completed")
        else:
            print(
                f"\n[WARNING] {description} completed with exit code {result.returncode}")
        return success
    except Exception as e:
        print(f"\n[ERROR] {description} failed: {e}")
        return False


def start_game_training() -> bool:
    """Start game training"""
    print("\n" + "=" * 70)
    print("STEP 1: STARTING GAME TRAINING")
    print("=" * 70)
    print()
    print("[INFO] Starting game training with: python run_with_training.py")
    print("[INFO] Training will run until stopped (Ctrl+C)")
    print("[INFO] Monitor progress at: http://localhost:8001")
    print()
    print("[NOTE] Press Ctrl+C to stop training and proceed to next steps")
    print()

    training_script = PROJECT_ROOT / "run_with_training.py"
    if not training_script.exists():
        print(f"[ERROR] {training_script} not found")
        return False

    try:
        subprocess.run(
            [sys.executable, str(training_script)],
            cwd=str(PROJECT_ROOT)
        )
        print("\n[INFO] Training stopped")
        return True
    except KeyboardInterrupt:
        print("\n[INFO] Training interrupted by user")
        print("[INFO] Proceeding to post-training checks...")
        return True
    except Exception as e:
        print(f"[ERROR] Training failed: {e}")
        return False


def run_post_training_checks() -> bool:
    """Run post-training logic check and error fixing"""
    print("\n" + "=" * 70)
    print("STEP 2: POST-TRAINING LOGIC CHECK AND ERROR FIXING")
    print("=" * 70)
    print()

    # Check for logic check script
    logic_check_script = PROJECT_ROOT / "tools" / "full_logic_check.py"
    if logic_check_script.exists():
        success = run_command(
            [sys.executable, str(logic_check_script)],
            "Running full logic check",
            PROJECT_ROOT
        )
    else:
        print("[INFO] full_logic_check.py not found, skipping")
        success = True

    # Check for error fixer
    error_fixer = PROJECT_ROOT / "tools" / "auto_error_fixer.py"
    if error_fixer.exists():
        success = run_command(
            [sys.executable, str(error_fixer)],
            "Running auto error fixer",
            PROJECT_ROOT
        ) and success
    else:
        print("[INFO] auto_error_fixer.py not found, skipping")

    return success


def run_full_file_logic_check() -> bool:
    """Run full file logic check"""
    print("\n" + "=" * 70)
    print("STEP 3: FULL FILE LOGIC CHECK")
    print("=" * 70)
    print()

    # Use comprehensive code style check
    style_check = PROJECT_ROOT / "tools" / "comprehensive_code_style_check.py"
    if style_check.exists():
        return run_command(
            [sys.executable, str(style_check)],
            "Running comprehensive code style check",
            PROJECT_ROOT
        )
    else:
        print("[INFO] comprehensive_code_style_check.py not found, skipping")
        return True


def run_replay_comparison_learning() -> bool:
    """Run replay comparison learning and apply data"""
    print("\n" + "=" * 70)
    print("STEP 4: REPLAY COMPARISON LEARNING AND DATA APPLICATION")
    print("=" * 70)
    print()

    # Run comparison analysis
    comparison_script = PROJECT_ROOT / "tools" / "compare_pro_vs_training_replays.py"
    if comparison_script.exists():
        success = run_command(
            [sys.executable, str(comparison_script)],
            "Running replay comparison analysis",
            PROJECT_ROOT
        )
    else:
        print("[INFO] compare_pro_vs_training_replays.py not found")
        success = True

    # Apply differences
    apply_script = PROJECT_ROOT / "tools" / "apply_differences_and_learn.py"
    if apply_script.exists():
        success = run_command(
            [sys.executable, str(apply_script)],
            "Applying differences and learning",
            PROJECT_ROOT
        ) and success
    else:
        print("[INFO] apply_differences_and_learn.py not found")

    return success


def run_replay_learning_comparison() -> bool:
    """Run replay learning data comparison analysis and learning"""
    print("\n" + "=" * 70)
    print("STEP 5: REPLAY LEARNING DATA COMPARISON ANALYSIS AND LEARNING")
    print("=" * 70)
    print()

    # Run comparison and learning workflow
    workflow_script = PROJECT_ROOT / "tools" / "post_training_learning_workflow.py"
    if workflow_script.exists():
        return run_command(
            [sys.executable, str(workflow_script)],
            "Running replay learning comparison and analysis",
            PROJECT_ROOT
        )
    else:
        print("[INFO] post_training_learning_workflow.py not found")
        return True


def cleanup_and_organize() -> bool:
    """Cleanup processes and organize unnecessary data"""
    print("\n" + "=" * 70)
    print("STEP 6: CLEANUP AND DATA ORGANIZATION")
    print("=" * 70)
    print()

    # Cleanup logs
    cleanup_logs = PROJECT_ROOT / "tools" / "cleanup_logs.py"
    if cleanup_logs.exists():
        run_command(
            [sys.executable, str(cleanup_logs)],
            "Cleaning up log files",
            PROJECT_ROOT
        )

    # Cleanup unnecessary files
    cleanup_files = PROJECT_ROOT / "tools" / "cleanup_unnecessary_files_auto.py"
    if cleanup_files.exists():
        run_command(
            [sys.executable, str(cleanup_files)],
            "Cleaning up unnecessary files",
            PROJECT_ROOT
        )

    # Comprehensive cleanup
    comprehensive_cleanup = PROJECT_ROOT / "tools" / "comprehensive_cleanup.py"
    if comprehensive_cleanup.exists():
        run_command(
            [sys.executable, str(comprehensive_cleanup)],
            "Running comprehensive cleanup",
            PROJECT_ROOT
        )

    print("\n[SUCCESS] Cleanup and organization completed")
    return True


def main():
    """Main workflow function"""
    print("\n" + "=" * 70)
    print("COMPLETE TRAINING WORKFLOW")
    print("=" * 70)
    print()
    print("This workflow will execute:")
    print("  1. Start game training (python run_with_training.py)")
    print("  2. Post-training logic check and error fixing")
    print("  3. Full file logic check")
    print("  4. Replay comparison learning and data application")
    print("  5. Replay learning data comparison analysis and learning")
    print("  6. Cleanup and data organization")
    print()
    print("[NOTE] You can interrupt training with Ctrl+C to proceed to next steps")
    print()

    # Step 1: Start game training
    if not start_game_training():
        print("[WARNING] Training failed, but continuing with remaining steps...")

    # Wait a bit before proceeding
    print("\n[INFO] Waiting 5 seconds before proceeding to post-training steps...")
    time.sleep(5)

    # Step 2: Post-training checks
    run_post_training_checks()

    # Step 3: Full file logic check
    run_full_file_logic_check()

    # Step 4: Replay comparison learning
    run_replay_comparison_learning()

    # Step 5: Replay learning comparison
    run_replay_learning_comparison()

    # Step 6: Cleanup
    cleanup_and_organize()

    print("\n" + "=" * 70)
    print("WORKFLOW COMPLETE")
    print("=" * 70)
    print()
    print("[SUCCESS] All steps completed!")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Workflow interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Workflow failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
