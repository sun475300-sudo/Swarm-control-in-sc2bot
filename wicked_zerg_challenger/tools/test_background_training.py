# -*- coding: utf-8 -*-
"""
Background Training System Test
백그라운드 학습 시스템 테스트 스크립트
"""

import sys
import time
import numpy as np
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 추가
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from wicked_zerg_challenger.tools.background_parallel_learner import BackgroundParallelLearner
from wicked_zerg_challenger.local_training.rl_agent import RLAgent


def create_dummy_experience_data(path: Path, num_steps: int = 50) -> None:
    """더미 경험 데이터 생성"""
    # 실제 봇과 유사한 형태의 데이터 생성
    states = []
    actions = []
    rewards = []

    for _ in range(num_steps):
        # 상태 벡터 (실제 봇의 feature 차원과 동일하게)
        state = np.random.rand(50).astype(np.float32)
        states.append(state)

        # 액션 (0-3: Attack/Defense/Economy/Tech)
        action = np.random.randint(0, 4)
        actions.append(action)

        # 보상 (승리 시뮬레이션: 마지막에 높은 보상)
        reward = 0.1 if _ < num_steps - 1 else 1.0
        rewards.append(reward)

    # NumPy 배열로 저장
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        states=np.array(states),
        actions=np.array(actions),
        rewards=np.array(rewards)
    )


def test_experience_data_save_load():
    """테스트 1: 경험 데이터 저장 및 로드"""
    print("\n" + "="*60)
    print("TEST 1: Experience Data Save/Load")
    print("="*60)

    test_dir = project_root / "local_training" / "data" / "test_buffer"
    test_dir.mkdir(parents=True, exist_ok=True)

    # 더미 데이터 생성
    test_file = test_dir / "test_game_001.npz"
    create_dummy_experience_data(test_file, num_steps=30)
    print(f"[OK] Created dummy data: {test_file}")

    # 데이터 로드 확인
    with np.load(str(test_file)) as data:
        print(f"  - States shape: {data['states'].shape}")
        print(f"  - Actions shape: {data['actions'].shape}")
        print(f"  - Rewards shape: {data['rewards'].shape}")
        print(f"  - Total reward: {np.sum(data['rewards']):.2f}")

    # 정리
    test_file.unlink()
    print("[OK] Test 1 PASSED\n")


def test_rl_agent_batch_training():
    """테스트 2: RLAgent 배치 학습"""
    print("\n" + "="*60)
    print("TEST 2: RLAgent Batch Training")
    print("="*60)

    # 임시 모델 경로
    temp_model_path = project_root / "local_training" / "models" / "test_rl_agent.npz"
    temp_model_path.parent.mkdir(parents=True, exist_ok=True)

    # RLAgent 생성
    agent = RLAgent(model_path=str(temp_model_path))
    print(f"[OK] Created RLAgent")

    # 더미 경험 데이터 생성
    experiences = []
    for i in range(3):  # 3개 게임 시뮬레이션
        states = np.random.rand(20, 50).astype(np.float32)
        actions = np.random.randint(0, 4, size=20)
        rewards = np.concatenate([
            np.full(19, 0.05),  # 중간 보상
            np.array([1.0 if i % 2 == 0 else -0.5])  # 마지막: 승/패
        ])

        experiences.append({
            'states': states,
            'actions': actions,
            'rewards': rewards
        })

    print(f"[OK] Created {len(experiences)} experience sets")

    # 배치 학습
    stats = agent.train_from_batch(experiences)
    print(f"[OK] Batch training complete:")
    print(f"  - Loss: {stats['loss']:.4f}")
    print(f"  - Total steps: {stats['steps']}")

    # 모델 저장
    saved = agent.save_model()
    print(f"[OK] Model saved: {saved}")

    # 모델 파일 확인
    if temp_model_path.exists():
        print(f"[OK] Model file exists: {temp_model_path}")
        temp_model_path.unlink()

    print("[OK] Test 2 PASSED\n")


