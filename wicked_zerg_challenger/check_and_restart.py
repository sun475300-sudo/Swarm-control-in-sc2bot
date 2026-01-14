#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check training status and restart if needed"""

import subprocess
import sys
import time
import json
from pathlib import Path

def check_python_processes():
    """Check if Python processes are running"""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
            capture_output=True,
            text=True
        )
        lines = [l for l in result.stdout.split('\n') if 'python.exe' in l and 'python.exe' not in l.split(',')[0]]
        return len(lines), lines
    except Exception as e:
        print(f"Error checking processes: {e}")
        return 0, []

def check_status_file():
    """Check status file for last update time"""
    status_file = Path("local_training/stats/instance_0_status.json")
    if not status_file.exists():
        return None, 999999
    
    try:
        data = json.loads(status_file.read_text(encoding='utf-8'))
        timestamp = data.get('timestamp', 0)
        age = time.time() - timestamp if timestamp > 0 else 999999
        return data, age
    except Exception as e:
        print(f"Error reading status file: {e}")
        return None, 999999

def kill_python_processes():
    """Kill all Python processes"""
    try:
        subprocess.run(["taskkill", "/F", "/IM", "python.exe"], 
                      capture_output=True, text=True)
        print("Python processes killed")
        time.sleep(2)  # Wait for processes to close
        return True
    except Exception as e:
        print(f"Error killing processes: {e}")
        return False

def main():
    print("=" * 70)
    print("TRAINING STATUS CHECK")
    print("=" * 70)
    
    # 1. Check processes
    proc_count, proc_lines = check_python_processes()
    print(f"\n[1] Python processes: {proc_count}")
    if proc_count > 0:
        for line in proc_lines[:5]:
            parts = line.split(',')
            if len(parts) >= 2:
                print(f"   PID: {parts[1].strip()}")
    
    # 2. Check status file
    status_data, age = check_status_file()
    print(f"\n[2] Status file:")
    if status_data:
        print(f"   Status: {status_data.get('status', 'N/A')}")
        print(f"   Game Count: {status_data.get('game_count', 0)}")
        print(f"   Last Update: {age:.1f} seconds ago ({age/60:.1f} minutes)")
    else:
        print("   Status file not found")
    
    # 3. Determine if restart needed
    print(f"\n[3] Analysis:")
    needs_restart = False
    
    if proc_count == 0:
        print("   - No Python processes running")
        needs_restart = True
    elif age > 3600:  # More than 1 hour
        print(f"   - Status file not updated for {age/3600:.1f} hours (stale)")
        needs_restart = True
    elif status_data and status_data.get('status') == 'GAME_ENDED':
        print("   - Game ended, restart needed")
        needs_restart = True
    else:
        print("   - Training appears to be running normally")
    
    # 4. Restart if needed
    if needs_restart:
        print(f"\n[4] Restart needed")
        response = input("   Kill processes and restart? (y/n): ")
        if response.lower() == 'y':
            if proc_count > 0:
                kill_python_processes()
            print("   Starting training...")
            # Start training in background
            subprocess.Popen(
                ["python", "main_integrated.py"],
                cwd="local_training",
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            )
            print("   Training started")
        else:
            print("   Restart cancelled")
    else:
        print(f"\n[4] No restart needed - training is running")
    
    print("=" * 70)

if __name__ == "__main__":
    main()
