#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Show Learning Data

н ͸ ִ ũƮ
"""

import sys
import json
from pathlib import Path
from typing import Dict
import Any
import Optional
from datetime import datetime

# Add parent directory to path
script_dir = Path(__file__).parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

PROJECT_ROOT = script_dir


def load_json_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """Load JSON file"""
    try:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load {file_path}: {e}")
    return None


def show_training_stats():
    """Show training statistics"""
    print("\n" + "=" * 70)
    print("TRAINING STATISTICS")
    print("=" * 70)

    stats_file = PROJECT_ROOT / "training_stats.json"
    stats = load_json_file(stats_file)

    if stats:
        print(f"\nTotal Games: {stats.get('total_games', 0)}")
        print(f"Wins: {stats.get('wins', 0)}")
        print(f"Losses: {stats.get('losses', 0)}")
        print(f"Win Rate: {stats.get('win_rate', 0):.1f}%")
        print(
            f"Average Game Time: {stats.get('avg_game_time', 0):.1f} seconds")

        if 'games_per_instance' in stats:
            print(f"\nGames per Instance:")
            for instance, count in stats['games_per_instance'].items():
                print(f"  Instance {instance}: {count} games")

        if 'top_loss_reasons' in stats:
            print(f"\nTop Loss Reasons:")
            for reason, count in list(stats['top_loss_reasons'].items())[:5]:
                print(f"  {reason}: {count}")
    else:
        print("\n[INFO] No training statistics found")
        print("[INFO] Start training to generate statistics")


def show_learned_parameters():
    """Show learned build order parameters"""
    print("\n" + "=" * 70)
    print("LEARNED BUILD ORDER PARAMETERS")
    print("=" * 70)

    learned_file = PROJECT_ROOT / "local_training" / \
        "scripts" / "learned_build_orders.json"
    learned_data = load_json_file(learned_file)

    if learned_data:
        # Handle different data structures
        if isinstance(learned_data, dict):
            if 'learned_parameters' in learned_data:
                params = learned_data['learned_parameters']
            else:
                params = learned_data

            print(f"\nTotal Parameters: {len(params)}")
            print("\nParameters:")
            for param_name, value in sorted(params.items()):
                if isinstance(value, (int, float)):
                    print(f"  {param_name}: {value}")

            if 'source_replays' in learned_data:
                print(f"\nSource Replays: {learned_data['source_replays']}")
            if 'replay_directory' in learned_data:
                print(f"Replay Directory: {learned_data['replay_directory']}")
        else:
            print(f"\n[INFO] Data format: {type(learned_data)}")
            print(f"[INFO] Content: {str(learned_data)[:200]}")
    else:
        print("\n[INFO] No learned parameters found")
        print("[INFO] Run replay learning to generate parameters")


def show_comparison_data():
    """Show comparison analysis data"""
    print("\n" + "=" * 70)
    print("COMPARISON ANALYSIS DATA")
    print("=" * 70)

    comparison_file = PROJECT_ROOT / "local_training" / \
        "scripts" / "build_order_comparison_history.json"
    comparison_data = load_json_file(comparison_file)

    if comparison_data:
        comparisons = comparison_data.get('comparisons', [])
        print(f"\nTotal Comparisons: {len(comparisons)}")

        if comparisons:
            latest = comparisons[-1]
            print(f"\nLatest Comparison:")
            print(f"  Date: {latest.get('date', 'N/A')}")

            training_build = latest.get('training_build', {})
            pro_baseline = latest.get('pro_baseline', {})

            print(f"\n  Training Build Order:")
            for param, value in sorted(training_build.items()):
                if value is not None:
                    print(f"    {param}: {value}")

            print(f"\n  Pro Baseline:")
            for param, value in sorted(pro_baseline.items()):
                if value is not None:
                    print(f"    {param}: {value}")

            # Show differences
            differences = []
            for param in set(
                list(
                    training_build.keys())
                + list(
                    pro_baseline.keys())):
                train_val = training_build.get(param)
                pro_val = pro_baseline.get(param)
                if train_val != pro_val:
                    differences.append({
                        'param': param,
                        'training': train_val,
                        'pro': pro_val
                    })

            if differences:
                print(f"\n  Differences Found: {len(differences)}")
                for diff in differences[:10]:
                    print(
                        f"    {diff['param']}: Training={diff['training']}, Pro={diff['pro']}")
    else:
        print("\n[INFO] No comparison data found")
        print("[INFO] Run comparison analysis to generate data")


def show_archive_data():
    """Show archived learning data"""
    print("\n" + "=" * 70)
    print("ARCHIVED LEARNING DATA")
    print("=" * 70)

    archive_dir = Path("D:/replays/archive")
    if not archive_dir.exists():
        print("\n[INFO] Archive directory not found: D:/replays/archive")
        return

    # Find training directories
    training_dirs = [d for d in archive_dir.iterdir(
    ) if d.is_dir() and d.name.startswith('training_')]
    training_dirs.sort(reverse=True)  # Most recent first

    if training_dirs:
        print(f"\nFound {len(training_dirs)} training archives")
        print("\nRecent Training Archives:")
        for training_dir in training_dirs[:5]:
            print(f"\n  {training_dir.name}:")

            # Check for learned_build_orders.json
            learned_file = training_dir / "learned_build_orders.json"
            if learned_file.exists():
                data = load_json_file(learned_file)
                if data and isinstance(data, dict):
                    params = data.get('learned_parameters', data)
                    if isinstance(params, dict):
                        print(f"    Parameters: {len(params)}")
                        print(
                            f"    Source Replays: {data.get('source_replays', 'N/A')}")
    else:
        print("\n[INFO] No training archives found")


def main():
    """Main function"""
    print("\n" + "=" * 70)
    print("LEARNING DATA SUMMARY")
    print("=" * 70)
    print()
    print("Showing all learning data:")
    print("  1. Training statistics")
    print("  2. Learned build order parameters")
    print("  3. Comparison analysis data")
    print("  4. Archived learning data")
    print()

    # Show all data
    show_training_stats()
    show_learned_parameters()
    show_comparison_data()
    show_archive_data()

    print("\n" + "=" * 70)
    print("LEARNING DATA SUMMARY COMPLETE")
    print("=" * 70)
    print()
    print("[INFO] All learning data displayed above")
    print("[INFO] Use this information to track learning progress")
    print("=" * 70)


if __name__ == "__main__":
    main()
