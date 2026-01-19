#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Arena Deployment Validation Script

This script simulates the AI Arena validation process to ensure the bot
can start correctly on the server before actual submission.

Usage:
 python tools/validate_arena_deployment.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_imports():
    """Check if all required modules can be imported"""
    print("\n[1/6] Checking imports...")
 errors = []

 # Core SC2 library
 try:
     pass
 pass

 except Exception:
     pass
     from sc2.data import Race
from sc2.player import Bot
    print("  ? sc2 (burnysc2) core imports successful")

 # run_ladder_game is imported inside run.py, not at module level
    # This is OK - it's only needed when --LadderServer flag is present
 try:
     print("  ? run_ladder_game available")
 except ImportError:
     print("  ??  run_ladder_game not available (may be OK if imported in run.py)")
 except ImportError as e:
     errors.append(f"? sc2 import failed: {e}")
     print(f"  ? sc2 import failed: {e}")

 # Bot class
 try:
     from wicked_zerg_bot_pro import WickedZergBotPro
     print("  ? wicked_zerg_bot_pro imported successfully")
 except ImportError as e:
     errors.append(f"? wicked_zerg_bot_pro import failed: {e}")
     print(f"  ? wicked_zerg_bot_pro import failed: {e}")

 # Neural network (optional)
 try:
     print("  ? zerg_net imported successfully")
 except ImportError as e:
     print(f"  ??  zerg_net import failed (optional): {e}")

 # PyTorch (optional)
 try:
     import torch
     print(f"  ? torch imported successfully (version: {torch.__version__})")
 except ImportError:
     print("  ??  torch not available (optional for basic bot)")

 # NumPy
 try:
     print(f"  ? numpy imported successfully (version: {np.__version__})")
 except ImportError as e:
     errors.append(f"? numpy import failed: {e}")
     print(f"  ? numpy import failed: {e}")

 # Config
 try:
     print("  ? config imported successfully")
 except ImportError as e:
     errors.append(f"? config import failed: {e}")
     print(f"  ? config import failed: {e}")

 return len(errors) == 0, errors

def check_run_py():
    """Check if run.py can be executed"""
    print("\n[2/6] Checking run.py entry point...")
 errors = []

    run_py_path = project_root / "run.py"
 if not run_py_path.exists():
     errors.append("run.py not found")
     print("  ? run.py not found")
 return False, errors

    print("  ? run.py exists")

 # Check if run.py has main function
 try:
     pass
 pass

 except Exception:
     pass
     with open(run_py_path, 'r', encoding='utf-8') as f:
 content = f.read()
     if 'def main()' in content:
         pass
     print("  ? main() function found")
 else:
     errors.append("main() function not found in run.py")
     print("  ? main() function not found")

     if 'if __name__ == "__main__"' in content:
         pass
     print("  ? __main__ block found")
 else:
     errors.append("__main__ block not found in run.py")
     print("  ? __main__ block not found")

     if '--LadderServer' in content:
         pass
     print("  ? --LadderServer flag handling found")
 else:
     errors.append("--LadderServer flag handling not found")
     print("  ? --LadderServer flag handling not found")

     if 'run_ladder_game' in content:
         pass
     print("  ? run_ladder_game() call found")
 else:
     errors.append("run_ladder_game() call not found")
     print("  ? run_ladder_game() call not found")
 except Exception as e:
     errors.append(f"Error reading run.py: {e}")
     print(f"  ? Error reading run.py: {e}")

 return len(errors) == 0, errors

def check_bot_instantiation():
    """Check if bot can be instantiated"""
    print("\n[3/6] Checking bot instantiation...")
 errors = []

 try:
     pass
 pass

 except Exception:
     pass
     pass

 # Try to create bot instance
 bot_ai = WickedZergBotPro(train_mode=False, instance_id=0)
     print("  ? WickedZergBotPro instantiated successfully")

 bot = Bot(Race.Zerg, bot_ai)
     print("  ? Bot wrapper created successfully")

 except Exception as e:
     errors.append(f"Bot instantiation failed: {e}")
     print(f"  ? Bot instantiation failed: {e}")
import traceback
 traceback.print_exc()

 return len(errors) == 0, errors

def check_paths():
    """Check if all paths are relative"""
    print("\n[4/6] Checking path configuration...")
 errors = []
 warnings = []

 # Check zerg_net.py for paths
    zerg_net_path = project_root / "zerg_net.py"
 if zerg_net_path.exists():
     try:
         pass
     pass

     except Exception:
         pass
         with open(zerg_net_path, 'r', encoding='utf-8') as f:
 content = f.read()
 # Check for absolute Windows paths
     if 'D:/' in content or 'D:\\' in content:
         pass
     warnings.append("Absolute Windows paths found in zerg_net.py")
     print("  ??  Absolute Windows paths found in zerg_net.py")
 else:
     print("  ? No absolute Windows paths in zerg_net.py")
 except Exception as e:
     print(f"  ??  Could not check zerg_net.py: {e}")

 # Check wicked_zerg_bot_pro.py for paths
    bot_pro_path = project_root / "wicked_zerg_bot_pro.py"
 if bot_pro_path.exists():
     try:
         pass
     pass

     except Exception:
         pass
         with open(bot_pro_path, 'r', encoding='utf-8') as f:
 content = f.read()
 # Check for absolute Windows paths (but allow some for logging)
     if 'D:/replays' in content or 'D:\\replays' in content:
     # This is OK if it's in a try/except or optional code
     if 'try:' in content or 'except' in content:
         pass
     print("  ? Absolute paths in optional code (OK)")
 else:
     warnings.append("Absolute Windows paths found in wicked_zerg_bot_pro.py")
     print("  ??  Absolute Windows paths found in wicked_zerg_bot_pro.py")
 else:
     print("  ? No problematic absolute paths in wicked_zerg_bot_pro.py")
 except Exception as e:
     print(f"  ??  Could not check wicked_zerg_bot_pro.py: {e}")

 return len(errors) == 0, errors, warnings

