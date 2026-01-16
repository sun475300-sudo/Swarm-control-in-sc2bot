#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Game Training Workflow - Precision check, game training, and post-training checks
"""

import sys
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

# Setup encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

PROJECT_ROOT = Path(__file__).parent.parent


def run_precision_check() -> bool:
    """Run precision code style check"""
    print("\n" + "=" * 70)
    print("STEP 1: PRECISION CODE STYLE CHECK")
    print("=" * 70)
    print()

    check_script = PROJECT_ROOT / "tools" / "comprehensive_code_style_check.py"
    if not check_script.exists():
        print(f"[ERROR] {check_script} not found")
        return False

    print("[INFO] Running comprehensive code style check...")
    try:
        result = subprocess.run(
            [sys.executable, str(check_script)],
            cwd=str(PROJECT_ROOT),
            timeout=600,  # 10 minutes timeout
            capture_output=False
        )
        if result.returncode == 0:
            print("[SUCCESS] Precision check completed")
            return True
        else:
            print("[WARNING] Precision check completed with warnings")
            return True  # Continue even with warnings
    except subprocess.TimeoutExpired:
        print("[ERROR] Precision check timed out")
        return False
    except Exception as e:
        print(f"[ERROR] Precision check failed: {e}")
        return False


def start_game_training() -> bool:
    """Start game training"""
    print("\n" + "=" * 70)
    print("STEP 2: STARTING GAME TRAINING")
    print("=" * 70)
    print()

    training_script = PROJECT_ROOT / "run_with_training.py"
    if not training_script.exists():
        print(f"[ERROR] {training_script} not found")
        return False

    print("[INFO] Starting game training...")
    print("[INFO] Training will run until stopped (Ctrl+C)")
    print("[INFO] Monitor progress at: http://localhost:8001")
    print()
    print("[NOTE] Press Ctrl+C to stop training and proceed to post-training checks")
    print()

    try:
        # Start training
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
        import traceback
        traceback.print_exc()
        return False


def run_post_training_logic_check() -> bool:
    """Run post-training logic check and error fixing"""
    print("\n" + "=" * 70)
    print("STEP 3: POST-TRAINING LOGIC CHECK AND ERROR FIXING")
    print("=" * 70)
    print()

    # 3.1: Full logic check
    print("[3.1] Running full logic check...")
    logic_check_script = PROJECT_ROOT / "tools" / "full_logic_check.py"
    if logic_check_script.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(logic_check_script)],
                cwd=str(PROJECT_ROOT),
                timeout=300,
                capture_output=False
            )
            if result.returncode != 0:
                print("[WARNING] Logic check found errors")
        except Exception as e:
            print(f"[WARNING] Logic check failed: {e}")
    else:
        print("[WARNING] full_logic_check.py not found")

    # 3.2: Auto error fixer
    print("\n[3.2] Running auto error fixer...")
    error_fixer_script = PROJECT_ROOT / "tools" / "auto_error_fixer.py"
    if error_fixer_script.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(error_fixer_script), "--all"],
                cwd=str(PROJECT_ROOT),
                timeout=300,
                capture_output=False
            )
            if result.returncode == 0:
                print("[SUCCESS] Auto error fixer completed")
            else:
                print("[WARNING] Auto error fixer completed with warnings")
        except Exception as e:
            print(f"[WARNING] Auto error fixer failed: {e}")
    else:
        print("[WARNING] auto_error_fixer.py not found")

    # 3.3: Re-run logic check after fixes
    print("\n[3.3] Re-running logic check after fixes...")
    if logic_check_script.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(logic_check_script)],
                cwd=str(PROJECT_ROOT),
                timeout=300,
                capture_output=False
            )
            if result.returncode == 0:
                print("[SUCCESS] Post-fix logic check passed")
                return True
            else:
                print("[WARNING] Post-fix logic check found remaining errors")
                return False
        except Exception as e:
            print(f"[WARNING] Post-fix logic check failed: {e}")
            return False

    return True


def run_full_file_logic_check() -> bool:
    """Run full file logic check"""
    print("\n" + "=" * 70)
    print("STEP 4: FULL FILE LOGIC CHECK")
    print("=" * 70)
    print()

    logic_check_script = PROJECT_ROOT / "tools" / "full_logic_check.py"
    if not logic_check_script.exists():
        print(f"[ERROR] {logic_check_script} not found")
        return False

    print("[INFO] Running comprehensive file logic check...")
    try:
        result = subprocess.run(
            [sys.executable, str(logic_check_script)],
            cwd=str(PROJECT_ROOT),
            timeout=600,
            capture_output=False
        )
        if result.returncode == 0:
            print("[SUCCESS] Full file logic check passed")
            return True
        else:
            print("[WARNING] Full file logic check found errors")
            return False
    except Exception as e:
        print(f"[ERROR] Full file logic check failed: {e}")
        return False


def main():
    """Main workflow"""
    print("=" * 70)
    print("GAME TRAINING WORKFLOW")
    print("=" * 70)
    print()
    print("This workflow will:")
    print("  1. Run precision code style check")
    print("  2. Start game training")
    print("  3. Run post-training logic check and error fixing")
    print("  4. Run full file logic check")
    print()

    # Step 1: Precision check
    if not run_precision_check():
        print("\n[ERROR] Precision check failed. Aborting workflow.")
        return 1

    # Step 2: Start game training
    if not start_game_training():
        print("\n[ERROR] Game training failed. Aborting workflow.")
        return 1

    # Step 3: Post-training logic check and error fixing
    if not run_post_training_logic_check():
        print("\n[WARNING] Post-training logic check found errors")
        # Continue anyway

    # Step 4: Full file logic check
    if not run_full_file_logic_check():
        print("\n[WARNING] Full file logic check found errors")
        return 1

    print("\n" + "=" * 70)
    print("WORKFLOW COMPLETE")
    print("=" * 70)
    print()
    print("All steps completed successfully!")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
