# -*- coding: utf-8 -*-
"""
???ΰ??̸? ???/??? ?н? ?? ???? ?Ʒ? ???? ??ũ?/ο?

1. ???ΰ??̸? ???/??̿??? ??????? ?н?
2. ?н??? ????????? config.py?? ????
3. ???? ?Ʒ? ???? (?н??? ??????? ????)
4. ???? ???/??̿? ???ΰ??̸? ???/??? ?? ?м?
5. ???? ???? ???? ?? ?ݺ?
"""

import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("ProReplayLearningWorkflow")


def run_command(
    cmd: List[str], cwd: Path, description: str, timeout: int = 3600
) -> Tuple[bool, str]:
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
            encoding="utf-8",
            errors="ignore",
            timeout=timeout,
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


def check_learned_parameters(project_root: Path) -> Dict[str, Any]:
    """?н??? ?Ķ???? Ȯ??"""
    learned_file = (
        project_root / "local_training" / "scripts" / "learned_build_orders.json"
    )

    if not learned_file.exists():
        return {}

    try:
        with open(learned_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Failed to load learned parameters: {e}")
        return {}


def print_learned_parameters(learned_params: Dict[str, Any]):
    """?н??? ?Ķ???? ???"""
    if not learned_params:
        logger.info("No learned parameters found")
        return

    logger.info(f"\n{'='*70}")
    logger.info("?н??? ??????? ?Ķ????")
    logger.info(f"{'='*70}")

    if isinstance(learned_params, dict):
        for key, value in learned_params.items():
            if isinstance(value, (int, float)):
                logger.info(f"  {key}: {value}")
            elif isinstance(value, dict):
                logger.info(f"  {key}:")
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, (int, float)):
                        logger.info(f"    {sub_key}: {sub_value}")

    logger.info(f"{'='*70}\n")


