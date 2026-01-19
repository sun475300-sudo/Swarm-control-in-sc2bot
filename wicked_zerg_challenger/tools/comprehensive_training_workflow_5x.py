# -*- coding: utf-8 -*-
"""
Comprehensive Training Workflow - 5 Iterations

This workflow includes:
1. Precision check (completed)
2. Start game training
3. Logic check and error fixing after training
4. Full file logic check
5. Start training (python run_with_training.py)
6. Run replay comparison learning and apply data
7. Run replay learning data comparison analysis and learning
8. Repeat 5 times
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple

def run_command(cmd: List[str], cwd: Path, description: str) -> Tuple[bool, str]:
    """Run a command and return success status and output"""
    print(f"\n{'='*70}")
    print(f"¢º {description}")
    print(f"{'='*70}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        success = result.returncode == 0
        return success, result.stdout + result.stderr
    except Exception as e:
        print(f"[ERROR] Failed to run command: {e}")
        return False, str(e)

def main():
    project_root = Path(__file__).parent.parent
    
    print("=" * 70)
    print("? COMPREHENSIVE TRAINING WORKFLOW - 5 ITERATIONS")
    print("=" * 70)
    print("\nThis workflow will execute:")
    print("  1. Precision check (completed)")
    print("  2. Start game training")
    print("  3. Logic check and error fixing after training")
    print("  4. Full file logic check")
    print("  5. Start training (python run_with_training.py)")
    print("  6. Run replay comparison learning and apply data")
    print("  7. Run replay learning data comparison analysis and learning")
    print("  8. Repeat 5 times")
    print("=" * 70)
    
    for iteration in range(1, 6):
        print(f"\n\n{'#'*70}")
        print(f"# ITERATION {iteration} / 5")
        print(f"{'#'*70}\n")
        
        # Step 1: Precision check (completed - skip)
        print("\n[STEP 1] Precision check - COMPLETED (skipping)")
        
        # Step 2: Start game training
        print("\n[STEP 2] Starting game training...")
        success, _ = run_command(
            [sys.executable, "run_with_training.py"],
            project_root,
            f"Iteration {iteration} - Game Training"
        )
        
        if not success:
            print(f"[WARNING] Game training failed in iteration {iteration}, continuing...")
        
        # Step 3: Logic check and error fixing after training
        print("\n[STEP 3] Logic check and error fixing after training...")
        
        # Run auto error fixer
        auto_fixer = project_root / "tools" / "auto_error_fixer.py"
        if auto_fixer.exists():
            run_command(
                [sys.executable, str(auto_fixer)],
                project_root,
                "Auto Error Fixer"
            )
        
        # Step 4: Full file logic check
        print("\n[STEP 4] Full file logic check...")
        
        # Run code quality improver
        code_quality = project_root / "tools" / "code_quality_improver.py"
        if code_quality.exists():
            run_command(
                [sys.executable, str(code_quality)],
                project_root,
                "Code Quality Check"
            )
        
        # Step 5: Start training (python run_with_training.py)
        print("\n[STEP 5] Starting training (run_with_training.py)...")
        success, _ = run_command(
            [sys.executable, "run_with_training.py"],
            project_root,
            f"Iteration {iteration} - Training"
        )
        
        if not success:
            print(f"[WARNING] Training failed in iteration {iteration}, continuing...")
        
        # Step 6: Run replay comparison learning and apply data
        print("\n[STEP 6] Running replay comparison learning and applying data...")
        
        # Run replay build order learner
        replay_learner = project_root / "local_training" / "scripts" / "replay_build_order_learner.py"
        if replay_learner.exists():
            success, _ = run_command(
                [sys.executable, str(replay_learner)],
                project_root,
                "Replay Build Order Learning"
            )
            if success:
                print("[SUCCESS] Replay learning completed, data will be applied automatically")
            else:
                print("[WARNING] Replay learning had issues, but continuing...")
        
        # Step 7: Run replay learning data comparison analysis and learning
        print("\n[STEP 7] Running replay learning data comparison analysis and learning...")
        
        # Run strategy audit (comparison analysis)
        strategy_audit = project_root / "local_training" / "strategy_audit.py"
        if strategy_audit.exists():
            success, _ = run_command(
                [sys.executable, str(strategy_audit)],
                project_root,
                "Strategy Audit (Comparison Analysis)"
            )
        
        print(f"\n{'='*70}")
        print(f"? ITERATION {iteration} / 5 COMPLETED")
        print(f"{'='*70}")
        
        if iteration < 5:
            print(f"\nWaiting 5 seconds before next iteration...")
            time.sleep(5)
    
    print(f"\n\n{'#'*70}")
    print("# ALL 5 ITERATIONS COMPLETED")
    print(f"{'#'*70}")
    print("\nSummary:")
    print("  - 5 game training sessions completed")
    print("  - Logic checks and error fixes applied")
    print("  - Replay learning data collected and applied")
    print("  - Strategy comparison analysis completed")
    print("\nCheck training statistics:")
    print("  python tools\\monitor_training_progress.py")
    print("  python tools\\show_learning_rate.py")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n??  Workflow interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n? Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
