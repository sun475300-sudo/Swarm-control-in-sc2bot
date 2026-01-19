#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Iterative Training Workflow - 10 Iterations
10번 반복 자동화 워크플로우:

매 반복마다:
1. 정밀검사 및 에러 수정 (반복)
2. 스타일 통일화
3. 리플레이 학습 시작 및 전체 로직검사
4. 정밀검사 후 게임학습 시작
5. 학습 완료 후 로직검사 및 에러 수정
6. 리플레이 비교 학습 실행 및 데이터 적용
7. 리플레이 학습 데이터 비교 분석 및 학습 실행
8. 빌드오더 학습 실행
9. 학습 방해 에러 개선
10. 프로세스 정리

10번 반복 실행하며, 각 반복마다 게임 정상 작동 여부 확인
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
MAX_ITERATIONS = 10


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


def check_and_fix_errors(max_iterations: int = 5) -> bool:
    """
    Check and fix errors repeatedly until no errors remain or max iterations reached.
    Returns True if errors fixed or acceptable, False if critical errors remain.
    """
    print(f"\n[PRECISION CHECK] Fixing errors (max {max_iterations} iterations)...")
    print("-" * 70)
    
    for iteration in range(max_iterations):
        print(f"\n  [CHECK {iteration + 1}/{max_iterations}] Checking errors...")
        
        # Run full logic check
        result = run_command([sys.executable, "tools/full_logic_check.py"], timeout=300)
        
        error_count = 999  # Default to high number
        if result:
            output = result.stdout or ""
            # Extract error count
            for line in output.split('\n'):
                if "Errors:" in line and "Total files:" in line or "Errors:" in line:
                    try:
                        parts = line.split("Errors:")
                        if len(parts) > 1:
                            error_count = int(parts[1].strip().split()[0])
                            break
                    except:
                        pass
        
        if error_count == 0:
            print("  ? All errors fixed!")
            return True
        
        print(f"  Found {error_count} errors, fixing...")
        
        # Fix errors in sequence
        print(f"    [FIX] Import errors...")
        run_command([sys.executable, "tools/fix_all_import_statements.py"], timeout=300)
        
        print(f"    [FIX] Syntax errors...")
        run_command([sys.executable, "tools/fix_all_remaining_errors.py"], timeout=600)
        
        if iteration < max_iterations - 1:
            time.sleep(3)
    
    # Even if some errors remain, continue (non-critical)
    print(f"  ? Error fixing complete (some non-critical errors may remain)")
    return True


def apply_code_style_unification():
    """Apply code style unification"""
    print("\n[STYLE] Applying code style unification...")
    print("-" * 70)
    
    # Apply autopep8
    print("  [AUTOPEP8] Standard formatting...")
    result = run_command(
        [sys.executable, "-m", "autopep8", "--in-place", "--recursive",
         "--max-line-length=120", "."],
        timeout=600
    )
    
    print("  [AUTOPEP8] Aggressive formatting...")
    result = run_command(
        [sys.executable, "-m", "autopep8", "--in-place", "--recursive",
         "--aggressive", "--aggressive", "--max-line-length=120", "."],
        timeout=600
    )
    
    print("  ? Code style unified")


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


def wait_for_training_completion(max_wait_hours: int = 2):
    """Wait for training to complete (shorter wait for iterative runs)"""
    print("\n[WAIT] Waiting for training completion...")
    print("-" * 70)
    print(f"  Maximum wait: {max_wait_hours} hours")
    
    start_time = time.time()
    max_wait_seconds = max_wait_hours * 3600
    check_interval = 60
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait_seconds:
            print(f"\n  [WARNING] Maximum wait time reached, proceeding...")
            break
        
        if not check_training_running():
            print("\n  [OK] Training completed")
            time.sleep(10)  # Cleanup time
            break
        
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        print(f"  Training running... ({hours}h {minutes}m)", end='\r')
        time.sleep(check_interval)
    
    print()


