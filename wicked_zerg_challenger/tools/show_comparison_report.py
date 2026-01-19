#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Show Comparison Analysis Report
"""

import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
LATEST_COMPARISON = PROJECT_ROOT / "local_training" / "comparison_reports" / "comparison_20260116_212712.json"
HISTORY_FILE = PROJECT_ROOT / "local_training" / "scripts" / "build_order_comparison_history.json"

print("=" * 70)
print("REPLAY LEARNING DATA COMPARISON ANALYSIS REPORT")
print("=" * 70)
print()

# Load latest comparison
if LATEST_COMPARISON.exists():
    with open(LATEST_COMPARISON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("[LATEST COMPARISON]")
    print("-" * 70)
    print(f"Timestamp: {data['timestamp']}")
    print(f"Pro Replays Analyzed: {data['pro_data']['replay_count']}")
    print(f"Training Games Analyzed: {data['training_data']['game_count']}")
    print()

    perf = data['performance_analysis']
    print("[PERFORMANCE SUMMARY]")
    print("-" * 70)
    print(f"Win Rate: {perf['win_rate']*100:.1f}%")
    print(f"Victories: {perf['victories']}")
    print(f"Defeats: {perf['defeats']}")
    print(f"Avg Build Order Score: {perf['avg_build_order_score']*100:.1f}%")
    print()

    print("[PRO BASELINE]")
    print("-" * 70)
    baseline = data['pro_data']['baseline']
    for key, value in sorted(baseline.items()):
        print(f"  {key}: {value} supply")
    print()

    print("[TIMING COMPARISONS]")
    print("-" * 70)
    comparisons = data['timing_comparisons']
    issues = []
    for param, comp in comparisons.items():
        pro_baseline = comp.get('pro_baseline')
        training_mean = comp.get('training_mean')
        if pro_baseline is not None and training_mean is None:
            issues.append(f"  [MISSING] {param}: Pro baseline {pro_baseline}, Training data not available")
        elif pro_baseline is not None and training_mean is not None:
            diff = training_mean - pro_baseline
            print(f"  {param}: Pro {pro_baseline}, Training {training_mean:.1f}, Diff {diff:+.1f}")

    if issues:
        print("\n[CRITICAL ISSUES]")
        print("-" * 70)
        for issue in issues:
            print(issue)
    print()
else:
    print("[WARNING] Latest comparison file not found")

# Load comparison history
if HISTORY_FILE.exists():
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        history = json.load(f)

    print("[COMPARISON HISTORY]")
    print("-" * 70)
    print(f"Total Comparisons: {history.get('total_comparisons', 0)}")
    print(f"Last Updated: {history.get('last_updated', 'N/A')}")
    print()

    comparisons = history.get('comparisons', [])
    if comparisons:
        latest_comp = comparisons[-1]
        print("[LATEST COMPARISON DETAIL]")
        print("-" * 70)
        print(f"Game ID: {latest_comp.get('game_id', 'N/A')}")
        print(f"Result: {latest_comp.get('game_result', 'N/A')}")
        print(f"Overall Score: {latest_comp.get('overall_score', 0)*100:.1f}%")
        print()

        recs = latest_comp.get('recommendations', [])
        if recs:
            print("[RECOMMENDATIONS]")
            print("-" * 70)
            for rec in recs:
                print(f"  {rec}")
        print()
else:
    print("[WARNING] Comparison history file not found")

print("=" * 70)
print(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)
