#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Optimize Learning Data

������ �н� �����͸� �м��ϰ� ����ȭ�ϴ� ��ũ��Ʈ�Դϴ�.
- �̻�ġ ����
- ��� �м�
- ���� �Ķ���� ����
- ������ ����ȭ
"""

import json
import sys
import statistics
from pathlib import Path
from typing import Dict
import List
import Any
import Tuple
from collections import defaultdict
from datetime import datetime

# Add parent directory to path
script_dir = Path(__file__).parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

PROJECT_ROOT = script_dir


def load_learning_data() -> Dict[str, Any]:
    """Load all learning data sources"""
    data = {
        "learned_params": {},
        "comparison_history": [],
        "training_stats": []
    }

    # Load learned build orders
    learned_path = PROJECT_ROOT / "local_training" / \
        "scripts" / "learned_build_orders.json"
    if learned_path.exists():
        try:
            with open(learned_path, 'r', encoding='utf-8') as f:
                data["learned_params"] = json.load(f)
        except Exception as e:
            print(f"[WARNING] Failed to load learned params: {e}")

    # Load comparison history
    comp_path = PROJECT_ROOT / "local_training" / \
        "scripts" / "build_order_comparison_history.json"
    if comp_path.exists():
        try:
            with open(comp_path, 'r', encoding='utf-8') as f:
                comp_data = json.load(f)
                data["comparison_history"] = comp_data.get("comparisons", [])
        except Exception as e:
            print(f"[WARNING] Failed to load comparison history: {e}")

    # Load training stats
    stats_path = PROJECT_ROOT / "training_stats.json"
    if stats_path.exists():
        try:
            with open(stats_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data["training_stats"].append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            print(f"[WARNING] Failed to load training stats: {e}")

    return data


def extract_timing_data(
        learning_data: Dict[str, Any]) -> Dict[str, List[float]]:
    """Extract timing data from all sources"""
    timings: Dict[str, List[float]] = defaultdict(list)

    # From learned params (baseline)
    for param_name, value in learning_data["learned_params"].items():
        if value is not None:
            timings[param_name].append(float(value))

    # From comparison history
    for comp in learning_data["comparison_history"]:
        training_build = comp.get("training_build", {})
        pro_baseline = comp.get("pro_baseline", {})

        # Training timings (only if executed)
        for param_name, value in training_build.items():
            if value is not None:
                timings[param_name].append(float(value))

        # Pro baseline timings
        for param_name, value in pro_baseline.items():
            if value is not None:
                timings[param_name].append(float(value))

    # From training stats (if available)
    for stat in learning_data["training_stats"]:
        # Extract build order timings if available
        if "build_order" in stat:
            build_order = stat["build_order"]
            for param_name, value in build_order.items():
                if value is not None and isinstance(value, (int, float)):
                    timings[param_name].append(float(value))

    return dict(timings)


def remove_outliers(values: List[float],
                    method: str = "iqr") -> Tuple[List[float],
                                                  List[float]]:
    """Remove outliers from data"""
    if len(values) < 3:
        return values, []

    if method == "iqr":
        # Interquartile Range method
        q1 = statistics.quantiles(values, n=4)[0]
        q3 = statistics.quantiles(values, n=4)[2]
        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        filtered = [v for v in values if lower_bound <= v <= upper_bound]
        outliers = [v for v in values if v < lower_bound or v > upper_bound]

        return filtered, outliers

    elif method == "zscore":
        # Z-score method
        mean = statistics.mean(values)
        std_dev = statistics.stdev(values) if len(values) > 1 else 0

        if std_dev == 0:
            return values, []

        filtered = [v for v in values if abs((v - mean) / std_dev) <= 2.0]
        outliers = [v for v in values if abs((v - mean) / std_dev) > 2.0]

        return filtered, outliers

    return values, []


def calculate_optimal_parameters(
        timings: Dict[str, List[float]], remove_outliers_flag: bool = True) -> Dict[str, Dict[str, Any]]:
    """Calculate optimal parameters with statistics"""
    optimal_params = {}

    for param_name, values in timings.items():
        if not values:
            continue

        original_count = len(values)

        # Remove outliers
        if remove_outliers_flag and len(values) >= 3:
            filtered_values, outliers = remove_outliers(values, method="iqr")
        else:
            filtered_values = values
            outliers = []

        if not filtered_values:
            continue

        # Calculate statistics
        mean_value = statistics.mean(filtered_values)
        median_value = statistics.median(filtered_values)
        std_dev = statistics.stdev(filtered_values) if len(
            filtered_values) > 1 else 0

        # Determine optimal value
        # Use median for robustness, but consider mean if std_dev is small
        if std_dev < 2.0 and len(filtered_values) >= 5:
            # Low variance, mean is reliable
            optimal_value = round(mean_value, 1)
            method = "mean (low variance)"
        else:
            # High variance or small sample, median is more robust
            optimal_value = round(median_value, 1)
            method = "median (robust)"

        # Ensure minimum value
        optimal_value = max(6.0, optimal_value)

        optimal_params[param_name] = {
            "optimal_value": optimal_value,
            "mean": round(mean_value, 2),
            "median": round(median_value, 2),
            "std_dev": round(std_dev, 2),
            "min": round(min(filtered_values), 2),
            "max": round(max(filtered_values), 2),
            "sample_count": len(filtered_values),
            "original_count": original_count,
            "outliers_removed": len(outliers),
            "method": method
        }

    return optimal_params


def optimize_parameters(
        optimal_params: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
    """Extract optimized parameter values"""
    return {param_name: data["optimal_value"]
            for param_name, data in optimal_params.items()}


def save_optimized_data(
        optimized_params: Dict[str, float], statistics: Dict[str, Dict[str, Any]]):
    """Save optimized parameters and statistics"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save optimized parameters
    learned_path = PROJECT_ROOT / "local_training" / \
        "scripts" / "learned_build_orders.json"
    learned_path.parent.mkdir(parents=True, exist_ok=True)

    with open(learned_path, 'w', encoding='utf-8') as f:
        json.dump(optimized_params, f, indent=2, ensure_ascii=False)

    print(f"[SAVED] Optimized parameters: {learned_path}")

    # Save statistics
    stats_path = PROJECT_ROOT / "local_training" / \
        "optimization_stats" / f"optimization_{timestamp}.json"
    stats_path.parent.mkdir(parents=True, exist_ok=True)

    stats_data = {
        "timestamp": timestamp,
        "optimized_parameters": optimized_params,
        "statistics": statistics,
        "optimization_method": "iqr_outlier_removal"
    }

    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats_data, f, indent=2, ensure_ascii=False)

    print(f"[SAVED] Optimization statistics: {stats_path}")

    return learned_path, stats_path


