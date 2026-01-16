#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apply Optimized Parameters to Training

다음 게임 훈련에서 최적화된 학습 데이터를 적용하는 스크립트입니다.
- 최적화된 파라미터 확인
- config.py에 반영 확인
- 게임 훈련에서 사용할 준비 완료
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path
script_dir = Path(__file__).parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

PROJECT_ROOT = script_dir


def load_optimized_parameters() -> Dict[str, float]:
    """Load optimized parameters from learned_build_orders.json"""
    learned_path = PROJECT_ROOT / "local_training" / \
        "scripts" / "learned_build_orders.json"

    if not learned_path.exists():
        print(f"[ERROR] Optimized parameters not found: {learned_path}")
        return {}

    try:
        with open(learned_path, 'r', encoding='utf-8') as f:
            params = json.load(f)

        # Ensure all values are floats
        return {k: float(v) for k, v in params.items()}
    except Exception as e:
        print(f"[ERROR] Failed to load optimized parameters: {e}")
        return {}


def verify_config_integration() -> bool:
    """Verify that config.py can load the optimized parameters"""
    try:
        from config import get_learned_parameter

        # Test loading a few parameters
        test_params = [
            "gas_supply",
            "spawning_pool_supply",
            "natural_expansion_supply",
            "lair_supply"
        ]

        loaded_count = 0
        for param_name in test_params:
            value = get_learned_parameter(param_name)
            if value is not None:
                loaded_count += 1

        if loaded_count == 0:
            print(
                "[WARNING] config.get_learned_parameter() could not load any parameters")
            return False

        print(
            f"[SUCCESS] config.get_learned_parameter() can load {loaded_count}/{len(test_params)} test parameters")
        return True
    except Exception as e:
        print(f"[WARNING] Failed to verify config integration: {e}")
        return False


def verify_production_manager_usage() -> bool:
    """Verify that production_manager.py uses get_learned_parameter"""
    production_manager_path = PROJECT_ROOT / "production_manager.py"

    if not production_manager_path.exists():
        print(f"[WARNING] production_manager.py not found")
        return False

    try:
        with open(production_manager_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if 'get_learned_parameter' in content:
            print("[SUCCESS] production_manager.py uses get_learned_parameter()")
            return True
        else:
            print("[WARNING] production_manager.py may not use get_learned_parameter()")
            return False
    except Exception as e:
        print(f"[WARNING] Failed to check production_manager.py: {e}")
        return False


def apply_to_config(optimized_params: Dict[str, float]) -> bool:
    """Apply optimized parameters to config.py"""
    try:
        from local_training.scripts.replay_build_order_learner import update_config_with_learned_params
        update_config_with_learned_params(optimized_params)
        print("[SUCCESS] Config updated with optimized parameters")
        return True
    except Exception as e:
        print(f"[WARNING] Failed to update config: {e}")
        # Not critical - get_learned_parameter will load from JSON
        return False


def main():
    """Main function"""
    print("\n" + "=" * 70)
    print("APPLY OPTIMIZED PARAMETERS TO TRAINING")
    print("=" * 70)
    print()

    # Step 1: Load optimized parameters
    print("[STEP 1] Loading optimized parameters...")
    optimized_params = load_optimized_parameters()

    if not optimized_params:
        print("[ERROR] No optimized parameters found")
        print("[INFO] Please run optimize_learning_data.py first")
        return False

    print(f"[SUCCESS] Loaded {len(optimized_params)} optimized parameters:")
    for param_name, value in sorted(optimized_params.items()):
        print(f"  {param_name}: {value}")

    # Step 2: Apply to config
    print("\n[STEP 2] Applying to config...")
    apply_to_config(optimized_params)

    # Step 3: Verify config integration
    print("\n[STEP 3] Verifying config integration...")
    config_ok = verify_config_integration()

    # Step 4: Verify production_manager usage
    print("\n[STEP 4] Verifying production_manager integration...")
    production_ok = verify_production_manager_usage()

    # Summary
    print("\n" + "=" * 70)
    print("APPLICATION COMPLETE")
    print("=" * 70)
    print(f"\nStatus:")
    print(f"  - Optimized parameters loaded: {len(optimized_params)}")
    print(f"  - Config integration: {'OK' if config_ok else 'WARNING'}")
    print(
        f"  - Production manager integration: {'OK' if production_ok else 'WARNING'}")
    print(f"\nNext steps:")
    print(f"  1. Start game training: bat\\start_local_training.bat")
    print(f"  2. Or run: python run_with_training.py")
    print(f"  3. Training will automatically use optimized parameters")
    print("=" * 70)

    return config_ok


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
