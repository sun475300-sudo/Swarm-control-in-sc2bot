#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check training status"""

import json
import time
from pathlib import Path

# Check status files
status_file = Path("local_training/stats/instance_0_status.json")
root_status_file = Path("stats/instance_0/status.json")

status_data = None
if status_file.exists():
    status_data = json.loads(status_file.read_text(encoding="utf-8"))
elif root_status_file.exists():
    status_data = json.loads(root_status_file.read_text(encoding="utf-8"))

if status_data:
    print("=" * 70)
    print("TRAINING STATUS")
    print("=" * 70)
    print(f"Status: {status_data.get('status', 'N/A')}")
    print(f"Game Count: {status_data.get('game_count', 0)}")
    print(f"Wins: {status_data.get('win_count', 0)} | Losses: {status_data.get('loss_count', 0)}")
    print(f"Last Result: {status_data.get('last_result', 'N/A')}")
    print(f"Current Map: {status_data.get('current_map', 'N/A')}")
    print(f"Difficulty: {status_data.get('difficulty', 'N/A')}")
    print(f"Personality: {status_data.get('personality', 'N/A')}")
    print(f"Mode: {status_data.get('mode', 'N/A')}")
    
    # Calculate time since last update
    timestamp = status_data.get('timestamp', 0)
    if timestamp > 0:
        age = time.time() - timestamp
        print(f"Last Update: {age:.1f} seconds ago")
    
    print("=" * 70)
else:
    print("Status file not found. Training may not be running.")

# Check for Python processes
import subprocess
try:
    result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq python.exe"], 
                          capture_output=True, text=True)
    if "python.exe" in result.stdout:
        print("\nPython processes running:")
        print(result.stdout)
    else:
        print("\nNo Python processes found.")
except Exception as e:
    print(f"\nCould not check processes: {e}")
