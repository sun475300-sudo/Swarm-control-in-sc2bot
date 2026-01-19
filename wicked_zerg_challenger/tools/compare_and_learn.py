# -*- coding: utf-8 -*-
"""
Compare Pro vs Training Replays and Apply Learning

���÷��� �н� �����Ϳ� �Ʒ� ���÷��� �н� �����͸� �� �м��ϰ�,
�������� ã�� �н��� �����ϴ� ���� ��ũ��Ʈ�Դϴ�.
"""

import json
import sys
from pathlib import Path
from typing import Dict
import Any
import Optional
from datetime import datetime

# Add parent directory to path
script_dir = Path(__file__).parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

try:
    from tools.compare_pro_vs_training_replays import ProVsTrainingComparator
    from local_training.scripts.replay_build_order_learner import ReplayBuildOrderExtractor
    import update_config_with_learned_params
except ImportError as e:
    print(f"[ERROR] Failed to import required modules: {e}")
    sys.exit(1)


def apply_learned_differences(
    timing_comparisons: Dict[str, Dict[str, Any]],
    learned_build_orders_path: Path,
    learning_rate: float = 0.3
) -> Dict[str, float]:
    """
    Apply learned differences from comparison to build order parameters

    Args:
        timing_comparisons: Comparison results from ProVsTrainingComparator
        learned_build_orders_path: Path to learned_build_orders.json
        learning_rate: How aggressively to apply changes (0.0 - 1.0)

    Returns:
        Updated learned parameters
    """
    # Load current learned parameters
    current_params = {}
    if learned_build_orders_path.exists():
        try:
            with open(learned_build_orders_path, 'r', encoding='utf-8') as f:
                current_params = json.load(f)
        except Exception as e:
            print(f"[WARNING] Failed to load current parameters: {e}")

    updated_params = current_params.copy()
    improvements_applied = []

    # Apply improvements based on comparison
    for param_name, comp in timing_comparisons.items():
        if comp.get("mean_difference") is None:
            continue

        diff = comp["mean_difference"]
        pro_mean = comp.get("pro_mean")
        training_mean = comp.get("training_mean")

        if pro_mean is None or training_mean is None:
            continue

        # If training is significantly later than pro (diff > 5), adjust
        # towards pro
        if diff > 5:
            current_value = current_params.get(param_name, training_mean)
            # Move towards pro mean
            adjustment = (pro_mean - current_value) * learning_rate
            new_value = current_value + adjustment
            updated_params[param_name] = max(
                6.0, new_value)  # Minimum supply 6
            improvements_applied.append({
                "parameter": param_name,
                "old_value": current_value,
                "new_value": updated_params[param_name],
                "pro_target": pro_mean,
                "adjustment": adjustment
            })
            print(
                f"[LEARNING] {param_name}: {current_value:.1f} �� {updated_params[param_name]:.1f} (target: {pro_mean:.1f}, diff: {diff:.1f})")

    return updated_params, improvements_applied


def main():
    """Main function"""
    print("\n" + "=" * 70)
    print("REPLAY LEARNING DATA COMPARISON AND LEARNING")
    print("=" * 70)
    print()

    # Step 1: Run comparison analysis
    print("[STEP 1] Running comparison analysis...")
    comparator = ProVsTrainingComparator()

    pro_data = comparator.load_pro_replay_data()
    training_data = comparator.load_training_data()

    if not pro_data.get("baseline") and not pro_data.get("build_orders"):
        print(
            "[WARNING] No pro replay data found. Please ensure pro replays are available.")
        return

    if not training_data.get(
            "comparisons") and not training_data.get("build_orders"):
        print("[WARNING] No training data found. Please run training first.")
        return

    # Compare timings
    print("\n[STEP 2] Comparing build order timings...")
    timing_comparisons = comparator.compare_timings(pro_data, training_data)

    # Analyze performance
    print("\n[STEP 3] Analyzing performance...")
    performance_analysis = comparator.analyze_performance(
        pro_data, training_data)

    # Generate and print report
    print("\n[STEP 4] Generating comparison report...")
    report = comparator.generate_comparison_report(
        pro_data, training_data, timing_comparisons, performance_analysis
    )
    print("\n" + report)

    # Save comparison data
    print("\n[STEP 5] Saving comparison data...")
    comparator.save_comparison_data(
        pro_data,
        training_data,
        timing_comparisons,
        performance_analysis,
        report)

    # Step 6: Apply learned differences
    print("\n[STEP 6] Applying learned differences to build order parameters...")
    learned_build_orders_path = comparator.learned_build_orders_path
    updated_params, improvements_applied = apply_learned_differences(
        timing_comparisons, learned_build_orders_path, learning_rate=0.3
    )

    if improvements_applied:
        # Save updated parameters
        learned_build_orders_path.parent.mkdir(parents=True, exist_ok=True)
        with open(learned_build_orders_path, 'w', encoding='utf-8') as f:
            json.dump(updated_params, f, indent=2, ensure_ascii=False)
        print(
            f"\n[SAVED] Updated {len(improvements_applied)} parameters to {learned_build_orders_path}")

        # Update config
        print("\n[STEP 7] Updating config with learned parameters...")
        try:
            update_config_with_learned_params(updated_params)
            print("[SUCCESS] Config updated with learned parameters")
        except Exception as e:
            print(f"[WARNING] Failed to update config: {e}")

        # Step 8: Start replay learning with updated parameters
        print("\n[STEP 8] Starting replay learning with updated parameters...")
        try:
            extractor = ReplayBuildOrderExtractor(
                replay_dir=str(comparator.pro_replay_dir))
            max_replays = 100  # Process 100 replays
            learned_params = extractor.learn_from_replays(
                max_replays=max_replays)

            if learned_params:
                extractor.save_learned_parameters(learned_params)
                update_config_with_learned_params(learned_params)
                print(
                    f"[SUCCESS] Learned {len(learned_params)} parameters from {max_replays} replays")
            else:
                print("[WARNING] No parameters learned from replays")
        except Exception as e:
            print(f"[WARNING] Failed to run replay learning: {e}")
    else:
        print("[INFO] No improvements needed - all timings are within acceptable range")

    print("\n" + "=" * 70)
    print("COMPARISON AND LEARNING COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
