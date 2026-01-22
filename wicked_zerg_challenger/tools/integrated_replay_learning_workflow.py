#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integrated Replay Learning Workflow

Pro gamer replay learning -> Build order learning -> Game training application

Full workflow:
1. Extract and learn build orders from pro gamer replays
2. Save learned build orders to learned_build_orders.json
3. Collect game training data (optional)
4. Compare training data with pro replays
5. Apply improved parameters to actual game
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Add parent directory to path
script_dir = Path(__file__).parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

PROJECT_ROOT = Path(__file__).parent.parent


class IntegratedReplayLearningWorkflow:
    """���� ���÷��� �н� ��ũ�÷ο�"""

    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.replay_learner_path = self.project_root / "local_training" / "scripts" / "replay_build_order_learner.py"
        self.learned_build_orders_path = self.project_root / "local_training" / "scripts" / "learned_build_orders.json"
        self.collect_data_path = self.project_root / "tools" / "collect_training_data.py"
        self.extract_train_path = self.project_root / "tools" / "extract_and_train_from_training.py"
        
    def step1_learn_from_replays(self, max_replays: int = 30) -> bool:
        """Step 1: ���ΰ��̸� ���÷��̿��� ������� �н�"""
        print("\n" + "=" * 70)
        print("[STEP 1] Learning Build Orders from Pro Gamer Replays")
        print("=" * 70)
        
        if not self.replay_learner_path.exists():
            print(f"[ERROR] Replay learner script not found: {self.replay_learner_path}")
            return False
        
        try:
            # Set environment variable for max replays
            env = os.environ.copy()
            env["MAX_REPLAYS_FOR_LEARNING"] = str(max_replays)
            
            print(f"[INFO] Learning from up to {max_replays} replays...")
            print(f"[INFO] Replay directory: D:\\replays\\replays")
            print(f"[INFO] Running: {self.replay_learner_path.name}")
            print()
            
            # Run replay learner
            result = subprocess.run(
                [sys.executable, str(self.replay_learner_path)],
                cwd=str(self.project_root),
                env=env,
                capture_output=False
            )
            
            if result.returncode == 0:
                print(f"[SUCCESS] Replay learning completed")
                
                # Verify learned parameters were saved
                if self.learned_build_orders_path.exists():
                    with open(self.learned_build_orders_path, 'r', encoding='utf-8') as f:
                        learned_params = json.load(f)
                    print(f"[INFO] Learned parameters: {learned_params}")
                    return True
                else:
                    print(f"[WARNING] Learned build orders file not created")
                    return False
            else:
                print(f"[ERROR] Replay learning failed with return code {result.returncode}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Failed to learn from replays: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def step2_collect_training_data(self) -> bool:
        """Step 2: ���� �Ʒ� ������ ���� (������)"""
        print("\n" + "=" * 70)
        print("[STEP 2] Collecting Training Game Data")
        print("=" * 70)
        
        if not self.collect_data_path.exists():
            print(f"[WARNING] Collect training data script not found: {self.collect_data_path}")
            print(f"[INFO] Skipping training data collection")
            return True  # Optional step, don't fail
        
        try:
            print(f"[INFO] Running training data collection...")
            print(f"[INFO] This will analyze existing training_stats.json")
            print()
            
            result = subprocess.run(
                [sys.executable, str(self.collect_data_path)],
                cwd=str(self.project_root),
                capture_output=False
            )
            
            if result.returncode == 0:
                print(f"[SUCCESS] Training data collection completed")
                return True
            else:
                print(f"[WARNING] Training data collection had issues (return code {result.returncode})")
                return True  # Optional step, don't fail
                
        except Exception as e:
            print(f"[WARNING] Failed to collect training data: {e}")
            return True  # Optional step, don't fail
    
    def step3_extract_and_learn_from_training(self) -> bool:
        """Step 3: �Ʒ� �����Ϳ��� ���� �� �н�"""
        print("\n" + "=" * 70)
        print("[STEP 3] Extracting and Learning from Training Data")
        print("=" * 70)
        
        if not self.extract_train_path.exists():
            print(f"[WARNING] Extract and train script not found: {self.extract_train_path}")
            print(f"[INFO] Skipping extraction step")
            return True  # Optional step
        
        try:
            print(f"[INFO] Extracting training data and comparing with pro replays...")
            print()
            
            result = subprocess.run(
                [sys.executable, str(self.extract_train_path)],
                cwd=str(self.project_root),
                capture_output=False
            )
            
            if result.returncode == 0:
                print(f"[SUCCESS] Training data extraction and learning completed")
                return True
            else:
                print(f"[WARNING] Extraction step had issues (return code {result.returncode})")
                return True  # Optional step
                
        except Exception as e:
            print(f"[WARNING] Failed to extract and learn from training: {e}")
            return True  # Optional step
    
    def step4_apply_learned_parameters(self) -> bool:
        """Step 4: �н��� �Ķ���� Ȯ�� �� ����"""
        print("\n" + "=" * 70)
        print("[STEP 4] Verifying Learned Parameters")
        print("=" * 70)
        
        if not self.learned_build_orders_path.exists():
            print(f"[ERROR] Learned build orders file not found: {self.learned_build_orders_path}")
            return False
        
        try:
            with open(self.learned_build_orders_path, 'r', encoding='utf-8') as f:
                learned_params = json.load(f)
            
            print(f"[INFO] Current learned parameters:")
            print(f"  - spawning_pool_supply: {learned_params.get('spawning_pool_supply', 'N/A')}")
            print(f"  - gas_supply: {learned_params.get('gas_supply', 'N/A')}")
            print(f"  - natural_expansion_supply: {learned_params.get('natural_expansion_supply', 'N/A')}")
            print()
            
            # Verify parameters are in expected ranges
            pro_baseline = {
                "spawning_pool_supply": 17.0,
                "gas_supply": 17.0,
                "natural_expansion_supply": 30.0
            }
            
            print(f"[INFO] Pro baseline values:")
            for param, value in pro_baseline.items():
                learned_value = learned_params.get(param)
                if learned_value:
                    diff = abs(learned_value - value)
                    status = "?" if diff <= 1.0 else "?"
                    print(f"  {status} {param}: {learned_value} (baseline: {value}, diff: {diff:.1f})")
                else:
                    print(f"  ? {param}: Not found")
            
            print()
            print(f"[SUCCESS] Learned parameters are ready for game training")
            print(f"[INFO] These parameters will be automatically used by:")
            print(f"  - production_resilience.py (via get_learned_parameter())")
            print(f"  - config.py (via get_learned_parameter())")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to verify learned parameters: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_full_workflow(self, max_replays: int = 30, skip_training_data: bool = False):
        """��ü ��ũ�÷ο� ����"""
        print("\n" + "=" * 70)
        print("INTEGRATED REPLAY LEARNING WORKFLOW")
        print("���ΰ��̸� ���÷��� �н� �� ������� �н� �� ���� �Ʒ� ����")
        print("=" * 70)
        print(f"[INFO] Project root: {self.project_root}")
        print(f"[INFO] Max replays: {max_replays}")
        print(f"[INFO] Skip training data collection: {skip_training_data}")
        print()
        
        start_time = datetime.now()
        
        # Step 1: Learn from replays (required)
        if not self.step1_learn_from_replays(max_replays=max_replays):
            print("\n[ERROR] Step 1 failed. Stopping workflow.")
            return False
        
        # Step 2: Collect training data (optional)
        if not skip_training_data:
            self.step2_collect_training_data()
        
        # Step 3: Extract and learn from training (optional)
        if not skip_training_data:
            self.step3_extract_and_learn_from_training()
        
        # Step 4: Verify learned parameters (required)
        if not self.step4_apply_learned_parameters():
            print("\n[ERROR] Step 4 failed. Learned parameters may not be applied correctly.")
            return False
        
        # Workflow complete
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 70)
        print("[WORKFLOW COMPLETE]")
        print("=" * 70)
        print(f"[SUCCESS] Integrated replay learning workflow completed in {duration:.1f} seconds")
        print()
        print("[NEXT STEPS]")
        print("1. Learned parameters are saved to: local_training/scripts/learned_build_orders.json")
        print("2. These parameters are automatically used in production_resilience.py")
        print("3. Start game training to apply the learned build orders:")
        print("   python run_with_training.py")
        print()
        
        return True


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Integrated Replay Learning Workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Learn from 30 replays (default)
  python integrated_replay_learning_workflow.py
  
  # Learn from 50 replays
  python integrated_replay_learning_workflow.py --max-replays 50
  
  # Skip training data collection
  python integrated_replay_learning_workflow.py --skip-training-data
        """
    )
    
    parser.add_argument(
        "--max-replays",
        type=int,
        default=30,
        help="Maximum number of replays to learn from (default: 30)"
    )
    
    parser.add_argument(
        "--skip-training-data",
        action="store_true",
        help="Skip training data collection and comparison steps"
    )
    
    args = parser.parse_args()
    
    workflow = IntegratedReplayLearningWorkflow()
    success = workflow.run_full_workflow(
        max_replays=args.max_replays,
        skip_training_data=args.skip_training_data
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