def update_config(optimized_params: Dict[str, float]):
    """Update config with optimized parameters"""
    try:
        from local_training.scripts.replay_build_order_learner import update_config_with_learned_params
        update_config_with_learned_params(optimized_params)
        print("[SUCCESS] Config updated with optimized parameters")
        return True
    except Exception as e:
        print(f"[WARNING] Failed to update config: {e}")
        return False


def main():
    """Main function"""
    print("\n" + "=" * 70)
    print("LEARNING DATA OPTIMIZATION")
    print("=" * 70)
    print()

    # Step 1: Load learning data
    print("[STEP 1] Loading learning data...")
    learning_data = load_learning_data()

    print(f"  - Learned parameters: {len(learning_data['learned_params'])}")
    print(
        f"  - Comparison records: {len(learning_data['comparison_history'])}")
    print(
        f"  - Training stats records: {len(learning_data['training_stats'])}")

    # Step 2: Extract timing data
    print("\n[STEP 2] Extracting timing data...")
    timings = extract_timing_data(learning_data)

    if not timings:
        print("[ERROR] No timing data found")
        return

    print(f"  - Parameters with data: {len(timings)}")
    for param_name, values in timings.items():
        print(f"    {param_name}: {len(values)} samples")

    # Step 3: Calculate optimal parameters
    print("\n[STEP 3] Calculating optimal parameters...")
    optimal_stats = calculate_optimal_parameters(
        timings, remove_outliers_flag=True)

    if not optimal_stats:
        print("[ERROR] No optimal parameters calculated")
        return

    # Step 4: Display optimization results
    print("\n[STEP 4] Optimization results:")
    print("-" * 70)

    for param_name, stats in optimal_stats.items():
        print(f"\n{param_name}:")
        print(f"  Optimal value: {stats['optimal_value']}")
        print(f"  Mean: {stats['mean']}, Median: {stats['median']}")
        print(
            f"  Std Dev: {stats['std_dev']}, Range: {stats['min']} - {stats['max']}")
        print(
            f"  Samples: {stats['sample_count']} (original: {stats['original_count']}, outliers removed: {stats['outliers_removed']})")
        print(f"  Method: {stats['method']}")

    # Step 5: Extract optimized parameters
    print("\n[STEP 5] Extracting optimized parameters...")
    optimized_params = optimize_parameters(optimal_stats)

    print(f"  - Optimized parameters: {len(optimized_params)}")
    for param_name, value in sorted(optimized_params.items()):
        current = learning_data["learned_params"].get(param_name)
        if current != value:
            print(f"    {param_name}: {current} �� {value} (updated)")
        else:
            print(f"    {param_name}: {value} (unchanged)")

    # Step 6: Save optimized data
    print("\n[STEP 6] Saving optimized data...")
    learned_path, stats_path = save_optimized_data(
        optimized_params, optimal_stats)

    # Step 7: Update config
    print("\n[STEP 7] Updating config...")
    update_config(optimized_params)

    # Summary
    print("\n" + "=" * 70)
    print("OPTIMIZATION COMPLETE")
    print("=" * 70)
    print(f"\nSummary:")
    print(f"  - Parameters optimized: {len(optimized_params)}")
    print(
        f"  - Total samples analyzed: {sum(len(v) for v in timings.values())}")
    print(
        f"  - Outliers removed: {sum(s['outliers_removed'] for s in optimal_stats.values())}")
    print(f"  - Optimized parameters saved: {learned_path}")
    print(f"  - Statistics saved: {stats_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
