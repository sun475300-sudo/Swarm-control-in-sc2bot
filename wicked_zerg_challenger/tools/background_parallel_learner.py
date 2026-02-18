# -*- coding: utf-8 -*-
"""
Background Parallel Learner (Improved)

제대로 된 백그라운드 학습을 수행하는 모듈입니다.
sc2reader를 사용한 부정확한 리플레이 분석 대신,
봇이 직접 저장한 '경험 데이터'를 사용하여 RLAgent를 학습시킵니다.

주요 기능:
1. 경험 데이터 모니터링 (local_training/data/buffer)
2. RLAgent 모델 로드 및 배치 학습
3. 학습된 모델 원자적 저장 (Atomic Save)
4. 처리된 데이터 아카이빙
"""

import os
import shutil
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import sys

# 프로젝트 루트 추가
script_dir = Path(__file__).parent
project_root = script_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from local_training.rl_agent import RLAgent

class BackgroundParallelLearner:
    """
    백그라운드 병렬 학습기 (Offline Experience Replay)
    """

    def __init__(
        self,
        max_workers: int = 1, # 단일 모델 업데이트이므로 1개면 충분
        enable_replay_analysis: bool = False, # 더 이상 사용 안 함
        enable_model_training: bool = True,
        verbose: bool = True,  # 상세 로깅 활성화
        max_file_age: int = 3600  # 최대 파일 나이 (초) - 1시간
    ):
        self.running = False
        self.enable_model_training = enable_model_training
        self.verbose = verbose
        self.max_file_age = max_file_age

        # 경로 설정
        self.data_dir = project_root / "local_training" / "data" / "buffer"
        self.archive_dir = project_root / "local_training" / "data" / "archive"
        self.model_path = project_root / "local_training" / "models" / "rl_agent_model.npz"
        self.log_dir = project_root / "local_training" / "logs"

        # 통계
        self.stats = {
            "files_processed": 0,
            "batches_trained": 0,
            "total_samples": 0,
            "total_processing_time": 0.0,
            "avg_loss": 0.0,
            "errors": 0,
            "active_workers": 0,
            "max_workers": max_workers,
            "last_batch_time": None,
            "last_loss": 0.0,
            "buffer_file_count": 0,
            "archive_file_count": 0,
            "files_skipped_old": 0,  # 너무 오래된 파일로 건너뛴 개수
            "last_adjusted_lr": 0.0  # 마지막 조정된 learning rate
        }

        self.worker_thread: Optional[threading.Thread] = None
        self.rl_agent = None
        self._last_report_time = 0.0

    def _safe_file_op(self, operation: callable, retries: int = 5, delay: float = 0.5) -> Any:
        """파일 작업 재시도 래퍼"""
        msg = ""
        for i in range(retries):
            try:
                return operation()
            except PermissionError:
                if i < retries - 1:
                    time.sleep(delay)
                else:
                    raise
            except OSError as e:
                # WinError 32: The process cannot access the file because it is being used by another process
                if getattr(e, 'winerror', 0) == 32:
                    if i < retries - 1:
                        time.sleep(delay)
                    else:
                        raise
                else:
                    raise
            except Exception as e:
                raise e
        return None

    def start(self) -> bool:
        """백그라운드 학습 시작"""
        if self.running:
            return False

        try:
            self.running = True
            
            # 디렉토리 생성
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.archive_dir.mkdir(parents=True, exist_ok=True)
            
            # RLAgent 초기화 (모델 로드)
            self.rl_agent = RLAgent(model_path=str(self.model_path))
            
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            
            print(f"[BG_LEARNER] Started (Monitoring {self.data_dir})")
            return True

        except Exception as e:
            print(f"[BG_LEARNER] Failed to start: {e}")
            self.running = False
            return False

    def stop(self) -> None:
        """백그라운드 학습 중지"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
        print("[BG_LEARNER] Stopped")

    def _worker_loop(self) -> None:
        """워커 루프"""
        if self.verbose:
            print("[BG_LEARNER] Worker thread started")

        while self.running:
            try:
                # 버퍼 상태 업데이트
                self._update_directory_stats()

                # 주기적 보고 (30초마다)
                current_time = time.time()
                if current_time - self._last_report_time > 30:
                    self._print_status_report()
                    self._last_report_time = current_time

                # 5초마다 파일 확인
                processed = self._process_new_data()

                if not processed:
                    time.sleep(5)

            except Exception as e:
                print(f"[BG_LEARNER] [ERROR] Worker error: {e}")
                self.stats["errors"] += 1
                time.sleep(5)

        if self.verbose:
            print("[BG_LEARNER] Worker thread stopped")

    def _process_new_data(self) -> bool:
        """새로운 경험 데이터 처리"""
        if not self.enable_model_training:
            return False

        # .npz 파일 찾기
        files = list(self.data_dir.glob("*.npz"))
        if not files:
            return False

        self.stats["active_workers"] = 1
        start_time = time.time()
        current_time = time.time()

        try:
            # 배치 로드
            experiences = []
            files_to_archive = []
            files_skipped = 0

            if self.verbose:
                print(f"\n[BG_LEARNER] > Processing batch: {len(files)} files available")

            for file_path in files[:10]:  # 한 번에 최대 10개 처리
                try:
                    # 파일 나이 체크 (Off-Policy 문제 완화)
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > self.max_file_age:
                        if self.verbose:
                            print(f"  [-] Skipped (too old): {file_path.name} (Age: {file_age/60:.1f} min)")
                        files_skipped += 1
                        # ★ FIX: 오래된 파일 아카이브 보존 (삭제하지 않음, 초기 학습 데이터 유지)
                        try:
                            archive_path = self.archive_dir / f"old_{file_path.name}"
                            import shutil
                            shutil.copy2(str(file_path), str(archive_path))
                        except Exception:
                            pass
                        continue

                    # ★ FIX: Use context manager to ensure file is closed ★
                    loaded_data = {}
                    with np.load(str(file_path)) as data:
                        loaded_data["states"] = np.copy(data['states'])
                        loaded_data["actions"] = np.copy(data['actions'])
                        loaded_data["rewards"] = np.copy(data['rewards'])
                    
                    # ★ FIX: NaN/Inf 검증 (오염 데이터 학습 방지)
                    if (np.any(np.isnan(loaded_data["states"])) or np.any(np.isinf(loaded_data["states"]))
                            or np.any(np.isnan(loaded_data["rewards"])) or np.any(np.isinf(loaded_data["rewards"]))):
                        print(f"[BG_LEARNER] [WARN] Corrupted data (NaN/Inf): {file_path.name} - skipped")
                        continue
                    # 액션 인덱스 범위 검증 (0-4)
                    if np.any(loaded_data["actions"] < 0) or np.any(loaded_data["actions"] > 4):
                        print(f"[BG_LEARNER] [WARN] Invalid action indices in {file_path.name} - skipped")
                        continue

                    experiences.append(loaded_data)
                    files_to_archive.append(file_path)
                    
                    if self.verbose:
                        total_reward = np.sum(loaded_data['rewards'])
                        print(f"  [OK] Loaded: {file_path.name} (Steps: {len(loaded_data['states'])}, Reward: {total_reward:.2f})")
                except Exception as e:
                    print(f"[BG_LEARNER] [ERROR] Corrupt file {file_path.name}: {e}")
                    # 손상된 파일은 별도 이동 또는 삭제
                    try:
                        file_path.rename(file_path.with_suffix(".corrupt"))
                    except Exception:
                        pass

            # 건너뛴 파일 통계 업데이트
            self.stats["files_skipped_old"] += files_skipped

            if not experiences:
                return False

            # 학습 수행
            if self.verbose:
                total_steps = sum(len(exp['states']) for exp in experiences)
                print(f"[BG_LEARNER] ~ Training on {len(experiences)} games ({total_steps} total steps)...")

            # RLAgent 리로드 (최신 모델 반영)
            self.rl_agent = RLAgent(model_path=str(self.model_path))

            train_stats = self.rl_agent.train_from_batch(experiences)

            # 모델 저장
            saved = self.rl_agent.save_model()

            if saved:
                # 처리된 파일 아카이브로 이동
                archived_count = 0
                for file_path in files_to_archive:
                    try:
                        archive_path = self.archive_dir / file_path.name
                        self._safe_file_op(lambda: shutil.move(str(file_path), str(archive_path)))
                        archived_count += 1
                    except Exception as e:
                        print(f"[BG_LEARNER] [ERROR] Archive error: {e}")

                # 통계 업데이트
                self.stats["files_processed"] += archived_count
                self.stats["batches_trained"] += 1
                self.stats["total_samples"] += train_stats.get("steps", 0)
                self.stats["avg_loss"] = train_stats.get("loss", 0.0)
                self.stats["last_loss"] = train_stats.get("loss", 0.0)
                self.stats["last_adjusted_lr"] = train_stats.get("adjusted_lr", 0.0)
                self.stats["last_batch_time"] = time.time()

                processing_time = time.time() - start_time
                if self.verbose:
                    print(f"[BG_LEARNER] [OK] Training complete!")
                    print(f"  - Loss: {train_stats.get('loss', 0):.4f}")
                    print(f"  - Games trained: {train_stats.get('games', 0)}")
                    print(f"  - Adjusted LR: {train_stats.get('adjusted_lr', 0):.6f}")
                    print(f"  - Files archived: {archived_count}")
                    print(f"  - Processing time: {processing_time:.2f}s")

                # 로그 파일에 기록
                self._log_training_result(len(experiences), train_stats, processing_time)

                return True
            else:
                print("[BG_LEARNER] [ERROR] Failed to save model, skipping archive")
                return False

        except Exception as e:
            print(f"[BG_LEARNER] [ERROR] Processing error: {e}")
            import traceback
            traceback.print_exc()
            self.stats["errors"] += 1
            return False
        finally:
            self.stats["total_processing_time"] += time.time() - start_time
            self.stats["active_workers"] = 0

    def get_stats(self) -> Dict[str, Any]:
        """통계 반환"""
        return self.stats.copy()

    def _update_directory_stats(self) -> None:
        """디렉토리 상태 업데이트"""
        try:
            buffer_files = list(self.data_dir.glob("*.npz"))
            archive_files = list(self.archive_dir.glob("*.npz"))
            self.stats["buffer_file_count"] = len(buffer_files)
            self.stats["archive_file_count"] = len(archive_files)
        except Exception:
            pass

    def _print_status_report(self) -> None:
        """주기적 상태 보고"""
        if not self.verbose:
            return

        print("\n" + "="*70)
        print("? [BACKGROUND LEARNER] STATUS REPORT")
        print("="*70)
        print(f"? Training Statistics:")
        print(f"  Files Processed:      {self.stats['files_processed']}")
        print(f"  Files Skipped (Old):  {self.stats['files_skipped_old']}")
        print(f"  Batch Training Runs:  {self.stats['batches_trained']}")
        print(f"  Total Samples:        {self.stats['total_samples']}")
        print(f"  Average Loss:         {self.stats['avg_loss']:.4f}")
        print(f"  Last Loss:            {self.stats['last_loss']:.4f}")
        print(f"  Last Adjusted LR:     {self.stats['last_adjusted_lr']:.6f}")
        print()
        print(f"? Directory Status:")
        print(f"  Buffer Files:         {self.stats['buffer_file_count']}")
        print(f"  Archived Files:       {self.stats['archive_file_count']}")
        print(f"  Max File Age:         {self.max_file_age/60:.1f} min")
        print()
        print(f"? System Status:")
        print(f"  Active Workers:       {self.stats['active_workers']}/{self.stats['max_workers']}")
        print(f"  Total Process Time:   {self.stats['total_processing_time']:.2f}s")
        print(f"  Errors:               {self.stats['errors']}")

        if self.stats['last_batch_time']:
            import datetime
            last_time = datetime.datetime.fromtimestamp(self.stats['last_batch_time'])
            print(f"  Last Training:        {last_time.strftime('%Y-%m-%d %H:%M:%S')}")

        print("="*70 + "\n")

    def _log_training_result(self, batch_size: int, train_stats: Dict, processing_time: float) -> None:
        """학습 결과를 로그 파일에 기록"""
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            log_file = self.log_dir / "background_training.log"

            import datetime
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n[{timestamp}] Batch Training Complete\n")
                f.write(f"  Batch Size:      {batch_size} games\n")
                f.write(f"  Total Steps:     {train_stats.get('steps', 0)}\n")
                f.write(f"  Loss:            {train_stats.get('loss', 0):.4f}\n")
                f.write(f"  Adjusted LR:     {train_stats.get('adjusted_lr', 0):.6f}\n")
                f.write(f"  Processing Time: {processing_time:.2f}s\n")
                f.write(f"  Total Processed: {self.stats['files_processed']} files\n")
                f.write(f"  Total Skipped:   {self.stats['files_skipped_old']} files (too old)\n")
                f.write(f"  Total Batches:   {self.stats['batches_trained']}\n")
                f.write("-" * 60 + "\n")
        except Exception as e:
            if self.verbose:
                print(f"[BG_LEARNER] Warning: Could not write log: {e}")

# 싱글톤 및 헬퍼
_instance: Optional[BackgroundParallelLearner] = None

def get_background_learner(**kwargs) -> BackgroundParallelLearner:
    """
    싱글톤 BackgroundParallelLearner 인스턴스 반환

    Args:
        max_workers: 워커 스레드 수 (기본값: 1)
        enable_replay_analysis: sc2reader 리플레이 분석 (기본값: False, 사용 안 함)
        enable_model_training: 경험 데이터 기반 학습 (기본값: True)
        verbose: 상세 로깅 활성화 (기본값: True)
    """
    global _instance
    if _instance is None:
        _instance = BackgroundParallelLearner(**kwargs)
    return _instance

def main():
    print("Testing Background Learner...")
    learner = BackgroundParallelLearner()
    learner.start()
    time.sleep(5)
    learner.stop()

if __name__ == "__main__":
    main()
