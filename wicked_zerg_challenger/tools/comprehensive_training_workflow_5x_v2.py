# -*- coding: utf-8 -*-
"""
Comprehensive Training Workflow - 5 Iterations (Version 2)

This workflow executes:
1. Auto error fixing (tools/auto_error_fixer.py)
2. Code quality check (tools/code_quality_improver.py)
3. Game training (run_with_training.py)
4. Replay build order learning (local_training/scripts/replay_build_order_learner.py)
5. Replay comparison analysis (local_training/strategy_audit.py)
6. Repeat 5 times
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple

def run_command(cmd: List[str], cwd: Path, description: str, timeout: int = 3600) -> Tuple[bool, str]:
    """Run a command and return success status and output"""
    print(f"\n{'='*70}")
    print(f"[STEP] {description}")
    print(f"{'='*70}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
            encoding='utf-8',
            errors='ignore',
            timeout=timeout
        )
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        success = result.returncode == 0
        return success, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        print(f"[WARNING] Command timed out after {timeout} seconds")
        return False, "Timeout"
    except Exception as e:
        print(f"[ERROR] Failed to run command: {e}")
        return False, str(e)

def main():
    project_root = Path(__file__).parent.parent
    
    print("=" * 70)
    print("COMPREHENSIVE TRAINING WORKFLOW - 5 ITERATIONS (VERSION 2)")
    print("=" * 70)
    print("\nThis workflow will execute:")
    print("  1. Auto error fixing (tools/auto_error_fixer.py)")
    print("  2. Code quality check (tools/code_quality_improver.py)")
    print("  3. Game training (run_with_training.py)")
    print("  4. Replay build order learning (replay_build_order_learner.py)")
    print("  5. Replay comparison analysis (strategy_audit.py)")
    print("  6. Repeat 5 times")
    print("=" * 70)
    
    # Script paths
    auto_error_fixer = project_root / "tools" / "auto_error_fixer.py"
    code_quality_improver = project_root / "tools" / "code_quality_improver.py"
    run_training = project_root / "run_with_training.py"
    replay_learner = project_root / "local_training" / "scripts" / "replay_build_order_learner.py"
    strategy_audit = project_root / "local_training" / "strategy_audit.py"
    
    # Check if scripts exist
    scripts = {
        "Auto Error Fixer": auto_error_fixer,
        "Code Quality Improver": code_quality_improver,
        "Run Training": run_training,
        "Replay Learner": replay_learner,
        "Strategy Audit": strategy_audit
    }
    
    for name, script in scripts.items():
        if not script.exists():
            print(f"[ERROR] {name} script not found: {script}")
            sys.exit(1)
    
    successful_iterations = 0
    
    for iteration in range(1, 6):
        print(f"\n\n{'#'*70}")
        print(f"# ITERATION {iteration} / 5")
        print(f"{'#'*70}\n")
        
        iteration_success = True
        
        # Step 1: Auto error fixing
        print(f"\n[STEP 1] Running auto error fixing...")
        success1, _ = run_command(
            [sys.executable, str(auto_error_fixer)],
            project_root,
            f"Iteration {iteration} - Auto Error Fixing",
            timeout=600  # 10 minutes
        )
        
        if success1:
            print(f"[SUCCESS] Auto error fixing completed for iteration {iteration}")
        else:
            print(f"[WARNING] Auto error fixing had issues in iteration {iteration}, continuing...")
            iteration_success = False
        
        # Step 2: Code quality check
        print(f"\n[STEP 2] Running code quality check...")
        success2, _ = run_command(
            [sys.executable, str(code_quality_improver)],
            project_root,
            f"Iteration {iteration} - Code Quality Check",
            timeout=600  # 10 minutes
        )
        
        if success2:
            print(f"[SUCCESS] Code quality check completed for iteration {iteration}")
        else:
            print(f"[WARNING] Code quality check had issues in iteration {iteration}, continuing...")
            iteration_success = False
        
        # Step 3: Game training
        print(f"\n[STEP 3] Running game training...")
        success3, _ = run_command(
            [sys.executable, str(run_training)],
            project_root,
            f"Iteration {iteration} - Game Training",
            timeout=3600  # 60 minutes
        )
        
        if success3:
            print(f"[SUCCESS] Game training completed for iteration {iteration}")
        else:
            print(f"[WARNING] Game training had issues in iteration {iteration}, continuing...")
            iteration_success = False
        
        # Step 4: Replay build order learning
        print(f"\n[STEP 4] Running replay build order learning...")
        success4, _ = run_command(
            [sys.executable, str(replay_learner)],
            project_root,
            f"Iteration {iteration} - Replay Build Order Learning",
            timeout=1800  # 30 minutes
        )
        
        if success4:
            print(f"[SUCCESS] Replay build order learning completed for iteration {iteration}")
            print("[INFO] Learned parameters will be automatically applied via config.py")
        else:
            print(f"[WARNING] Replay build order learning had issues in iteration {iteration}, continuing...")
            iteration_success = False
        
        # Step 5: Replay comparison analysis
        print(f"\n[STEP 5] Running replay comparison analysis...")
        success5, _ = run_command(
            [sys.executable, str(strategy_audit)],
            project_root,
            f"Iteration {iteration} - Replay Comparison Analysis",
            timeout=1800  # 30 minutes
        )
        
        if success5:
            print(f"[SUCCESS] Replay comparison analysis completed for iteration {iteration}")
        else:
            print(f"[WARNING] Replay comparison analysis had issues in iteration {iteration}, continuing...")
            iteration_success = False
        
        if iteration_success:
            successful_iterations += 1
        
        print(f"\n{'='*70}")
        print(f"? ITERATION {iteration} / 5 COMPLETED")
        print(f"   Auto Error Fixing: {'?' if success1 else '?'}")
        print(f"   Code Quality Check: {'?' if success2 else '?'}")
        print(f"   Game Training: {'?' if success3 else '?'}")
        print(f"   Replay Build Order Learning: {'?' if success4 else '?'}")
        print(f"   Replay Comparison Analysis: {'?' if success5 else '?'}")
        print(f"{'='*70}")
        
        if iteration < 5:
            print(f"\nWaiting 10 seconds before next iteration...")
            time.sleep(10)
    
    print(f"\n\n{'#'*70}")
    print("# ALL 5 ITERATIONS COMPLETED")
    print(f"{'#'*70}")
    print(f"\nSummary:")
    print(f"  - Successful iterations: {successful_iterations} / 5")
    print(f"  - Learned build orders: local_training/scripts/learned_build_orders.json")
    print(f"  - Comparison reports: local_training/comparison_reports/")
    print(f"\nCheck results:")
    print(f"  python tools\\show_learning_rate.py")
    print(f"  python tools\\monitor_training_progress.py")
    print(f"\n{'#'*70}")

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
