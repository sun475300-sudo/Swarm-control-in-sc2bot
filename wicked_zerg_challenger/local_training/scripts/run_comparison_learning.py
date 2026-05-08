import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("RunComparisonLearning")

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


def run_comparison():
    logger.info("=" * 60)
    logger.info("COMPARISON LEARNING: BOT vs PRO REPLAYS")
    logger.info("=" * 60)

    # Paths
    base_dir = Path("local_training/scripts")
    learned_builds_path = base_dir / "learned_build_orders.json"
    history_path = base_dir / "build_order_comparison_history.json"

    if not learned_builds_path.exists():
        logger.error(f"Learned data not found: {learned_builds_path}")
        logger.info("Please run replay_build_order_learner.py first.")
        return

    with open(learned_builds_path, encoding="utf-8") as f:
        pro_data = json.load(f)

    pro_timings = pro_data.get("build_order_timings", {})
    if not pro_timings:
        logger.warning("No pro timings found in learned data.")
        return

    # Define Bot's "Standard" targets (Mock data or loaded from config)
    # Ideally, we should read what the bot ACTUALLY did in recent games,
    # but for now we look at the 'default' strategy plan.
    bot_plan = {
        "Hatchery": 50,  # 12 Hatch? No, standard is ~0:50 for 16 hatch?
        # SC2 seconds.
        "SpawningPool": 65,  # 18 Pool
        "Extractor": 60,  # 17 Gas
        "Queen": 100,
        "Zergling": 110,
        "RoachWarren": 180,
    }

    logger.info(
        f"Analyzed {pro_data['stats']['total_replays']} pro replays for baseline."
    )

    comparisons = []

    logger.info("\n[COMPARISON REPORT]")
    logger.info(
        f"{'Unit/Structure':<20} | {'Pro Avg (s)':<12} | {'Bot Target (s)':<12} | {'Diff':<10} | {'Status'}"
    )
    logger.info("-" * 75)

    score_sum = 0
    count = 0

    for unit, pro_time in pro_timings.items():
        if unit in bot_plan:
            bot_time = bot_plan[unit]
            diff = bot_time - pro_time

            # Simple heuristic status
            if abs(diff) < 10:
                status = "EXCELLENT"
                score = 1.0
            elif abs(diff) < 20:
                status = "GOOD"
                score = 0.8
            elif abs(diff) < 40:
                status = "FAIR"
                score = 0.5
            else:
                status = "POOR"
                score = 0.2

            logger.info(
                f"{unit:<20} | {pro_time:<12.1f} | {bot_time:<12.1f} | {diff:<+10.1f} | {status}"
            )

            comparisons.append(
                {
                    "unit": unit,
                    "pro_time": pro_time,
                    "bot_time": bot_time,
                    "diff": diff,
                    "status": status,
                }
            )
            score_sum += score
            count += 1

    avg_score = (score_sum / count) if count > 0 else 0
    logger.info("-" * 75)
    logger.info(f"OVERALL SIMILARITY SCORE: {avg_score:.1%}")

    # Save History
    history_entry = {
        "timestamp": datetime.now().isoformat(),
        "score": avg_score,
        "details": comparisons,
    }

    # Create or update history file
    history = {"entries": []}
    if history_path.exists():
        try:
            with open(history_path) as f:
                loaded = json.load(f)
                if isinstance(loaded, dict) and "entries" in loaded:
                    history = loaded
                elif isinstance(loaded, list):  # Legacy format support if any
                    history["entries"] = loaded
        except (OSError, json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"History load failed, using defaults: {e}")

    history["entries"].append(history_entry)

    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)

    logger.info(f"\n[INFO] Comparison saved to {history_path}")


if __name__ == "__main__":
    run_comparison()
