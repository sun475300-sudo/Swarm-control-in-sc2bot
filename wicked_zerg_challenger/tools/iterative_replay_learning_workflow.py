#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Iterative Replay Learning Workflow

프로게이머 리플레이 학습 → 빌드오더 학습 → 게임 훈련 적용 → 개선 (30회 반복)

전체 워크플로우:
1. 프로게이머 리플레이에서 빌드오더 학습 (30개 리플레이)
2. 학습된 빌드오더를 learned_build_orders.json에 저장
3. 게임 훈련 실행 (학습된 빌드오더 자동 적용)
4. 훈련 데이터 수집 및 비교 분석
5. 개선된 파라미터를 실제 게임에 적용
6. 1-5 단계를 반복하여 점진적 개선
"""

import json
import os
import sys
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Add parent directory to path
script_dir = Path(__file__).parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

PROJECT_ROOT = Path(__file__).parent.parent


class IterativeReplayLearningWorkflow:
    """반복 리플레이 학습 워크플로우"""

    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.replay_learner_path = self.project_root / "local_training" / "scripts" / "replay_build_order_learner.py"
        self.learned_build_orders_path = self.project_root / "local_training" / "scripts" / "learned_build_orders.json"
        self.collect_data_path = self.project_root / "tools" / "collect_training_data.py"
        self.extract_train_path = self.project_root / "tools" / "extract_and_train_from_training.py"
        self.run_training_path = self.project_root / "run_with_training.py"
        
        # 반복 학습 기록
        self.iteration_history: List[Dict[str, Any]] = []
        self.history_path = self.project_root / "local_training" / "scripts" / "iterative_learning_history.json"
    
    def learn_from_replays(self, max_replays: int = 30) -> bool:
        """프로게이머 리플레이에서 빌드오더 학습"""
        if not self.replay_learner_path.exists():
            print(f"[ERROR] Replay learner script not found: {self.replay_learner_path}")
            return False
        
        try:
            env = os.environ.copy()
            env["MAX_REPLAYS_FOR_LEARNING"] = str(max_replays)
            
            print(f"[INFO] Learning from {max_replays} replays...")
            
            result = subprocess.run(
                [sys.executable, str(self.replay_learner_path)],
                cwd=str(self.project_root),
                env=env,
                capture_output=False
            )
            
            if result.returncode == 0:
                if self.learned_build_orders_path.exists():
                    with open(self.learned_build_orders_path, 'r', encoding='utf-8') as f:
                        learned_params = json.load(f)
                    print(f"[SUCCESS] Learned parameters: {learned_params}")
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
    
    def collect_training_data(self) -> bool:
        """게임 훈련 데이터 수집"""
        if not self.collect_data_path.exists():
            print(f"[WARNING] Collect training data script not found")
            return True  # Optional step
        
        try:
            result = subprocess.run(
                [sys.executable, str(self.collect_data_path)],
                cwd=str(self.project_root),
                capture_output=False
            )
            
            return result.returncode == 0
                
        except Exception as e:
            print(f"[WARNING] Failed to collect training data: {e}")
            return True  # Optional step
    
    def extract_and_learn_from_training(self) -> bool:
        """훈련 데이터에서 추출 및 학습"""
        if not self.extract_train_path.exists():
            print(f"[WARNING] Extract and train script not found")
            return True  # Optional step
        
        try:
            result = subprocess.run(
                [sys.executable, str(self.extract_train_path)],
                cwd=str(self.project_root),
                capture_output=False
            )
            
            return result.returncode == 0
                
        except Exception as e:
            print(f"[WARNING] Failed to extract and learn from training: {e}")
            return True  # Optional step
    
    def verify_learned_parameters(self) -> Dict[str, Any]:
        """학습된 파라미터 확인"""
        if not self.learned_build_orders_path.exists():
            return {}
        
        try:
            with open(self.learned_build_orders_path, 'r', encoding='utf-8') as f:
                learned_params = json.load(f)
            return learned_params
        except Exception as e:
            print(f"[WARNING] Failed to load learned parameters: {e}")
            return {}
    
    def save_iteration_history(self):
        """반복 학습 기록 저장"""
        try:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing history
            existing_history = []
            if self.history_path.exists():
                with open(self.history_path, 'r', encoding='utf-8') as f:
                    existing_history = json.load(f)
            
            # Append current iteration history
            existing_history.extend(self.iteration_history)
            
            # Save updated history
            with open(self.history_path, 'w', encoding='utf-8') as f:
                json.dump(existing_history, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            print(f"[WARNING] Failed to save iteration history: {e}")
    
    def run_single_iteration(self, iteration: int, max_replays: int = 30) -> Dict[str, Any]:
        """단일 반복 학습 실행"""
        iteration_start = datetime.now()
        
        print("\n" + "=" * 70)
        print(f"[ITERATION {iteration}] Starting iterative learning cycle")
        print("=" * 70)
        
        iteration_result = {
            "iteration": iteration,
            "start_time": iteration_start.isoformat(),
            "max_replays": max_replays,
            "steps": []
        }
        
        # Step 1: Learn from replays
        print(f"\n[ITERATION {iteration} - STEP 1] Learning from {max_replays} replays...")
        step1_start = time.time()
        if self.learn_from_replays(max_replays=max_replays):
            step1_duration = time.time() - step1_start
            learned_params = self.verify_learned_parameters()
            iteration_result["steps"].append({
                "step": "replay_learning",
                "status": "success",
                "duration": step1_duration,
                "learned_params": learned_params
            })
            print(f"[SUCCESS] Step 1 completed in {step1_duration:.1f}s")
        else:
            step1_duration = time.time() - step1_start
            iteration_result["steps"].append({
                "step": "replay_learning",
                "status": "failed",
                "duration": step1_duration
            })
            print(f"[ERROR] Step 1 failed")
            return iteration_result
        
        # Step 2: Collect training data (if exists)
        print(f"\n[ITERATION {iteration} - STEP 2] Collecting training data...")
        step2_start = time.time()
        self.collect_training_data()
        step2_duration = time.time() - step2_start
        iteration_result["steps"].append({
            "step": "collect_training_data",
            "status": "completed",
            "duration": step2_duration
        })
        print(f"[INFO] Step 2 completed in {step2_duration:.1f}s")
        
        # Step 3: Extract and learn from training
        print(f"\n[ITERATION {iteration} - STEP 3] Extracting and learning from training...")
        step3_start = time.time()
        self.extract_and_learn_from_training()
        step3_duration = time.time() - step3_start
        iteration_result["steps"].append({
            "step": "extract_and_learn",
            "status": "completed",
            "duration": step3_duration
        })
        print(f"[INFO] Step 3 completed in {step3_duration:.1f}s")
        
        # Verify final parameters
        final_params = self.verify_learned_parameters()
        iteration_result["final_params"] = final_params
        
        iteration_end = datetime.now()
        iteration_duration = (iteration_end - iteration_start).total_seconds()
        iteration_result["end_time"] = iteration_end.isoformat()
        iteration_result["duration"] = iteration_duration
        
        print(f"\n[ITERATION {iteration}] Completed in {iteration_duration:.1f}s")
        print(f"[INFO] Final parameters: {final_params}")
        
        return iteration_result
    
    def run_iterative_workflow(self, max_iterations: int = 30, max_replays: int = 30):
        """반복 학습 워크플로우 실행"""
        print("\n" + "=" * 70)
        print("ITERATIVE REPLAY LEARNING WORKFLOW")
        print(f"프로게이머 리플레이 학습 → 빌드오더 학습 → 게임 훈련 적용 → 개선 ({max_iterations}회 반복)")
        print("=" * 70)
        print(f"[INFO] Project root: {self.project_root}")
        print(f"[INFO] Max iterations: {max_iterations}")
        print(f"[INFO] Max replays per iteration: {max_replays}")
        print()
        
        workflow_start = datetime.now()
        
        # Clear iteration history for this run
        self.iteration_history = []
        
        successful_iterations = 0
        failed_iterations = 0
        
        for iteration in range(1, max_iterations + 1):
            try:
                iteration_result = self.run_single_iteration(
                    iteration=iteration,
                    max_replays=max_replays
                )
                
                self.iteration_history.append(iteration_result)
                
                if iteration_result["steps"][0]["status"] == "success":
                    successful_iterations += 1
                else:
                    failed_iterations += 1
                
                # Save history after each iteration (in case of interruption)
                self.save_iteration_history()
                
                # Brief pause between iterations
                if iteration < max_iterations:
                    print(f"\n[INFO] Waiting 2 seconds before next iteration...")
                    time.sleep(2)
                
            except KeyboardInterrupt:
                print(f"\n[WARNING] Workflow interrupted by user at iteration {iteration}")
                break
            except Exception as e:
                print(f"\n[ERROR] Iteration {iteration} failed with exception: {e}")
                import traceback
                traceback.print_exc()
                failed_iterations += 1
        
        # Final summary
        workflow_end = datetime.now()
        workflow_duration = (workflow_end - workflow_start).total_seconds()
        
        # Final parameters
        final_params = self.verify_learned_parameters()
        
        print("\n" + "=" * 70)
        print("[WORKFLOW COMPLETE]")
        print("=" * 70)
        print(f"[INFO] Total iterations: {max_iterations}")
        print(f"[INFO] Successful: {successful_iterations}")
        print(f"[INFO] Failed: {failed_iterations}")
        print(f"[INFO] Total duration: {workflow_duration:.1f} seconds ({workflow_duration/60:.1f} minutes)")
        print()
        print(f"[FINAL PARAMETERS]")
        for param, value in final_params.items():
            print(f"  - {param}: {value}")
        print()
        print(f"[HISTORY] Iteration history saved to: {self.history_path}")
        print()
        print("[NEXT STEPS]")
        print("1. Learned parameters are ready in: local_training/scripts/learned_build_orders.json")
        print("2. These parameters are automatically used in production_resilience.py")
        print("3. Start game training to apply the learned build orders:")
        print("   python run_with_training.py")
        print()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Iterative Replay Learning Workflow (30 iterations)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 30 iterations with 30 replays each (default)
  python iterative_replay_learning_workflow.py
  
  # 50 iterations with 30 replays each
  python iterative_replay_learning_workflow.py --max-iterations 50
  
  # 30 iterations with 50 replays each
  python iterative_replay_learning_workflow.py --max-replays 50
        """
    )
    
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=30,
        help="Maximum number of learning iterations (default: 30)"
    )
    
    parser.add_argument(
        "--max-replays",
        type=int,
        default=30,
        help="Maximum number of replays per iteration (default: 30)"
    )
    
    args = parser.parse_args()
    
    workflow = IterativeReplayLearningWorkflow()
    workflow.run_iterative_workflow(
        max_iterations=args.max_iterations,
        max_replays=args.max_replays
    )


if __name__ == "__main__":
    main()
