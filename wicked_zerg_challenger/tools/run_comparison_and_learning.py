#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run Comparison Analysis and Learning

서로 다른 데이터(프로 리플레이 vs 훈련 리플레이)를 비교 분석하고
차이점을 찾아 학습을 실행하는 통합 스크립트입니다.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Add parent directory to path
script_dir = Path(__file__).parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

try:
    from tools.compare_pro_vs_training_replays import ProVsTrainingComparator
    from local_training.scripts.replay_build_order_learner import (
        ReplayBuildOrderExtractor,
        update_config_with_learned_params
    )
except ImportError as e:
    print(f"[ERROR] Failed to import required modules: {e}")
    print("[INFO] Attempting to load modules individually...")
    sys.exit(1)


def extract_differences_from_comparison(
        comparison_history_path: Path) -> Dict[str, Any]:
    """Extract differences from comparison history"""
    differences = {
        "missing_executions": [],
        "timing_differences": [],
        "recommendations": []
    }

    if not comparison_history_path.exists():
        return differences

    try:
        with open(comparison_history_path, 'r', encoding='utf-8') as f:
            history_data = json.load(f)

        comparisons = history_data.get("comparisons", [])

        for comp in comparisons:
            training_build = comp.get("training_build", {})
            pro_baseline = comp.get("pro_baseline", {})
            recommendations = comp.get("recommendations", [])

            # Extract missing executions
            for param_name, training_value in training_build.items():
                pro_value = pro_baseline.get(param_name)
                if training_value is None and pro_value is not None:
                    differences["missing_executions"].append({
                        "parameter": param_name,
                        "pro_value": pro_value,
                        "recommendation": f"Execute {param_name} at supply {pro_value}"
                    })

            # Extract recommendations
            differences["recommendations"].extend(recommendations)

    except Exception as e:
        print(f"[WARNING] Failed to extract differences: {e}")

    return differences


def apply_differences_to_learning(
    differences: Dict[str, Any],
    learned_build_orders_path: Path
) -> Dict[str, float]:
    """Apply differences to learned parameters"""
    # Load current learned parameters
    current_params = {}
    if learned_build_orders_path.exists():
        try:
            with open(learned_build_orders_path, 'r', encoding='utf-8') as f:
                current_params = json.load(f)
        except Exception as e:
            print(f"[WARNING] Failed to load current parameters: {e}")

    updated_params = current_params.copy()
    improvements = []

    # Apply missing executions (use pro values directly)
    for missing in differences.get("missing_executions", []):
        param_name = missing["parameter"]
        pro_value = missing["pro_value"]

        current_value = current_params.get(param_name)
        if current_value != pro_value:
            updated_params[param_name] = float(pro_value)
            improvements.append({
                "parameter": param_name,
                "old_value": current_value,
                "new_value": pro_value,
                "reason": "Missing execution - using pro baseline"
            })
            print(
                f"[LEARNING] {param_name}: {current_value} → {pro_value} (pro baseline)")

    return updated_params, improvements


def main():
    """Main function"""
    print("\n" + "=" * 70)
    print("DATA COMPARISON ANALYSIS AND LEARNING")
    print("=" * 70)
    print()

    project_root = Path(__file__).parent.parent
    comparison_history_path = project_root / "local_training" / \
        "scripts" / "build_order_comparison_history.json"
    learned_build_orders_path = project_root / \
        "local_training" / "scripts" / "learned_build_orders.json"

    # Step 1: Load and compare data
    print("[STEP 1] Loading comparison data...")
    differences = extract_differences_from_comparison(comparison_history_path)

    if not differences["missing_executions"] and not differences["recommendations"]:
        print("[WARNING] No differences found in comparison data.")
        print("[INFO] Running comparison analysis first...")

        # Run comparison analysis
        try:
            comparator = ProVsTrainingComparator()
            pro_data = comparator.load_pro_replay_data()
            training_data = comparator.load_training_data()

            if not pro_data.get(
                    "baseline") and not pro_data.get("build_orders"):
                print("[WARNING] No pro replay data found.")
                return

            if not training_data.get(
                    "comparisons") and not training_data.get("build_orders"):
                print("[WARNING] No training data found.")
                return

            # Compare timings
            timing_comparisons = comparator.compare_timings(
                pro_data, training_data)

            # Re-extract differences
            differences = extract_differences_from_comparison(
                comparison_history_path)
        except Exception as e:
            print(f"[ERROR] Failed to run comparison: {e}")
            return

    # Step 2: Display differences
    print("\n[STEP 2] Found differences:")
    print("-" * 70)

    if differences["missing_executions"]:
        print(
            f"\nMissing Executions ({len(differences['missing_executions'])}):")
        for missing in differences["missing_executions"]:
            print(
                f"  - {missing['parameter']}: Pro={missing['pro_value']}, Training=null")

    if differences["recommendations"]:
        print(f"\nRecommendations ({len(differences['recommendations'])}):")
        for rec in differences["recommendations"][:5]:  # Show first 5
            print(f"  - {rec}")

    # Step 3: Apply differences to learning
    print("\n[STEP 3] Applying differences to learned parameters...")
    updated_params, improvements = apply_differences_to_learning(
        differences, learned_build_orders_path
    )

    if improvements:
        # Save updated parameters
        learned_build_orders_path.parent.mkdir(parents=True, exist_ok=True)
        with open(learned_build_orders_path, 'w', encoding='utf-8') as f:
            json.dump(updated_params, f, indent=2, ensure_ascii=False)
        print(
            f"\n[SAVED] Updated {len(improvements)} parameters to {learned_build_orders_path}")

        # Update config
        print("\n[STEP 4] Updating config with learned parameters...")
        try:
            update_config_with_learned_params(updated_params)
            print("[SUCCESS] Config updated")
        except Exception as e:
            print(f"[WARNING] Failed to update config: {e}")

        # Step 5: Start replay learning
        print("\n[STEP 5] Starting replay learning with updated parameters...")
        try:
            pro_replay_dir = Path("D:/replays/replays")
            if not pro_replay_dir.exists():
                pro_replay_dir = Path("replays_archive")

            extractor = ReplayBuildOrderExtractor(
                replay_dir=str(pro_replay_dir))
            max_replays = 50  # Process 50 replays

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
    else:
        print("[INFO] No improvements needed - all parameters are up to date")

    print("\n" + "=" * 70)
    print("COMPARISON AND LEARNING COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
