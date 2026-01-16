#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integrated Learning Workflow

리플레이 학습 데이터 수집 → 최적화 → 비교 분석 → 학습 실행 → 개선화
"""

import json
import sys
import statistics
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from collections import defaultdict

# Add parent directory to path
script_dir = Path(__file__).parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

PROJECT_ROOT = script_dir


def collect_replay_data(
        replay_dir: Path, max_replays: int = 100) -> Dict[str, List[float]]:
    """Collect build order data from replays"""
    print(f"\n[STEP 1] Collecting replay data from {replay_dir}...")

    try:
        from local_training.scripts.replay_build_order_learner import ReplayBuildOrderExtractor

        extractor = ReplayBuildOrderExtractor(replay_dir=str(replay_dir))
        replay_files = extractor.scan_replays()

        if not replay_files:
            print(f"[WARNING] No replay files found in {replay_dir}")
            return {}

        print(f"[INFO] Found {len(replay_files)} replay files")

        # Extract build orders
        max_process = min(max_replays, len(replay_files))
        timings_data: Dict[str, List[float]] = defaultdict(list)

        for i, replay_path in enumerate(replay_files[:max_process], 1):
            try:
                build_order = extractor.extract_build_order(replay_path)
                if build_order:
                    for param_name in [
                        "natural_expansion_supply",
                        "gas_supply",
                        "spawning_pool_supply",
                        "third_hatchery_supply",
                        "speed_upgrade_supply",
                        "lair_supply",
                        "roach_warren_supply",
                        "hive_supply",
                            "hydralisk_den_supply"]:
                        if param_name in build_order:
                            value = build_order[param_name]
                            if value is not None:
                                timings_data[param_name].append(float(value))

                if i % 10 == 0:
                    print(f"  Processed {i}/{max_process} replays...")
            except Exception as e:
                if i <= 5:  # Log first few errors
                    print(
                        f"  [WARNING] Failed to extract from {replay_path.name}: {e}")
                continue

        print(f"[SUCCESS] Collected data from {max_process} replays")
        return dict(timings_data)

    except Exception as e:
        print(f"[ERROR] Failed to collect replay data: {e}")
        import traceback
        traceback.print_exc()
        return {}


def optimize_parameters(
        timings_data: Dict[str, List[float]]) -> Dict[str, float]:
    """Find optimal parameters from collected data"""
    print(f"\n[STEP 2] Optimizing parameters from collected data...")

    optimal_params = {}

    for param_name, values in timings_data.items():
        if not values:
            continue

        # Use median for robustness (less affected by outliers)
        median_value = statistics.median(values)
        mean_value = statistics.mean(values)

        # Use median, but if there's significant difference, analyze further
        if len(values) >= 10:
            std_dev = statistics.stdev(values) if len(values) > 1 else 0

            # If standard deviation is small, mean is reliable
            # If large, median is more robust
            if std_dev < 3.0:
                optimal_value = round(mean_value, 1)
            else:
                optimal_value = round(median_value, 1)
        else:
            optimal_value = round(median_value, 1)

        optimal_params[param_name] = max(
            6.0, optimal_value)  # Minimum supply 6

        print(
            f"  {param_name}: median={median_value:.1f}, mean={mean_value:.1f}, "
            f"optimal={optimal_value:.1f}, samples={len(values)}")

    return optimal_params


def compare_with_training_data(
        optimal_params: Dict[str, float]) -> Dict[str, Any]:
    """Compare optimal parameters with training data"""
    print(f"\n[STEP 3] Comparing optimal parameters with training data...")

    comparison_path = PROJECT_ROOT / "local_training" / \
        "scripts" / "build_order_comparison_history.json"

    comparison_result = {
        "optimal_params": optimal_params,
        "training_params": {},
        "differences": []
    }

    if not comparison_path.exists():
        print("[INFO] No training comparison data found")
        return comparison_result

    try:
        with open(comparison_path, 'r', encoding='utf-8') as f:
            comp_data = json.load(f)

        comparisons = comp_data.get("comparisons", [])
        if not comparisons:
            print("[INFO] No training comparisons found")
            return comparison_result

        # Aggregate training data
        training_timings: Dict[str, List[float]] = defaultdict(list)

        for comp in comparisons:
            training_build = comp.get("training_build", {})
            for param_name, value in training_build.items():
                if value is not None:
                    training_timings[param_name].append(float(value))

        # Calculate training medians
        training_params = {}
        for param_name, values in training_timings.items():
            if values:
                training_params[param_name] = statistics.median(values)

        comparison_result["training_params"] = training_params

        # Find differences
        all_params = set(optimal_params.keys()) | set(training_params.keys())

        for param_name in all_params:
            optimal_value = optimal_params.get(param_name)
            training_value = training_params.get(param_name)

            if optimal_value is not None and training_value is not None:
                diff = abs(optimal_value - training_value)
                if diff > 2.0:  # Significant difference
                    comparison_result["differences"].append({
                        "parameter": param_name,
                        "optimal": optimal_value,
                        "training": training_value,
                        "difference": diff
                    })
                    print(
                        f"  [DIFF] {param_name}: optimal={optimal_value:.1f}, "
                        f"training={training_value:.1f}, diff={diff:.1f}")
            elif optimal_value is not None:
                comparison_result["differences"].append({
                    "parameter": param_name,
                    "optimal": optimal_value,
                    "training": None,
                    "difference": None,
                    "note": "Not executed in training"
                })
                print(
                    f"  [MISSING] {param_name}: optimal={optimal_value:.1f}, training=null")

    except Exception as e:
        print(f"[WARNING] Failed to compare with training data: {e}")

    return comparison_result


def apply_optimal_parameters(optimal_params: Dict[str, float]) -> bool:
    """Apply optimal parameters to learned_build_orders.json and config"""
    print(f"\n[STEP 4] Applying optimal parameters...")

    learned_path = PROJECT_ROOT / "local_training" / \
        "scripts" / "learned_build_orders.json"

    # Load current parameters
    current_params = {}
    if learned_path.exists():
        try:
            with open(learned_path, 'r', encoding='utf-8') as f:
                current_params = json.load(f)
        except Exception as e:
            print(f"[WARNING] Failed to load current parameters: {e}")

    # Merge optimal parameters (optimal takes priority)
    updated_params = current_params.copy()
    changes = []

    for param_name, optimal_value in optimal_params.items():
        current_value = current_params.get(param_name)
        if current_value != optimal_value:
            updated_params[param_name] = optimal_value
            changes.append({
                "parameter": param_name,
                "old": current_value,
                "new": optimal_value
            })
            print(
                f"  [UPDATE] {param_name}: {current_value} → {optimal_value}")
        else:
            print(f"  [KEEP] {param_name}: {optimal_value} (unchanged)")

    if not changes:
        print("[INFO] All parameters are already optimal")
        return False

    # Save updated parameters
    learned_path.parent.mkdir(parents=True, exist_ok=True)
    with open(learned_path, 'w', encoding='utf-8') as f:
        json.dump(updated_params, f, indent=2, ensure_ascii=False)

    print(f"[SAVED] Updated {len(changes)} parameters to {learned_path}")

    # Update config
    try:
        from local_training.scripts.replay_build_order_learner import update_config_with_learned_params
        update_config_with_learned_params(updated_params)
        print("[SUCCESS] Config updated with optimal parameters")
    except Exception as e:
        print(f"[WARNING] Failed to update config: {e}")

    return True


def start_improvement_cycle():
    """Start continuous improvement cycle"""
    print(f"\n[STEP 5] Starting improvement cycle...")

    print("[INFO] Improvement cycle started:")
    print("  1. Monitor training performance")
    print("  2. Collect new training data")
    print("  3. Compare with optimal parameters")
    print("  4. Adjust parameters based on results")
    print("  5. Repeat cycle")

    # Save improvement status
    status_path = PROJECT_ROOT / "local_training" / "improvement_status.json"
    status_data = {
        "last_update": datetime.now().isoformat(),
        "status": "active",
        "cycle_count": 1,
        "next_check": None
    }

    if status_path.exists():
        try:
            with open(status_path, 'r', encoding='utf-8') as f:
                old_status = json.load(f)
                status_data["cycle_count"] = old_status.get(
                    "cycle_count", 0) + 1
        except Exception:
            pass

    status_path.parent.mkdir(parents=True, exist_ok=True)
    with open(status_path, 'w', encoding='utf-8') as f:
        json.dump(status_data, f, indent=2, ensure_ascii=False)

    print(f"[SAVED] Improvement status saved to {status_path}")
    print(f"[INFO] Current cycle: {status_data['cycle_count']}")


def main():
    """Main function"""
    print("\n" + "=" * 70)
    print("INTEGRATED LEARNING WORKFLOW")
    print("=" * 70)
    print("Collecting replay data → Optimizing → Comparing → Learning → Improving")
    print()

    # Configuration
    replay_dir = Path("D:/replays/replays")
    if not replay_dir.exists():
        replay_dir = Path("replays_archive")

    if not replay_dir.exists():
        print(f"[ERROR] Replay directory not found: {replay_dir}")
        print("[INFO] Please ensure replay directory exists")
        return

    max_replays = 100  # Process up to 100 replays

    # Step 1: Collect replay data
    timings_data = collect_replay_data(replay_dir, max_replays)

    if not timings_data:
        print("[ERROR] No data collected from replays")
        return

    # Step 2: Optimize parameters
    optimal_params = optimize_parameters(timings_data)

    if not optimal_params:
        print("[ERROR] No optimal parameters found")
        return

    print(f"\n[SUCCESS] Found {len(optimal_params)} optimal parameters")

    # Step 3: Compare with training data
    comparison_result = compare_with_training_data(optimal_params)

    if comparison_result["differences"]:
        print(
            f"\n[INFO] Found {len(comparison_result['differences'])} differences")

    # Step 4: Apply optimal parameters
    params_updated = apply_optimal_parameters(optimal_params)

    # Step 5: Start improvement cycle
    start_improvement_cycle()

    # Final summary
    print("\n" + "=" * 70)
    print("INTEGRATED LEARNING WORKFLOW COMPLETE")
    print("=" * 70)
    print(f"\nSummary:")
    print(f"  - Replays processed: {max_replays}")
    print(f"  - Optimal parameters found: {len(optimal_params)}")
    print(f"  - Parameters updated: {params_updated}")
    print(f"  - Differences found: {len(comparison_result['differences'])}")
    print(f"\nNext steps:")
    print(f"  1. Run training with optimized parameters")
    print(f"  2. Monitor performance")
    print(f"  3. Collect new data and repeat cycle")
    print("=" * 70)


if __name__ == "__main__":
    main()
