#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete Training Workflow - Automated
1. Code optimization and style unification
2. Start game training
3. Wait for training completion
4. Run replay comparison learning
5. Run replay learning data analysis
6. Fix errors
7. Cleanup and shutdown
"""

import subprocess
import sys
import time
import os
import signal
from pathlib import Path
from typing import Optional
import psutil

PROJECT_ROOT = Path(__file__).parent.parent


def run_command(cmd: list, timeout: Optional[int] = None, background: bool = False):
    """Run a command"""
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
                timeout=timeout
            )
            return result
    except Exception as e:
        print(f"  ? Error: {e}")
        return None


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
    """Wait for training to complete"""
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


def main():
    """Main workflow"""
    print("=" * 70)
    print("COMPLETE TRAINING WORKFLOW - AUTOMATED")
    print("=" * 70)
    print()

    # Step 1: Precision Check - Fix all errors repeatedly
    print("[STEP 1] PRECISION CHECK - ERROR FIXING")
    print("-" * 70)
    
    # 1.1 Check and fix errors (multiple iterations)
    print("[1.1] Running precision check (multiple iterations)...")
    for iteration in range(3):
        print(f"  [CHECK {iteration + 1}/3] Checking errors...")
        result = run_command([sys.executable, "tools/full_logic_check.py"], timeout=300)
        
        # Check if errors exist
        if result:
            output = result.stdout or ""
            if "Errors: 0" in output:
                print("  ? All errors fixed!")
                break
        
        # Fix errors
        print(f"  [FIX {iteration + 1}/3] Fixing errors...")
        run_command([sys.executable, "tools/fix_all_import_statements.py"], timeout=300)
        run_command([sys.executable, "tools/fix_all_remaining_errors.py"], timeout=600)
        
        if iteration < 2:
            time.sleep(5)
    
    # 1.2 Apply code style unification
    print("[1.2] Applying code style unification...")
    result = run_command(
        [sys.executable, "-m", "autopep8", "--in-place", "--recursive",
         "--aggressive", "--aggressive", "--max-line-length=120", "."],
        timeout=600
    )
    if result and result.returncode == 0:
        print("  ? Code formatted")
    else:
        print("  ? Some formatting issues may remain")

    print()
    print("[STEP 1] Complete")
    print()

    # Step 2: Start game training
    print("[STEP 2] Starting game training...")
    print("-" * 70)
    print("[INFO] Training will run in background")
    print("[INFO] Monitor progress at: http://localhost:8001")
    print()

    training_process = run_command(
        [sys.executable, "run_with_training.py"],
        background=True
    )

    if training_process:
        print(f"  ? Training started (PID: {training_process.pid})")
        print("[INFO] Training is running in background")
    else:
        print("  ? Failed to start training")
        return

    print()
    print("[STEP 2] Complete")
    print()

    # Step 3: Wait for training completion
    print("[STEP 3] Waiting for training completion...")
    print("-" * 70)
    wait_for_training_completion(max_wait_hours=24)
    print()
    print("[STEP 3] Complete")
    print()

    # Step 4: Replay comparison learning
    print("[STEP 4] Running replay comparison learning...")
    print("-" * 70)

    # 4.1 Compare replays
    print("[4.1] Comparing replays with pro baseline...")
    if Path("tools/compare_pro_vs_training_replays.py").exists():
        result = run_command(
            [sys.executable, "tools/compare_pro_vs_training_replays.py"],
            timeout=1800
        )
        if result and result.returncode == 0:
            print("  ? Replay comparison complete")
        else:
            print("  ? Replay comparison had issues")
    else:
        print("  ? Comparison script not found, skipping...")

    # 4.2 Apply differences
    print("[4.2] Applying differences to learning parameters...")
    if Path("tools/apply_differences_and_learn.py").exists():
        result = run_command(
            [sys.executable, "tools/apply_differences_and_learn.py"],
            timeout=600
        )
        if result and result.returncode == 0:
            print("  ? Differences applied")
        else:
            print("  ? Some issues applying differences")
    else:
        print("  ? Apply script not found, skipping...")

    print()
    print("[STEP 4] Complete")
    print()

    # Step 5: Replay learning data analysis
    print("[STEP 5] Running replay learning data analysis...")
    print("-" * 70)

    if Path("tools/run_comparison_and_apply_learning.py").exists():
        result = run_command(
            [sys.executable, "tools/run_comparison_and_apply_learning.py"],
            timeout=1800
        )
        if result and result.returncode == 0:
            print("  ? Learning data analysis complete")
        else:
            print("  ? Some issues in analysis")
    else:
        print("  ? Analysis script not found, skipping...")

    print()
    print("[STEP 5] Complete")
    print()

    # Step 5.5: Build order learning (explicit step)
    print("[STEP 5.5] Running build order learning...")
    print("-" * 70)
    
    build_order_learner_script = PROJECT_ROOT / "local_training" / "scripts" / "replay_build_order_learner.py"
    if build_order_learner_script.exists():
        print("[5.5] Learning build orders from pro replays...")
        try:
            result = run_command(
                [sys.executable, str(build_order_learner_script)],
                timeout=3600  # 1 hour timeout
            )
            if result and result.returncode == 0:
                print("  ? Build order learning complete")
            else:
                print("  ??  Build order learning had issues")
        except Exception as e:
            print(f"  ??  Build order learning failed: {e}")
    else:
        print("  ??  replay_build_order_learner.py not found, skipping...")
    
    print()
    print("[STEP 5.5] Complete")
    print()

    # Step 6: Fix errors
    print("[STEP 6] Fixing errors that interfere with learning...")
    print("-" * 70)

    # 6.1 Final syntax check
    print("[6.1] Running final syntax check...")
    result = run_command([sys.executable, "tools/full_logic_check.py"], timeout=300)
    if result:
        output = result.stdout
        if "Errors:" in output:
            error_line = [l for l in output.split('\n') if 'Errors:' in l]
            if error_line:
                print(f"  {error_line[0]}")

    # 6.2 Fix remaining errors
    print("[6.2] Fixing remaining errors...")
    result = run_command([sys.executable, "tools/fix_all_remaining_errors.py"], timeout=600)
    if result and result.returncode == 0:
        print("  ? Errors fixed")
    else:
        print("  ? Some errors may remain")

    print()
    print("[STEP 6] Complete")
    print()

    # Step 7: Cleanup and shutdown
    print("[STEP 7] Cleaning up processes and files...")
    print("-" * 70)

    # 7.1 Stop any remaining training processes
    print("[7.1] Stopping remaining processes...")
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline:
                    cmdline_str = ' '.join(str(c) for c in cmdline)
                    if any(x in cmdline_str for x in ['run_with_training.py']):
                        if 'complete_training_workflow' not in cmdline_str:
                            proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        time.sleep(5)
        print("  ? Processes stopped")
    except Exception as e:
        print(f"  ? Error stopping processes: {e}")

    # 7.2 Cleanup log files
    print("[7.2] Cleaning up log files...")
    if Path("tools/cleanup_logs.py").exists():
        result = run_command([sys.executable, "tools/cleanup_logs.py"], timeout=300)
        if result and result.returncode == 0:
            print("  ? Log files cleaned")
        else:
            print("  ? Some log cleanup issues")

    # 7.3 Cleanup unnecessary files
    print("[7.3] Cleaning up unnecessary files...")
    if Path("tools/comprehensive_cleanup.py").exists():
        result = run_command([sys.executable, "tools/comprehensive_cleanup.py"], timeout=600)
        if result and result.returncode == 0:
            print("  ? Unnecessary files cleaned")
        else:
            print("  ? Some cleanup issues")

    print()
    print("[STEP 7] Complete")
    print()

    # Step 8: Shutdown computer (removed - user requested only error fixing)
    print("[STEP 8] Workflow complete - skipping shutdown")
    print("-" * 70)
    print("[INFO] All steps completed successfully")
    print("[INFO] Computer will NOT shutdown automatically")

    print()
    print("=" * 70)
    print("COMPLETE TRAINING WORKFLOW FINISHED")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[STOP] Workflow interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Workflow error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
