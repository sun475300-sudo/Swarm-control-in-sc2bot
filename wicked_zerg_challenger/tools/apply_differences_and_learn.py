#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apply Differences and Learn

Apply differences from comparison analysis to learning parameters and execute learning.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
script_dir = Path(__file__).parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

PROJECT_ROOT = script_dir


def main():
    """Main function"""
    print("\n" + "=" * 70)
    print("APPLY DIFFERENCES AND LEARNING")
    print("=" * 70)
    print()

    # Load comparison data
    comparison_path = PROJECT_ROOT / "local_training" / \
        "scripts" / "build_order_comparison_history.json"
    learned_path = PROJECT_ROOT / "local_training" / \
        "scripts" / "learned_build_orders.json"

    print("[STEP 1] Loading comparison data...")
    if not comparison_path.exists():
        print(f"[ERROR] Comparison data not found: {comparison_path}")
        return

    with open(comparison_path, 'r', encoding='utf-8') as f:
        comparison_data = json.load(f)

    # Load current learned parameters
    print("[STEP 2] Loading current learned parameters...")
    current_params = {}
    if learned_path.exists():
        with open(learned_path, 'r', encoding='utf-8') as f:
            current_params = json.load(f)

    print(f"[INFO] Current parameters: {len(current_params)} parameters")
    for key, value in current_params.items():
        print(f"  - {key}: {value}")

    # Extract differences
    print("\n[STEP 3] Analyzing differences...")
    comparisons = comparison_data.get("comparisons", [])

    differences = []
    for comp in comparisons:
        training_build = comp.get("training_build", {})
        pro_baseline = comp.get("pro_baseline", {})

        for param_name, training_value in training_build.items():
            pro_value = pro_baseline.get(param_name)

            if training_value is None and pro_value is not None:
                differences.append({
                    "parameter": param_name,
                    "training_value": training_value,
                    "pro_value": pro_value,
                    "action": "ADD"
                })
                print(
                    f"  [DIFF] {param_name}: Training=null, Pro={pro_value} -> Need to add")
            elif training_value is not None and pro_value is not None:
                diff = abs(training_value - pro_value)
                if diff > 2:  # Significant difference
                    differences.append({
                        "parameter": param_name,
                        "training_value": training_value,
                        "pro_value": pro_value,
                        "difference": diff,
                        "action": "ADJUST"
                    })
                    print(
                        f"  [DIFF] {param_name}: Training={training_value}, Pro={pro_value}, Diff={diff:.1f} -> Need to adjust")

    if not differences:
        print("[INFO] No significant differences found. All parameters are up to date.")
        return

    # Apply differences
    print(f"\n[STEP 4] Applying {len(differences)} differences...")
    updated_params = current_params.copy()

    for diff in differences:
        param_name = diff["parameter"]
        pro_value = diff["pro_value"]

        if diff["action"] == "ADD":
            updated_params[param_name] = float(pro_value)
            print(
                f"  [APPLY] {param_name}: null -> {pro_value} (added from pro baseline)")
        elif diff["action"] == "ADJUST":
            current_value = current_params.get(
                param_name, diff["training_value"])
            # Move towards pro value with learning rate 0.3
            learning_rate = 0.3
            adjustment = (pro_value - current_value) * learning_rate
            new_value = current_value + adjustment
            updated_params[param_name] = max(
                6.0, new_value)  # Minimum supply 6
            print(
                f"  [APPLY] {param_name}: {current_value:.1f} -> {updated_params[param_name]:.1f} (target: {pro_value}, adjustment: {adjustment:+.1f})")

    # Save updated parameters
    print(f"\n[STEP 5] Saving updated parameters...")
    learned_path.parent.mkdir(parents=True, exist_ok=True)
    with open(learned_path, 'w', encoding='utf-8') as f:
        json.dump(updated_params, f, indent=2, ensure_ascii=False)

    print(f"[SAVED] Updated parameters saved to {learned_path}")
    print("\nUpdated parameters:")
    for key, value in updated_params.items():
        if key in current_params and current_params[key] != value:
            print(f"  * {key}: {current_params[key]} -> {value}")
        else:
            print(f"  - {key}: {value}")

    # Update config
    print("\n[STEP 6] Updating config...")
    try:
        from local_training.scripts.replay_build_order_learner import update_config_with_learned_params
        update_config_with_learned_params(updated_params)
        print("[SUCCESS] Config updated with learned parameters")
    except Exception as e:
        print(f"[WARNING] Failed to update config: {e}")
        import traceback
        traceback.print_exc()

    # Start replay learning
    print("\n[STEP 7] Starting replay learning...")
    try:
        from local_training.scripts.replay_build_order_learner import ReplayBuildOrderExtractor

        pro_replay_dir = Path("D:/replays/replays")
        if not pro_replay_dir.exists():
            pro_replay_dir = Path("replays_archive")

        if not pro_replay_dir.exists():
            print(f"[WARNING] Replay directory not found: {pro_replay_dir}")
            print("[INFO] Skipping replay learning")
        else:
            extractor = ReplayBuildOrderExtractor(
                replay_dir=str(pro_replay_dir))
            max_replays = 50

            print(
                f"[INFO] Learning from {max_replays} replays in {pro_replay_dir}...")
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
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print("DIFFERENCES APPLIED AND LEARNING COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
