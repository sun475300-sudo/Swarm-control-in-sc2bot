#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run Comparison and Apply Learning

 м    ݿ н  ũƮԴϴ.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add parent directory to path
script_dir = Path(__file__).parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

PROJECT_ROOT = script_dir


def run_comparison_analysis() -> Dict[str, Any]:
    """Run comparison analysis between training and pro replays"""
    print("\n[STEP 1] Running comparison analysis...")
    print("-" * 70)

    try:
        # Load existing comparison data
        comparison_path = PROJECT_ROOT / "local_training" / \
            "scripts" / "build_order_comparison_history.json"

        if not comparison_path.exists():
            print("[WARNING] Comparison data not found, skipping comparison analysis")
            return {}

        with open(comparison_path, 'r', encoding='utf-8') as f:
            comparison_data = json.load(f)

        comparisons = comparison_data.get("comparisons", [])

        if not comparisons:
            print("[WARNING] No comparison data found")
            return {}

        print(f"[INFO] Found {len(comparisons)} comparison records")

        # Extract differences
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
                        f"  [DIFF] {param_name}: Training=null, Pro={pro_value}  Need to add")
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
                            f"  [DIFF] {param_name}: Training={training_value}, Pro={pro_value}, Diff={diff:.1f}  Need to adjust")

        print(f"[SUCCESS] Found {len(differences)} differences")

        return {
            "differences": differences,
            "comparisons": comparisons
        }

    except Exception as e:
        print(f"[ERROR] Comparison analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return {}


def apply_differences_to_learning(
        differences: list, learned_path: Path) -> Dict[str, float]:
    """Apply differences to learned parameters"""
    print("\n[STEP 2] Applying differences to learning...")
    print("-" * 70)

    # Load current learned parameters
    current_params = {}
    if learned_path.exists():
        try:
            with open(learned_path, 'r', encoding='utf-8') as f:
                current_params = json.load(f)
        except Exception as e:
            print(f"[WARNING] Failed to load current parameters: {e}")

    print(f"[INFO] Current parameters: {len(current_params)}")

    # Apply differences
    updated_params = current_params.copy()
    changes = []

    for diff in differences:
        param_name = diff["parameter"]
        pro_value = diff["pro_value"]

        if diff["action"] == "ADD":
            updated_params[param_name] = float(pro_value)
            changes.append({
                "parameter": param_name,
                "old": None,
                "new": pro_value
            })
            print(
                f"  [APPLY] {param_name}: null  {pro_value} (added from pro baseline)")
        elif diff["action"] == "ADJUST":
            current_value = current_params.get(
                param_name, diff["training_value"])
            # Move towards pro value with learning rate 0.3
            learning_rate = 0.3
            adjustment = (pro_value - current_value) * learning_rate
            new_value = current_value + adjustment
            updated_params[param_name] = max(
                6.0, new_value)  # Minimum supply 6
            changes.append({
                "parameter": param_name,
                "old": current_value,
                "new": new_value
            })
            print(
                f"  [APPLY] {param_name}: {current_value:.1f}  {new_value:.1f} (target: {pro_value}, adjustment: {adjustment:+.1f})")

    if changes:
        # Save updated parameters
        learned_path.parent.mkdir(parents=True, exist_ok=True)
        with open(learned_path, 'w', encoding='utf-8') as f:
            json.dump(updated_params, f, indent=2, ensure_ascii=False)

        print(f"\n[SUCCESS] Updated {len(changes)} parameters:")
        for change in changes:
            print(f"  {change['parameter']}: {change['old']}  {change['new']}")

        return updated_params
    else:
        print("[INFO] No parameter changes needed")
        return current_params


def learn_from_pro_replays(
        max_replays: int = 50) -> Optional[Dict[str, float]]:
    """Learn from pro gamer replays"""
    print("\n[STEP 3] Learning from pro gamer replays...")
    print("-" * 70)

    try:
        from local_training.scripts.replay_build_order_learner import (
            ReplayBuildOrderExtractor,
            update_config_with_learned_params
        )

        # Find pro replay directory
        pro_replay_dir = Path("D:/replays/replays")
        if not pro_replay_dir.exists():
            pro_replay_dir = Path("replays_archive")

        if not pro_replay_dir.exists():
            print(f"[WARNING] Replay directory not found: {pro_replay_dir}")
            return None

        print(
            f"[INFO] Learning from {max_replays} replays in {pro_replay_dir}...")

        extractor = ReplayBuildOrderExtractor(replay_dir=str(pro_replay_dir))
        learned_params = extractor.learn_from_replays(max_replays=max_replays)

        if not learned_params:
            print("[WARNING] No parameters learned from replays")
            return None

        # Save learned parameters
        archive_dir = Path("D:/replays/archive")
        archive_dir.mkdir(parents=True, exist_ok=True)

        saved_path = extractor.save_learned_parameters(
            learned_params,
            output_file=str(
                archive_dir /
                f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}" /
                "learned_build_orders.json"))

        print(f"[SUCCESS] Learned parameters saved to: {saved_path}")

        # Also save to local_training/scripts/learned_build_orders.json for
        # immediate use
        local_learned_path = PROJECT_ROOT / "local_training" / \
            "scripts" / "learned_build_orders.json"
        local_learned_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_learned_path, 'w', encoding='utf-8') as f:
            json.dump(learned_params, f, indent=2, ensure_ascii=False)

        print(f"[INFO] Also saved to local training: {local_learned_path}")

        # Update config
        try:
            update_config_with_learned_params(learned_params)
            print("[SUCCESS] Config updated with learned parameters")
        except Exception as e:
            print(f"[WARNING] Failed to update config: {e}")

        print(
            f"[SUCCESS] Learned {len(learned_params)} parameters from {max_replays} replays")

        return learned_params

    except Exception as e:
        print(f"[ERROR] Replay learning failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main function"""
    print("\n" + "=" * 70)
    print("COMPARISON ANALYSIS AND LEARNING")
    print("=" * 70)
    print()
    print("This workflow will:")
    print("  1. Run comparison analysis (training vs pro replays)")
    print("  2. Apply differences to learned parameters")
    print("  3. Learn from pro gamer replays")
    print("  4. Save learned parameters")
    print()

    learned_path = PROJECT_ROOT / "local_training" / \
        "scripts" / "learned_build_orders.json"

    # Step 1: Comparison analysis
    comparison_result = run_comparison_analysis()

    # Step 2: Apply differences
    if comparison_result.get("differences"):
        updated_params = apply_differences_to_learning(
            comparison_result["differences"],
            learned_path
        )
    else:
        print("\n[INFO] No differences found, loading current parameters...")
        if learned_path.exists():
            with open(learned_path, 'r', encoding='utf-8') as f:
                updated_params = json.load(f)
        else:
            updated_params = {}

    # Step 3: Learn from pro replays
    learned_params = learn_from_pro_replays(max_replays=50)

    # Step 4: Merge learned parameters
    if learned_params:
        # Merge learned params with updated params
        final_params = updated_params.copy()
        for param_name, learned_value in learned_params.items():
            if param_name not in final_params or abs(
                    final_params.get(param_name, 0) - learned_value) > 2:
                final_params[param_name] = float(learned_value)

        # Save final parameters
        learned_path.parent.mkdir(parents=True, exist_ok=True)
        with open(learned_path, 'w', encoding='utf-8') as f:
            json.dump(final_params, f, indent=2, ensure_ascii=False)

        print(f"\n[SUCCESS] Final parameters ({len(final_params)}):")
        for key, value in sorted(final_params.items()):
            print(f"  {key}: {value}")

    # Summary
    print("\n" + "=" * 70)
    print("COMPARISON AND LEARNING COMPLETE")
    print("=" * 70)
    print(f"\nSummary:")
    print(
        f"  - Comparison analysis: {'Success' if comparison_result else 'Skipped'}")
    print(
        f"  - Differences found: {len(comparison_result.get('differences', []))}")
    print(
        f"  - Learned parameters: {len(learned_params) if learned_params else 0}")
    print(
        f"  - Final parameters: {len(final_params) if learned_params else len(updated_params)}")
    print()
    print("Next steps:")
    print("  - Start training with updated parameters")
    print("  - Monitor performance improvements")
    print("=" * 70)


if __name__ == "__main__":
    main()