def main():
    project_root = Path(__file__).parent.parent

    logger.info("=" * 70)
    logger.info("???ΰ??̸? ???/??? ?н? ?? ???? ?Ʒ? ???? ??ũ?/ο?")
    logger.info("=" * 70)
    logger.info("\n?? ??ũ?/ο?? ???? ?ܰ踦 ?????մϴ?:")
    logger.info("  1. ???ΰ??̸? ???/??̿??? ??????? ?н?")
    logger.info("  2. ?н??? ????????? config.py?? ????")
    logger.info("  3. ???? ?Ʒ? ???? (?н??? ??????? ????)")
    logger.info("  4. ???? ???/??̿? ???ΰ??̸? ???/??? ?? ?м?")
    logger.info("  5. ???? ???? ???? ?? ?ݺ?")
    logger.info("=" * 70)

    # Script paths
    replay_learner = (
        project_root / "local_training" / "scripts" / "replay_build_order_learner.py"
    )
    run_training = project_root / "run_with_training.py"
    strategy_audit = project_root / "local_training" / "strategy_audit.py"

    # Check if scripts exist
    scripts = {
        "Replay Learner": replay_learner,
        "Run Training": run_training,
        "Strategy Audit": strategy_audit,
    }

    for name, script in scripts.items():
        if not script.exists():
            logger.error(f"{name} script not found: {script}")
            sys.exit(1)

    iteration = 0
    max_iterations = 5  # ?ִ? 5ȸ ?ݺ?

    while iteration < max_iterations:
        iteration += 1
        logger.info(f"\n\n{'#'*70}")
        logger.info(f"# ITERATION {iteration} / {max_iterations}")
        logger.info(f"{'#'*70}\n")

        # STEP 1: ???ΰ??̸? ???/??̿??? ??????? ?н?
        logger.info(f"\n{'='*70}")
        logger.info(f"???ΰ??̸? ???/??̿??? ??????? ?н? (Iteration {iteration})")
        logger.info(f"{'='*70}\n")

        success_learn, output_learn = run_command(
            [sys.executable, str(replay_learner)],
            project_root,
            f"Iteration {iteration} - Pro Gamer Replay Learning",
            timeout=1800,  # 30 minutes
        )

        if not success_learn:
            logger.error(f"Replay learning failed in iteration {iteration}")
            logger.info("Continuing with existing learned parameters...")
        else:
            logger.info(f"Replay learning completed for iteration {iteration}")

        # ?н??? ?Ķ???? Ȯ??
        learned_params = check_learned_parameters(project_root)
        if learned_params:
            print_learned_parameters(learned_params)
            logger.info(
                "Learned parameters have been automatically applied to config.py"
            )
        else:
            logger.warning("No learned parameters found. Using default parameters.")

        # STEP 2: ???? ?Ʒ? ???? (?н??? ??????? ????)
        logger.info(f"\n{'='*70}")
        logger.info(f"???? ?Ʒ? ???? (?н??? ??????? ????) (Iteration {iteration})")
        logger.info(f"{'='*70}\n")

        logger.info("???? ?Ʒ??? ?????մϴ?...")
        logger.info("?н??? ????????? ?ڵ????? ?????ϴ?.")
        logger.info("Ctrl+C?? ???? ?ߴ??? ?? ?ֽ??ϴ?.")
        success_training, output_training = run_command(
            [sys.executable, str(run_training)],
            project_root,
            f"Iteration {iteration} - Game Training with Learned Build Orders",
            timeout=3600,  # 60 minutes
        )

        if success_training:
            logger.info(f"Game training completed for iteration {iteration}")
        else:
            logger.warning(f"Game training had issues in iteration {iteration}")
            logger.info("Continuing with comparison analysis...")

        # STEP 3: ???? ???/??̿? ???ΰ??̸? ???/??? ?? ?м?
        logger.info(f"\n{'='*70}")
        logger.info(f"???? ???/??̿? ???ΰ??̸? ???/??? ?? ?м? (Iteration {iteration})")
        logger.info(f"{'='*70}\n")

        success_audit, output_audit = run_command(
            [sys.executable, str(strategy_audit)],
            project_root,
            f"Iteration {iteration} - Bot vs Pro Gamer Comparison Analysis",
            timeout=1800,  # 30 minutes
        )

        if success_audit:
            logger.info(f"Comparison analysis completed for iteration {iteration}")

            # ?м? ??? ??? ???
            if (
                "critical_issues" in output_audit.lower()
                or "recommendations" in output_audit.lower()
            ):
                logger.info("\n[INFO] Analysis results:")
                logger.info(
                    "  - Check local_training/comparison_reports/ for detailed reports"
                )
        else:
            logger.warning(f"Comparison analysis had issues in iteration {iteration}")

        # STEP 4: ???? ???? Ȯ?? ?? ???
        logger.info(f"\n{'='*70}")
        logger.info(f"???? ???? Ȯ?? ?? ??? (Iteration {iteration})")
        logger.info(f"{'='*70}\n")

        # ?н??? ?Ķ???? ??Ȯ??
        learned_params_after = check_learned_parameters(project_root)
        if learned_params_after:
            logger.info("Updated learned parameters:")
            print_learned_parameters(learned_params_after)

        # ?? ????Ʈ Ȯ??
        comparison_dir = project_root / "local_training" / "comparison_reports"
        if comparison_dir.exists():
            report_files = list(comparison_dir.glob("*.md"))
            if report_files:
                latest_report = max(report_files, key=lambda p: p.stat().st_mtime)
                logger.info(f"Latest comparison report: {latest_report}")

        logger.info(f"\n{'='*70}")
        logger.info(f"? ITERATION {iteration} / {max_iterations} COMPLETED")
        logger.info(f"{'='*70}")
        logger.info(f"   Replay Learning: {'?' if success_learn else '?'}")
        logger.info(f"   Game Training: {'?' if success_training else '?'}")
        logger.info(f"   Comparison Analysis: {'?' if success_audit else '?'}")
        logger.info(f"{'='*70}")

        if iteration < max_iterations:
            logger.info("\n[INFO] Waiting 10 seconds before next iteration...")
            time.sleep(10)

    # ???? ???
    logger.info(f"\n\n{'#'*70}")
    logger.info("# ??ü ??ũ?/ο? ?Ϸ?")
    logger.info(f"{'#'*70}\n")

    # ???? ?н??? ?Ķ???? Ȯ??
    final_learned_params = check_learned_parameters(project_root)
    if final_learned_params:
        logger.info("???? ?н??? ??????? ?Ķ????:")
        print_learned_parameters(final_learned_params)

    logger.info("\n??? Ȯ??:")
    logger.info("  - ?н??? ???????: local_training/scripts/learned_build_orders.json")
    logger.info("  - ?? ????Ʈ: local_training/comparison_reports/")
    logger.info("  - ???? ???: local_training/scripts/training_session_stats.json")
    logger.info("\n?߰? ????:")
    logger.info("  python tools\\show_learning_rate.py")
    logger.info("  python tools\\monitor_training_progress.py")
    logger.info(f"\n{'#'*70}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[DRONE]  Workflow interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n? Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
