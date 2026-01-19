#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Show learning rate and training statistics"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# Training statistics
stats_file = PROJECT_ROOT / "local_training/scripts/training_session_stats.json"
print("=" * 70)
print("TRAINING STATISTICS")
print("=" * 70)

if stats_file.exists():
    stats = json.load(open(stats_file, encoding='utf-8'))
    session_stats = stats.get('session_stats', {})
    
    print(f"Total Games: {session_stats.get('total_games', 0)}")
    print(f"Wins: {session_stats.get('wins', 0)}")
    print(f"Losses: {session_stats.get('losses', 0)}")
    print(f"Win Rate: {session_stats.get('win_rate', 0):.2f}%")
    print(f"Average Game Time: {session_stats.get('average_game_time', 0):.1f}s")
    print(f"Consecutive Wins: {session_stats.get('consecutive_wins', 0)}")
    print(f"Consecutive Losses: {session_stats.get('consecutive_losses', 0)}")
    print(f"Current Difficulty: {session_stats.get('current_difficulty', 'Unknown')}")
    print(f"Last 10 Games Win Rate: {session_stats.get('last_10_games_win_rate', 0):.2f}%")
    print(f"Best Win Rate: {session_stats.get('best_win_rate', 0):.2f}%")
    print(f"Worst Win Rate: {session_stats.get('worst_win_rate', 0):.2f}%")
else:
    print("Training stats file not found")

print()
print("=" * 70)
print("LEARNED BUILD ORDER PARAMETERS")
print("=" * 70)

# Learned parameters
params_file = PROJECT_ROOT / "local_training/scripts/learned_build_orders.json"
if params_file.exists():
    params = json.load(open(params_file, encoding='utf-8'))
    learned = params.get('learned_parameters', params)
    
    if learned:
        for k, v in sorted(learned.items()):
            if isinstance(v, (int, float)):
                print(f"{k}: {v:.2f}")
            else:
                print(f"{k}: {v}")
    else:
        print("No learned parameters found")
else:
    print("Learned parameters file not found")

print()
print("=" * 70)