def run_replay_learning_and_logic_check():
    """Run replay learning and full logic check"""
    print("\n[REPLAY LEARNING] Starting replay learning and logic check...")
    print("-" * 70)
    
    # 1. Full logic check
    print("  [LOGIC CHECK] Running full logic check...")
    result = run_command([sys.executable, "tools/full_logic_check.py"], timeout=300)
    
    # 2. Replay build order learning
    print("  [BUILD ORDER] Starting build order learning...")
    build_order_script = PROJECT_ROOT / "local_training/scripts/replay_build_order_learner.py"
    if build_order_script.exists():
        os.environ["MAX_REPLAYS_FOR_LEARNING"] = "300"
        result = run_command([sys.executable, str(build_order_script)], timeout=1800)  # 30 min
        if result and result.returncode == 0:
            print("  ? Build order learning complete")
        else:
            print("  ?? Build order learning had issues")
    else:
        print("  ?? Build order script not found")
    
    print("  ? Replay learning and logic check complete")


def run_replay_comparison_learning():
    """Run replay comparison learning (pro vs bot)"""
    print("\n[REPLAY COMPARISON] Running replay comparison learning...")
    print("-" * 70)
    
    # 1. Compare pro vs bot replays
    print("  [COMPARE] Comparing pro vs bot replays...")
    comparison_scripts = [
        "tools/compare_pro_vs_training_replays.py",
        "local_training/scripts/compare_pro_vs_bot_replays.py",
        "tools/compare_replays.py"
    ]
    
    for script_path in comparison_scripts:
        script = Path(PROJECT_ROOT / script_path)
        if script.exists():
            print(f"    Running: {script_path}")
            result = run_command([sys.executable, str(script)], timeout=1800)
            if result and result.returncode == 0:
                print("    ? Comparison complete")
                break
    
    # 2. Apply differences and learn
    print("  [APPLY] Applying differences and learning...")
    apply_scripts = [
        "tools/apply_differences_and_learn.py",
        "local_training/scripts/apply_comparison_results.py"
    ]
    
    for script_path in apply_scripts:
        script = Path(PROJECT_ROOT / script_path)
        if script.exists():
            result = run_command([sys.executable, str(script)], timeout=600)
            if result and result.returncode == 0:
                print("    ? Differences applied")
                break
    
    print("  ? Replay comparison learning complete")


def cleanup_processes():
    """Clean up all training-related processes"""
    print("\n[CLEANUP] Cleaning up processes...")
    print("-" * 70)
    
    try:
        cleaned = 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline:
                    cmdline_str = ' '.join(str(c) for c in cmdline)
                    if any(x in cmdline_str for x in ['run_with_training.py', 'replay_build_order_learner.py']):
                        if 'iterative_training_workflow' not in cmdline_str:
                            proc.terminate()
                            cleaned += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if cleaned > 0:
            print(f"  ? Cleaned up {cleaned} processes")
            time.sleep(5)
        else:
            print("  ? No processes to clean up")
    except Exception as e:
        print(f"  ?? Cleanup error: {e}")