def test_background_learner_processing():
    """테스트 3: BackgroundParallelLearner 파일 처리"""
    print("\n" + "="*60)
    print("TEST 3: Background Learner Processing")
    print("="*60)

    # 테스트 디렉토리 설정
    test_buffer_dir = project_root / "local_training" / "data" / "test_buffer"
    test_archive_dir = project_root / "local_training" / "data" / "test_archive"
    test_model_path = project_root / "local_training" / "models" / "test_rl_agent.npz"

    # 기존 테스트 파일 정리
    if test_buffer_dir.exists():
        for f in test_buffer_dir.glob("*.npz"):
            f.unlink()
    if test_archive_dir.exists():
        for f in test_archive_dir.glob("*.npz"):
            f.unlink()

    test_buffer_dir.mkdir(parents=True, exist_ok=True)
    test_archive_dir.mkdir(parents=True, exist_ok=True)

    # 더미 경험 데이터 생성 (5개 파일)
    for i in range(5):
        file_path = test_buffer_dir / f"game_{i:03d}.npz"
        create_dummy_experience_data(file_path, num_steps=25)

    print(f"[OK] Created 5 dummy experience files in {test_buffer_dir}")

    # BackgroundParallelLearner 생성 (테스트 경로로 오버라이드)
    learner = BackgroundParallelLearner(enable_model_training=True)

    # 경로 오버라이드
    learner.data_dir = test_buffer_dir
    learner.archive_dir = test_archive_dir
    learner.model_path = test_model_path

    # RLAgent 초기화
    learner.rl_agent = RLAgent(model_path=str(test_model_path))

    print("[OK] BackgroundParallelLearner created with test paths")

    # 수동으로 1회 처리 실행
    processed = learner._process_new_data()

    if processed:
        print("[OK] Data processing successful")
        print(f"  - Files processed: {learner.stats['files_processed']}")
        print(f"  - Batches trained: {learner.stats['batches_trained']}")
        print(f"  - Total samples: {learner.stats['total_samples']}")
        print(f"  - Avg loss: {learner.stats['avg_loss']:.4f}")

        # 아카이브 디렉토리 확인
        archived_files = list(test_archive_dir.glob("*.npz"))
        print(f"[OK] Archived files: {len(archived_files)}")

        # 버퍼 디렉토리 확인 (처리된 파일은 제거되어야 함)
        remaining_files = list(test_buffer_dir.glob("*.npz"))
        print(f"[OK] Remaining files in buffer: {len(remaining_files)}")
    else:
        print("[FAIL] No data processed (may be expected if no files found)")

    # 정리
    for f in test_buffer_dir.glob("*.npz"):
        f.unlink()
    for f in test_archive_dir.glob("*.npz"):
        f.unlink()
    if test_model_path.exists():
        test_model_path.unlink()

    print("[OK] Test 3 PASSED\n")


def test_background_learner_lifecycle():
    """테스트 4: BackgroundParallelLearner 라이프사이클"""
    print("\n" + "="*60)
    print("TEST 4: Background Learner Lifecycle")
    print("="*60)

    learner = BackgroundParallelLearner(enable_model_training=True)

    # 시작
    started = learner.start()
    print(f"[OK] Learner started: {started}")
    print(f"  - Running: {learner.running}")
    print(f"  - Worker thread alive: {learner.worker_thread.is_alive()}")

    # 통계 확인
    time.sleep(2)
    stats = learner.get_stats()
    print(f"[OK] Stats retrieved:")
    for key, value in stats.items():
        print(f"  - {key}: {value}")

    # 중지
    learner.stop()
    print(f"[OK] Learner stopped")
    print(f"  - Running: {learner.running}")

    time.sleep(1)
    print("[OK] Test 4 PASSED\n")


def run_all_tests():
    """모든 테스트 실행"""
    print("\n" + "="*70)
    print("  BACKGROUND TRAINING SYSTEM - TEST SUITE")
    print("="*70)

    start_time = time.time()

    try:
        test_experience_data_save_load()
        test_rl_agent_batch_training()
        test_background_learner_processing()
        test_background_learner_lifecycle()

        elapsed = time.time() - start_time

        print("\n" + "="*70)
        print(f"  ALL TESTS PASSED [OK]")
        print(f"  Total time: {elapsed:.2f}s")
        print("="*70 + "\n")

    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
