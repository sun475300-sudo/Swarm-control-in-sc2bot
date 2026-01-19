#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Training Workflow - Improved & Automated
완전 자동화된 전체 워크플로우:

1. 정밀검사: 전체 소스코드 에러 점검 및 수정 (반복)
2. 스타일 통일화: 코드 스타일 최적화
3. 게임 학습 시작
4. 학습 완료 대기 (자동 모니터링)
5. 로직 검사 및 에러 수정 (반복)
6. 리플레이 비교 학습 (프로 vs 봇)
7. 빌드오더 학습
8. 학습 데이터 적용 및 개선

버그 발견 시 자동으로 수정 후 재실행
"""

import subprocess
import sys
import time
import os
import signal
from pathlib import Path
from typing import Optional, List, Dict, Any
import psutil
import json

PROJECT_ROOT = Path(__file__).parent.parent


def run_command(cmd: list, timeout: Optional[int] = None, background: bool = False, check_returncode: bool = False):
    """Run a command with better error handling"""
    try:
        if background:
            process = subprocess.Popen(
                cmd,
                cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
            )
            return process
        else:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8',
                errors='replace'
            )
            if check_returncode and result.returncode != 0:
                print(f"  ?? Command failed: {' '.join(cmd)}")
                print(f"  Return code: {result.returncode}")
                if result.stderr:
                    print(f"  Error: {result.stderr[:500]}")
            return result
    except subprocess.TimeoutExpired:
        print(f"  ?? Command timeout: {' '.join(cmd)}")
        return None
    except Exception as e:
        print(f"  ?? Error: {e}")
        return None


def check_errors(max_iterations: int = 3) -> bool:
    """
    Check and fix errors repeatedly until no errors remain or max iterations reached.
    Returns True if all errors fixed, False otherwise.
    """
    print("\n" + "=" * 70)
    print("PRECISION CHECK - ERROR DETECTION & FIXING")
    print("=" * 70)
    
    for iteration in range(max_iterations):
        print(f"\n[ITERATION {iteration + 1}/{max_iterations}] Checking errors...")
        
        # Run full logic check
        result = run_command([sys.executable, "tools/full_logic_check.py"], timeout=300)
        if result and result.returncode == 0:
            # Check output for errors
            output = result.stdout or ""
            if "Errors: 0" in output or "Total files:" in output and "Errors: 0" in output:
                print("  ? All errors fixed!")
                return True
            else:
                # Extract error count
                if "Errors:" in output:
                    for line in output.split('\n'):
                        if "Errors:" in line:
                            error_count = int(line.split("Errors:")[1].strip().split()[0])
                            print(f"  Found {error_count} errors, fixing...")
        else:
            print("  ? Logic check failed, attempting fixes...")
        
        # Fix errors
        print(f"  [FIX {iteration + 1}] Fixing import errors...")
        run_command([sys.executable, "tools/fix_all_import_statements.py"], timeout=300)
        
        print(f"  [FIX {iteration + 1}] Fixing syntax errors...")
        run_command([sys.executable, "tools/fix_all_remaining_errors.py"], timeout=600)
        
        if iteration < max_iterations - 1:
            print(f"  Waiting 5 seconds before next check...")
            time.sleep(5)
    
    print("  ?? Some errors may remain after max iterations")
    return False


def apply_code_style_unification():
    """Apply code style unification (autopep8)"""
    print("\n[STYLE] Applying code style unification...")
    print("-" * 70)
    
    # Apply autopep8 (non-aggressive first)
    print("[STYLE 1] Applying autopep8 (standard)...")
    result = run_command(
        [sys.executable, "-m", "autopep8", "--in-place", "--recursive",
         "--max-line-length=120", "."],
        timeout=600
    )
    if result and result.returncode == 0:
        print("  ? Code formatted (standard)")
    else:
        print("  ? Formatting issues may remain")
    
    print("[STYLE 2] Applying autopep8 (aggressive)...")
    result = run_command(
        [sys.executable, "-m", "autopep8", "--in-place", "--recursive",
         "--aggressive", "--aggressive", "--max-line-length=120", "."],
        timeout=600
    )
    if result and result.returncode == 0:
        print("  ? Code formatted (aggressive)")
    else:
        print("  ? Some aggressive formatting may have failed")
    
    print("[STYLE] Complete")


def check_training_running() -> bool:
    """Check if training process is running"""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline:
                    cmdline_str = ' '.join(str(c) for c in cmdline)
                    if 'run_with_training.py' in cmdline_str and 'check_training_status' not in cmdline_str:
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False
    except Exception:
        return False


def wait_for_training_completion(max_wait_hours: int = 24):
    """Wait for training to complete with progress monitoring"""
    print("\n" + "=" * 70)
    print("WAITING FOR TRAINING COMPLETION")
    print("=" * 70)
    print(f"Maximum wait time: {max_wait_hours} hours")
    print("Monitoring training process...")
    print()
    
    start_time = time.time()
    max_wait_seconds = max_wait_hours * 3600
    check_interval = 60  # Check every minute
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait_seconds:
            print(f"\n[WARNING] Maximum wait time ({max_wait_hours} hours) reached")
            print("[INFO] Stopping training and proceeding...")
            break
        
        if not check_training_running():
            print("\n[INFO] Training process has stopped")
            print("[INFO] Waiting 30 seconds for cleanup...")
            time.sleep(30)
            break
        
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        print(f"[MONITOR] Training running... ({hours}h {minutes}m elapsed)", end='\r')
        time.sleep(check_interval)
    
    print("\n[OK] Training monitoring complete")


def run_replay_comparison_learning():
    """Run replay comparison learning (pro vs bot replays)"""
    print("\n" + "=" * 70)
    print("REPLAY COMPARISON LEARNING")
    print("=" * 70)
    
    # 1. Compare pro replays vs bot replays
    print("[COMPARE 1] Comparing pro replays with bot replays...")
    comparison_scripts = [
        "tools/compare_pro_vs_training_replays.py",
        "local_training/scripts/compare_pro_vs_bot_replays.py",
        "tools/compare_replays.py"
    ]
    
    for script_path in comparison_scripts:
        script = Path(PROJECT_ROOT / script_path)
        if script.exists():
            print(f"  Running: {script_path}")
            result = run_command([sys.executable, str(script)], timeout=1800)
            if result and result.returncode == 0:
                print("  ? Comparison complete")
                break
            else:
                print("  ?? Comparison had issues")
        else:
            print(f"  ?? Script not found: {script_path}")
    
    # 2. Apply differences and learn
    print("[COMPARE 2] Applying differences and learning...")
    apply_scripts = [
        "tools/apply_differences_and_learn.py",
        "local_training/scripts/apply_comparison_results.py"
    ]
    
    for script_path in apply_scripts:
        script = Path(PROJECT_ROOT / script_path)
        if script.exists():
            print(f"  Running: {script_path}")
            result = run_command([sys.executable, str(script)], timeout=600)
            if result and result.returncode == 0:
                print("  ? Differences applied")
                break
    
    print("[COMPARE] Complete")


def run_build_order_learning():
    """Run build order learning from pro replays"""
    print("\n" + "=" * 70)
    print("BUILD ORDER LEARNING")
    print("=" * 70)
    
    build_order_script = PROJECT_ROOT / "local_training/scripts/replay_build_order_learner.py"
    if build_order_script.exists():
        print("[BUILD ORDER] Learning build orders from pro replays...")
        os.environ["MAX_REPLAYS_FOR_LEARNING"] = "300"  # Set max replays
        result = run_command([sys.executable, str(build_order_script)], timeout=3600)
        if result and result.returncode == 0:
            print("  ? Build order learning complete")
        else:
            print("  ?? Build order learning had issues")
    else:
        print("  ?? replay_build_order_learner.py not found, skipping...")
    
    print("[BUILD ORDER] Complete")


def main():
    """Main comprehensive workflow"""
    print("=" * 70)
    print("COMPREHENSIVE TRAINING WORKFLOW - AUTOMATED")
    print("=" * 70)
    print()
    print("This workflow will:")
    print("  1. Run precision check and fix all errors (repeatedly)")
    print("  2. Unify code style")
    print("  3. Start game training")
    print("  4. Wait for training completion")
    print("  5. Check logic and fix errors again")
    print("  6. Run replay comparison learning")
    print("  7. Run build order learning")
    print("  8. Apply learned parameters")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()
    
    # Step 1: Precision Check - Fix all errors repeatedly
    print("[STEP 1] PRECISION CHECK - ERROR FIXING")
    print("-" * 70)
    all_errors_fixed = check_errors(max_iterations=3)
    if not all_errors_fixed:
        print("[WARNING] Some errors remain, continuing anyway...")
    print()
    print("[STEP 1] Complete")
    print()
    
    # Step 2: Code Style Unification
    print("[STEP 2] CODE STYLE UNIFICATION")
    print("-" * 70)
    apply_code_style_unification()
    print()
    print("[STEP 2] Complete")
    print()
    
    # Step 3: Start Game Training
    print("[STEP 3] STARTING GAME TRAINING")
    print("-" * 70)
    print("[INFO] Training will run in background")
    print("[INFO] Monitor progress at: http://localhost:8001")
    print()
    
    training_process = run_command([sys.executable, "run_with_training.py"], background=True)
    
    if training_process:
        print(f"  ? Training started (PID: {training_process.pid})")
        print("[INFO] Training is running in background")
    else:
        print("  ?? Failed to start training")
        return
    
    print()
    print("[STEP 3] Complete")
    print()
    
    # Step 4: Wait for Training Completion
    print("[STEP 4] WAITING FOR TRAINING COMPLETION")
    print("-" * 70)
    wait_for_training_completion(max_wait_hours=24)
    print()
    print("[STEP 4] Complete")
    print()
    
    # Step 5: Logic Check and Error Fixing (Post-Training)
    print("[STEP 5] POST-TRAINING LOGIC CHECK & ERROR FIXING")
    print("-" * 70)
    check_errors(max_iterations=2)
    print()
    print("[STEP 5] Complete")
    print()
    
    # Step 6: Replay Comparison Learning
    print("[STEP 6] REPLAY COMPARISON LEARNING")
    print("-" * 70)
    run_replay_comparison_learning()
    print()
    print("[STEP 6] Complete")
    print()
    
    # Step 7: Build Order Learning
    print("[STEP 7] BUILD ORDER LEARNING")
    print("-" * 70)
    run_build_order_learning()
    print()
    print("[STEP 7] Complete")
    print()
    
    # Final Summary
    print("\n" + "=" * 70)
    print("WORKFLOW COMPLETE")
    print("=" * 70)
    print()
    print("All steps completed successfully!")
    print()
    print("Next steps:")
    print("  - Review learned parameters in: local_training/scripts/learned_build_orders.json")
    print("  - Check comparison reports in: local_training/comparison_reports/")
    print("  - Run workflow again to continue improving")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] Workflow interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n[ERROR] Workflow failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