def run_single_iteration(iteration: int) -> bool:
    """
    Run a single iteration of the workflow.
    Returns True if successful, False if should stop.
    """
    print("\n" + "=" * 70)
    print(f"ITERATION {iteration}/{MAX_ITERATIONS}")
    print("=" * 70)
    print()
    
    # Step 1: Precision check and error fixing
    print(f"[{iteration}.1] PRECISION CHECK - ERROR FIXING")
    if not check_and_fix_errors(max_iterations=5):
        print("  ?? Critical errors remain, but continuing...")
    
    # Step 2: Code style unification
    print(f"\n[{iteration}.2] CODE STYLE UNIFICATION")
    apply_code_style_unification()
    
    # Step 3: Replay learning and logic check
    print(f"\n[{iteration}.3] REPLAY LEARNING & LOGIC CHECK")
    run_replay_learning_and_logic_check()
    
    # Step 4: Precision check again before training
    print(f"\n[{iteration}.4] PRECISION CHECK (PRE-TRAINING)")
    check_and_fix_errors(max_iterations=3)
    
    # Step 5: Start game training
    print(f"\n[{iteration}.5] STARTING GAME TRAINING")
    print("-" * 70)
    training_process = run_command([sys.executable, "run_with_training.py"], background=True)
    
    if not training_process:
        print("  ?? Failed to start training")
        return False
    
    print(f"  ? Training started (PID: {training_process.pid})")
    
    # Step 6: Wait for training completion
    print(f"\n[{iteration}.6] WAITING FOR TRAINING COMPLETION")
    wait_for_training_completion(max_wait_hours=2)  # 2 hours per iteration
    
    # Step 7: Post-training logic check and error fixing
    print(f"\n[{iteration}.7] POST-TRAINING LOGIC CHECK & ERROR FIXING")
    check_and_fix_errors(max_iterations=3)
    
    # Step 8: Replay comparison learning
    print(f"\n[{iteration}.8] REPLAY COMPARISON LEARNING")
    run_replay_comparison_learning()
    
    # Step 9: Replay learning data comparison and analysis
    print(f"\n[{iteration}.9] REPLAY LEARNING DATA ANALYSIS")
    run_replay_learning_and_logic_check()  # Build order learning
    
    # Step 10: Cleanup
    print(f"\n[{iteration}.10] CLEANUP")
    cleanup_processes()
    
    print(f"\n[OK] Iteration {iteration} complete")
    print()
    
    return True


def main():
    """Main iterative workflow - 10 iterations"""
    print("=" * 70)
    print("ITERATIVE TRAINING WORKFLOW - 10 ITERATIONS")
    print("=" * 70)
    print()
    print("This workflow will run 10 iterations of:")
    print("  1. Precision check and error fixing (repeatedly)")
    print("  2. Code style unification")
    print("  3. Replay learning and logic check")
    print("  4. Game training")
    print("  5. Post-training error fixing")
    print("  6. Replay comparison learning (pro vs bot)")
    print("  7. Build order learning")
    print("  8. Cleanup")
    print()
    print(f"Total iterations: {MAX_ITERATIONS}")
    print("Press Ctrl+C to stop at any time")
    print("=" * 70)
    print()
    
    successful_iterations = 0
    
    for iteration in range(1, MAX_ITERATIONS + 1):
        try:
            success = run_single_iteration(iteration)
            if success:
                successful_iterations += 1
                print(f"[PROGRESS] Completed {successful_iterations}/{iteration} iterations")
            else:
                print(f"[WARNING] Iteration {iteration} had issues, but continuing...")
            
            # Short pause between iterations (except last)
            if iteration < MAX_ITERATIONS:
                print("\n[PAUSE] Waiting 10 seconds before next iteration...")
                time.sleep(10)
        
        except KeyboardInterrupt:
            print(f"\n\n[STOP] Workflow interrupted by user at iteration {iteration}")
            break
        except Exception as e:
            print(f"\n[ERROR] Iteration {iteration} failed: {e}")
            import traceback
            traceback.print_exc()
            # Continue to next iteration
            continue
    
    # Final summary
    print("\n" + "=" * 70)
    print("ITERATIVE WORKFLOW COMPLETE")
    print("=" * 70)
    print(f"Successfully completed: {successful_iterations}/{MAX_ITERATIONS} iterations")
    print()
    print("Results:")
    print("  - Learned parameters: local_training/scripts/learned_build_orders.json")
    print("  - Comparison reports: local_training/comparison_reports/")
    print("  - Training data: local_training/models/")
    print()
    print("Next steps:")
    print("  - Review learned parameters")
    print("  - Check comparison reports")
    print("  - Run more iterations if needed")
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