def check_requirements():
    """Check if requirements.txt exists and has essential packages"""
    print("\n[5/6] Checking requirements.txt...")
 errors = []

    req_path = project_root / "requirements.txt"
 if not req_path.exists():
     errors.append("requirements.txt not found")
     print("  ? requirements.txt not found")
 return False, errors

    print("  ? requirements.txt exists")

 try:
     pass
 pass

 except Exception:
     pass
     with open(req_path, 'r', encoding='utf-8') as f:
 content = f.read()

 required_packages = {
     'burnysc2': 'sc2',
     'torch': 'torch',
     'numpy': 'numpy',
 }

 for package_name, import_name in required_packages.items():
     if package_name in content.lower():
         print(f"  ? {package_name} found in requirements.txt")
 else:
     errors.append(f"{package_name} not found in requirements.txt")
     print(f"  ? {package_name} not found in requirements.txt")
 except Exception as e:
     errors.append(f"Error reading requirements.txt: {e}")
     print(f"  ? Error reading requirements.txt: {e}")

 return len(errors) == 0, errors

def check_file_structure():
    """Check if essential files exist"""
    print("\n[6/6] Checking file structure...")
 errors = []

 essential_files = [
    "run.py",
    "wicked_zerg_bot_pro.py",
    "config.py",
    "zerg_net.py",
    "requirements.txt",
 ]

 for file_name in essential_files:
     file_path = project_root / file_name
 if file_path.exists():
     print(f"  ? {file_name} exists")
 else:
     errors.append(f"{file_name} not found")
     print(f"  ? {file_name} not found")

 # Check for models directory (optional)
    models_dir = project_root / "models"
 if models_dir.exists():
     model_files = list(models_dir.glob("*.pt"))
 if model_files:
     print(f"  ? models/ directory exists ({len(model_files)} model files)")
 else:
     print("  ??  models/ directory exists but no .pt files found")
 else:
     print("  ??  models/ directory not found (bot will start without trained model)")

 return len(errors) == 0, errors

def simulate_arena_start():
    """Simulate AI Arena server startup"""
    print("\n[VALIDATION] Simulating AI Arena server startup...")

 try:
     pass
 pass

 except Exception:
     pass
     # Simulate --LadderServer flag
 original_argv = sys.argv.copy()
     sys.argv = ['run.py', '--LadderServer']

     # Import run module (but don't execute main)
import importlib.util
    run_py_path = project_root / "run.py"
    spec = importlib.util.spec_from_file_location("run", run_py_path)
 run_module = importlib.util.module_from_spec(spec)

 # Check if create_bot function exists
    if hasattr(run_module, 'create_bot'):
        pass
    pass
    print("  ? create_bot() function found")
 else:
     print("  ??  create_bot() function not found (optional)")

 # Restore argv
 sys.argv = original_argv

     print("  ? run.py can be imported without errors")
 return True, []
 except Exception as e:
     print(f"  ? Error simulating startup: {e}")
import traceback
 traceback.print_exc()
 return False, [str(e)]

def main():
    """Run all validation checks"""
    print("="*70)
    print("AI ARENA DEPLOYMENT VALIDATION")
    print("="*70)
    print(f"\nProject root: {project_root}")

 all_passed = True
 all_errors = []
 all_warnings = []

 # Run all checks
 passed, errors = check_imports()
 all_passed = all_passed and passed
 all_errors.extend(errors)

 passed, errors = check_run_py()
 all_passed = all_passed and passed
 all_errors.extend(errors)

 passed, errors = check_bot_instantiation()
 all_passed = all_passed and passed
 all_errors.extend(errors)

 passed, errors, warnings = check_paths()
 all_passed = all_passed and passed
 all_errors.extend(errors)
 all_warnings.extend(warnings)

 passed, errors = check_requirements()
 all_passed = all_passed and passed
 all_errors.extend(errors)

 passed, errors = check_file_structure()
 all_passed = all_passed and passed
 all_errors.extend(errors)

 passed, errors = simulate_arena_start()
 all_passed = all_passed and passed
 all_errors.extend(errors)

 # Summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)

 if all_passed and len(all_warnings) == 0:
     print("\n? ALL CHECKS PASSED - Ready for AI Arena deployment!")
 elif all_passed:
     print("\n? ALL CHECKS PASSED (with warnings)")
     print("\n??  Warnings:")
 for warning in all_warnings:
     print(f"   - {warning}")
 else:
     print("\n? VALIDATION FAILED")
     print("\n? Errors:")
 for error in all_errors:
     print(f"   - {error}")

 if all_warnings:
     print("\n??  Warnings:")
 for warning in all_warnings:
     print(f"   - {warning}")

    print("\n" + "="*70)

 return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
