#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Entry Point - Complete System Launcher

This is the main entry point for the entire system.
After git clone, users can immediately run:
    python main.py

This script provides a menu-driven interface to:
1. Run the bot (with or without SC2)
2. Train the bot (replay learning + game training)
3. Run mock battles (no SC2 required)
4. Clean and maintain the project
5. View documentation

Usage:
    python main.py [--quick-start] [--mock-only]
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Add wicked_zerg_challenger to path
WICKED_ZERG_PATH = PROJECT_ROOT / "wicked_zerg_challenger"
if WICKED_ZERG_PATH.exists():
    sys.path.insert(0, str(WICKED_ZERG_PATH))

# Add src to path
SRC_PATH = PROJECT_ROOT / "src"
if SRC_PATH.exists():
    sys.path.insert(0, str(SRC_PATH))


def print_banner():
    """Print welcome banner."""
    print("=" * 70)
    print("? SWARM CONTROL IN SC2BOT - Complete System")
    print("=" * 70)
    print()
    print("From Simulation to Reality: Autonomous Swarm Control & Intelligent Management")
    print("가상 시뮬레이션 환경을 활용한 군집 제어 강화학습 및 지능형 통합 관제 시스템")
    print()
    print("=" * 70)
    print()


def check_requirements():
    """Check if required packages are installed."""
    required_packages = {
        'numpy': 'numpy',
        'torch': 'torch',
    }
    
    missing = []
    for module_name, package_name in required_packages.items():
        try:
            __import__(module_name)
        except ImportError:
            missing.append(package_name)
    
    if missing:
        print("[WARNING] Missing required packages:")
        for pkg in missing:
            print(f"  - {pkg}")
        print()
        print("Install with:")
        print(f"  pip install {' '.join(missing)}")
        print()
        return False
    
    return True


def run_bot():
    """Run the actual SC2 bot."""
    print("\n[OPTION 1] Running SC2 Bot...")
    print("-" * 70)
    
    run_py = WICKED_ZERG_PATH / "run.py"
    if not run_py.exists():
        print("[ERROR] run.py not found!")
        print(f"[INFO] Expected location: {run_py}")
        return False
    
    try:
        import subprocess
        result = subprocess.run([sys.executable, str(run_py)], cwd=str(WICKED_ZERG_PATH))
        return result.returncode == 0
    except Exception as e:
        print(f"[ERROR] Failed to run bot: {e}")
        return False


def run_mock_battle():
    """Run mock battle simulation (no SC2 required)."""
    print("\n[OPTION 2] Running Mock Battle Simulation...")
    print("-" * 70)
    
    mock_script = PROJECT_ROOT / "scripts" / "run_mock_battle.py"
    if not mock_script.exists():
        print("[ERROR] run_mock_battle.py not found!")
        print(f"[INFO] Expected location: {mock_script}")
        return False
    
    try:
        import subprocess
        result = subprocess.run([sys.executable, str(mock_script)], cwd=str(PROJECT_ROOT))
        return result.returncode == 0
    except Exception as e:
        print(f"[ERROR] Failed to run mock battle: {e}")
        return False


def run_training():
    """Run training pipeline."""
    print("\n[OPTION 3] Running Training Pipeline...")
    print("-" * 70)
    
    pipeline_script = WICKED_ZERG_PATH / "tools" / "integrated_pipeline.py"
    if not pipeline_script.exists():
        print("[ERROR] integrated_pipeline.py not found!")
        print(f"[INFO] Expected location: {pipeline_script}")
        return False
    
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, str(pipeline_script), "--epochs", "3"],
            cwd=str(WICKED_ZERG_PATH)
        )
        return result.returncode == 0
    except Exception as e:
        print(f"[ERROR] Failed to run training: {e}")
        return False


def clean_project():
    """Clean duplicate files and temporary files."""
    print("\n[OPTION 4] Cleaning Project...")
    print("-" * 70)
    
    clean_script = WICKED_ZERG_PATH / "tools" / "clean_duplicates.py"
    if not clean_script.exists():
        print("[ERROR] clean_duplicates.py not found!")
        print(f"[INFO] Expected location: {clean_script}")
        return False
    
    try:
        import subprocess
        # First show what would be removed (dry run)
        print("[DRY RUN] Showing what would be removed...")
        result = subprocess.run(
            [sys.executable, str(clean_script), "--dry-run", "--verbose"],
            cwd=str(PROJECT_ROOT)
        )
        
        if result.returncode == 0:
            response = input("\nProceed with cleanup? (y/n): ").lower().strip()
            if response == 'y':
                print("\n[LIVE] Removing files...")
                result = subprocess.run(
                    [sys.executable, str(clean_script), "--verbose"],
                    cwd=str(PROJECT_ROOT)
                )
                return result.returncode == 0
        
        return False
    except Exception as e:
        print(f"[ERROR] Failed to clean project: {e}")
        return False


def show_documentation():
    """Show documentation."""
    print("\n[OPTION 5] Documentation...")
    print("-" * 70)
    print()
    print("Available documentation:")
    print()
    
    docs = [
        ("README.md", "Main project README"),
        ("README_NEW_STRUCTURE.md", "New structure documentation"),
        ("QUICK_START.md", "Quick start guide"),
        ("wicked_zerg_challenger/README.md", "Bot documentation"),
    ]
    
    for doc_path, description in docs:
        full_path = PROJECT_ROOT / doc_path
        if full_path.exists():
            print(f"  ? {doc_path} - {description}")
        else:
            print(f"  ? {doc_path} - {description} (not found)")
    
    print()
    print("For more information, see the docs/ directory.")


def main():
    """Main menu."""
    print_banner()
    
    # Check requirements
    if not check_requirements():
        print("[WARNING] Some requirements are missing. Some features may not work.")
        print()
    
    # Quick start mode
    if "--quick-start" in sys.argv or "--mock-only" in sys.argv:
        print("[QUICK START] Running mock battle simulation...")
        return run_mock_battle()
    
    # Interactive menu
    while True:
        print("\n" + "=" * 70)
        print("MAIN MENU")
        print("=" * 70)
        print()
        print("1. Run SC2 Bot (requires StarCraft II)")
        print("2. Run Mock Battle (no SC2 required)")
        print("3. Run Training Pipeline")
        print("4. Clean Project (remove duplicates & temp files)")
        print("5. View Documentation")
        print("0. Exit")
        print()
        
        choice = input("Enter your choice (0-5): ").strip()
        
        if choice == "0":
            print("\n[EXIT] Goodbye!")
            break
        elif choice == "1":
            run_bot()
        elif choice == "2":
            run_mock_battle()
        elif choice == "3":
            run_training()
        elif choice == "4":
            clean_project()
        elif choice == "5":
            show_documentation()
        else:
            print("[ERROR] Invalid choice. Please enter 0-5.")
        
        if choice in ["1", "2", "3", "4"]:
            input("\nPress Enter to continue...")


if __name__ == "__main__":
    try:
        sys.exit(0 if main() else 1)
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Exiting...")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
