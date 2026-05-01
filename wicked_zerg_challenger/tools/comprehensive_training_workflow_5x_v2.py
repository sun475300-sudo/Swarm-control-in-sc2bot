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

import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger("ComprehensiveTrainingWorkflow5xV2")

def run_command(cmd: List[str], cwd: Path, description: str, timeout: int = 3600) -> Tuple[bool, str]:
    """Run a command and return success status and output"""
    logger.info(f"\n{'='*70}")
    logger.info(f"{description}")
    logger.info(f"{'='*70}")
    logger.info(f"Command: {' '.join(cmd)}")
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
            logger.info(result.stdout)
        if result.stderr:
            logger.info(result.stderr, file=sys.stderr)
        
        success = result.returncode == 0
        return success, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        logger.warning(f"Command timed out after {timeout} seconds")
        return False, "Timeout"
    except Exception as e:
        logger.error(f"Failed to run command: {e}")
        return False, str(e)

def main():
    project_root = Path(__file__).parent.parent
    
    logger.info("=" * 70)
    logger.info("COMPREHENSIVE TRAINING WORKFLOW - 5 ITERATIONS (VERSION 2)")
    logger.info("=" * 70)
    logger.info("\nThis workflow will execute:")
    logger.error("  1. Auto error fixing (tools/auto_error_fixer.py)")
    logger.info("  2. Code quality check (tools/code_quality_improver.py)")
    logger.info("  3. Game training (run_with_training.py)")
    logger.info("  4. Replay build order learning (replay_build_order_learner.py)")
    logger.info("  5. Replay comparison analysis (strategy_audit.py)")
    logger.info("  6. Repeat 5 times")
    logger.info("=" * 70)
    
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
            logger.error(f"{name} script not found: {script}")
            sys.exit(1)
    
    successful_iterations = 0
    
    for iteration in range(1, 6):
        logger.info(f"\n\n{'#'*70}")
        logger.info(f"# ITERATION {iteration} / 5")
        logger.info(f"{'#'*70}\n")
        
        iteration_success = True
        
        # Step 1: Auto error fixing
        logger.error("\n[STEP 1] Running auto error fixing...")
        success1, _ = run_command(
            [sys.executable, str(auto_error_fixer)],
            project_root,
            f"Iteration {iteration} - Auto Error Fixing",
            timeout=600  # 10 minutes
        )
        
        if success1:
            logger.error(f"Auto error fixing completed for iteration {iteration}")
        else:
            logger.error(f"Auto error fixing had issues in iteration {iteration}, continuing...")
            iteration_success = False
        
        # Step 2: Code quality check
        logger.info("\n[STEP 2] Running code quality check...")
        success2, _ = run_command(
            [sys.executable, str(code_quality_improver)],
            project_root,
            f"Iteration {iteration} - Code Quality Check",
            timeout=600  # 10 minutes
        )
        
        if success2:
            logger.info(f"Code quality check completed for iteration {iteration}")
        else:
            logger.warning(f"Code quality check had issues in iteration {iteration}, continuing...")
            iteration_success = False
        
        # Step 3: Game training
        logger.info("\n[STEP 3] Running game training...")
        success3, _ = run_command(
            [sys.executable, str(run_training)],
            project_root,
            f"Iteration {iteration} - Game Training",
            timeout=3600  # 60 minutes
        )
        
        if success3:
            logger.info(f"Game training completed for iteration {iteration}")
        else:
            logger.warning(f"Game training had issues in iteration {iteration}, continuing...")
            iteration_success = False
        
        # Step 4: Replay build order learning
        logger.info("\n[STEP 4] Running replay build order learning...")
        success4, _ = run_command(
            [sys.executable, str(replay_learner)],
            project_root,
            f"Iteration {iteration} - Replay Build Order Learning",
            timeout=1800  # 30 minutes
        )
        
        if success4:
            logger.info(f"Replay build order learning completed for iteration {iteration}")
            logger.info("Learned parameters will be automatically applied via config.py")
        else:
            logger.warning(f"Replay build order learning had issues in iteration {iteration}, continuing...")
            iteration_success = False
        
        # Step 5: Replay comparison analysis
        logger.info("\n[STEP 5] Running replay comparison analysis...")
        success5, _ = run_command(
            [sys.executable, str(strategy_audit)],
            project_root,
            f"Iteration {iteration} - Replay Comparison Analysis",
            timeout=1800  # 30 minutes
        )
        
        if success5:
            logger.info(f"Replay comparison analysis completed for iteration {iteration}")
        else:
            logger.warning(f"Replay comparison analysis had issues in iteration {iteration}, continuing...")
            iteration_success = False
        
        if iteration_success:
            successful_iterations += 1
        
        logger.info(f"\n{'='*70}")
        logger.info(f"? ITERATION {iteration} / 5 COMPLETED")
        logger.error(f"   Auto Error Fixing: {'?' if success1 else '?'}")
        logger.info(f"   Code Quality Check: {'?' if success2 else '?'}")
        logger.info(f"   Game Training: {'?' if success3 else '?'}")
        logger.info(f"   Replay Build Order Learning: {'?' if success4 else '?'}")
        logger.info(f"   Replay Comparison Analysis: {'?' if success5 else '?'}")
        logger.info(f"{'='*70}")
        
        if iteration < 5:
            logger.info("\nWaiting 10 seconds before next iteration...")
            time.sleep(10)
    
    logger.info(f"\n\n{'#'*70}")
    logger.info("# ALL 5 ITERATIONS COMPLETED")
    logger.info(f"{'#'*70}")
    logger.info("\nSummary:")
    logger.info(f"  - Successful iterations: {successful_iterations} / 5")
    logger.info("  - Learned build orders: local_training/scripts/learned_build_orders.json")
    logger.info("  - Comparison reports: local_training/comparison_reports/")
    logger.info("\nCheck results:")
    logger.info("  python tools\\show_learning_rate.py")
    logger.info("  python tools\\monitor_training_progress.py")
    logger.info(f"\n{'#'*70}")

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
