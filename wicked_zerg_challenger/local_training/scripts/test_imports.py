#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test imports for replay build order learner"""

import sys
from pathlib import Path

script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

print("Testing imports...")
print(f"Script directory: {script_dir}")
print(f"Python path: {sys.path[:3]}")

modules_to_test = [
    "replay_learning_manager",
    "learning_logger",
    "strategy_database",
    "replay_crash_handler",
    "learning_status_manager"
]

for module_name in modules_to_test:
    try:
        __import__(module_name)
        print(f"[OK] {module_name}")
    except ImportError as e:
        print(f"[FAIL] {module_name}: {e}")
    except Exception as e:
        print(f"[ERROR] {module_name}: {e}")
