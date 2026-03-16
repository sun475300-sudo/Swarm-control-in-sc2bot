#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run Training Pipeline - 독립 실행 훈련 스크립트

사용법:
    python run_training_pipeline.py --cycles 10 --games-per-cycle 5
    python run_training_pipeline.py --summary

사이클 동작:
    1. experience buffer에서 .npz 파일 수집
    2. RLAgent.train_from_batch() 로 학습
    3. 체크포인트 생성 (버전 관리)
    4. 기존 운영 모델 대비 개선 시 자동 배포
    5. 처리 완료 experience 아카이브
"""

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np

# 프로젝트 루트 경로 설정
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent  # wicked_zerg_challenger/local_training
BOT_ROOT = PROJECT_ROOT.parent    # wicked_zerg_challenger/

sys.path.insert(0, str(BOT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))


def load_experience_files(file_paths):
    """경험 파일 로드"""
    experiences = []
    for fpath in file_paths:
        try:
            data = np.load(str(fpath), allow_pickle=False)
            exp = {
                "states": data["states"],
                "actions": data["actions"],
                "rewards": data["rewards"],
            }
            if len(exp["states"]) > 0:
                experiences.append(exp)
                print(f"  Loaded: {fpath.name} ({len(exp['states'])} steps)")
        except Exception as e:
            print(f"  Skip (corrupted): {fpath.name} - {e}")
    return experiences


def run_training_cycle(pipeline, rl_agent, cycle_num):
    """단일 훈련 사이클 실행"""
    print(f"\n{'='*60}")
    print(f"  CYCLE {cycle_num}")
    print(f"{'='*60}")

    # 1. Experience 수집
    exp_files = pipeline.collect_experience_files()
    if not exp_files:
        print("  No experience files in buffer. Skipping cycle.")
        return None

    print(f"  Found {len(exp_files)} experience files")

    # 2. 경험 로드
    experiences = load_experience_files(exp_files)
    if not experiences:
        print("  No valid experience data. Skipping cycle.")
        return None

    total_steps = sum(len(e["states"]) for e in experiences)
    print(f"  Total training data: {len(experiences)} games, {total_steps} steps")

    # 3. 학습
    print("  Training...")
    train_stats = rl_agent.train_from_batch(experiences)
    print(
        f"  Loss: {train_stats['loss']:.4f}, "
        f"Steps: {train_stats['steps']}, "
        f"LR: {train_stats.get('adjusted_lr', 0):.6f}"
    )

    # 4. 메트릭 계산 (경험 기반 추정)
    avg_reward = float(
        np.mean([np.sum(e["rewards"]) for e in experiences])
    )
    # Win rate 추정: 최종 reward > 0 이면 승리로 간주
    wins = sum(1 for e in experiences if np.sum(e["rewards"]) > 0)
    win_rate = wins / len(experiences) if experiences else 0.0

    metrics = {
        "win_rate": win_rate,
        "avg_reward": avg_reward,
        "games": len(experiences),
        "total_steps": total_steps,
        "loss": train_stats["loss"],
    }

    # 5. 체크포인트 생성
    version = pipeline.create_checkpoint(rl_agent, metrics)

    # 6. 자동 배포 판단
    deployed = pipeline.deploy_if_better(version)

    # 7. 처리 완료 experience 아카이브
    pipeline.archive_processed_experience(exp_files)
    print(f"  Archived {len(exp_files)} experience files")

    return {
        "cycle": cycle_num,
        "version": version.version_id,
        "metrics": metrics,
        "deployed": deployed,
    }


def main():
    parser = argparse.ArgumentParser(description="SC2 Bot Training Pipeline")
    parser.add_argument(
        "--cycles", type=int, default=1,
        help="Number of training cycles (default: 1)"
    )
    parser.add_argument(
        "--learning-rate", type=float, default=0.001,
        help="Learning rate (default: 0.001)"
    )
    parser.add_argument(
        "--model-path", type=str, default=None,
        help="Base model path to start from"
    )
    parser.add_argument(
        "--summary", action="store_true",
        help="Show training summary and exit"
    )
    parser.add_argument(
        "--buffer-dir", type=str, default=None,
        help="Override experience buffer directory"
    )
    args = parser.parse_args()

    # Pipeline & Agent 초기화
    from training_pipeline import TrainingPipeline
    from rl_agent import RLAgent

    pipeline = TrainingPipeline()

    # buffer_dir 오버라이드
    if args.buffer_dir:
        pipeline.buffer_dir = Path(args.buffer_dir)

    # Summary 모드
    if args.summary:
        summary = pipeline.get_training_summary()
        print("\n=== Training Pipeline Summary ===")
        for k, v in summary.items():
            print(f"  {k}: {v}")
        return

    # RLAgent 초기화
    model_path = args.model_path
    if model_path is None:
        # 배포된 모델이 있으면 그걸로 시작
        if pipeline.deployed_model_path.exists():
            model_path = str(pipeline.deployed_model_path)
            print(f"Starting from deployed model: {model_path}")
        else:
            # 기본 모델 경로
            default_model = PROJECT_ROOT / "models" / "rl_agent_model.npz"
            if default_model.exists():
                model_path = str(default_model)
                print(f"Starting from default model: {model_path}")

    rl_agent = RLAgent(
        learning_rate=args.learning_rate,
        model_path=model_path,
    )

    print(f"\n{'='*60}")
    print(f"  SC2 Bot Training Pipeline")
    print(f"  Cycles: {args.cycles}")
    print(f"  Learning Rate: {args.learning_rate}")
    print(f"  Buffer: {pipeline.buffer_dir}")
    print(f"{'='*60}")

    # 훈련 사이클 실행
    results = []
    for cycle in range(1, args.cycles + 1):
        result = run_training_cycle(pipeline, rl_agent, cycle)
        if result:
            results.append(result)

        # 사이클 간 짧은 대기 (파일 시스템 동기화)
        if cycle < args.cycles:
            time.sleep(1)

    # 최종 요약
    print(f"\n{'='*60}")
    print(f"  TRAINING COMPLETE")
    print(f"{'='*60}")
    print(f"  Cycles completed: {len(results)}/{args.cycles}")

    if results:
        deployed_versions = [r for r in results if r["deployed"]]
        print(f"  Models deployed: {len(deployed_versions)}")
        best_wr = max(r["metrics"]["win_rate"] for r in results)
        print(f"  Best win rate: {best_wr:.1%}")

    summary = pipeline.get_training_summary()
    print(f"\n  Pipeline Status:")
    for k, v in summary.items():
        print(f"    {k}: {v}")

    # 최종 모델 저장
    rl_agent.save_model()
    print(f"\n  Final model saved to: {rl_agent.model_path}")


if __name__ == "__main__":
    main()
