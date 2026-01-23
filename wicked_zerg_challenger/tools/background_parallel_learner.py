# -*- coding: utf-8 -*-
"""
Background Parallel Learner

백그라운드에서 병렬로 학습을 수행하는 모듈입니다.

주요 기능:
1. 멀티스레드 워커로 리플레이 분석
2. 비동기 모델 훈련
3. 게임 중에도 학습 지속
4. 리소스 효율적 관리
"""

import json
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import sys

# 프로젝트 루트 추가
script_dir = Path(__file__).parent
project_root = script_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class BackgroundParallelLearner:
    """
    백그라운드 병렬 학습기

    게임이 실행되는 동안 별도 스레드에서 학습을 수행합니다.
    """

    def __init__(
        self,
        max_workers: int = 2,
        enable_replay_analysis: bool = True,
        enable_model_training: bool = True
    ):
        """
        Args:
            max_workers: 최대 워커 수
            enable_replay_analysis: 리플레이 분석 활성화
            enable_model_training: 모델 훈련 활성화
        """
        self.max_workers = max_workers
        self.enable_replay_analysis = enable_replay_analysis
        self.enable_model_training = enable_model_training

        # 스레드 풀
        self.executor: Optional[ThreadPoolExecutor] = None
        self.running = False

        # 작업 큐
        self.task_queue: queue.Queue = queue.Queue()
        self.result_queue: queue.Queue = queue.Queue()

        # 통계
        self.stats = {
            "replays_analyzed": 0,
            "models_trained": 0,
            "total_processing_time": 0.0,
            "errors": 0,
            "active_workers": 0,
            "max_workers": max_workers,
            "started_at": None,
            "last_activity": None
        }

        # 경로 설정
        self.replay_dir = project_root / "replays"
        self.model_dir = project_root / "local_training" / "models"
        self.output_dir = project_root / "local_training" / "background_results"

        # 워커 스레드
        self.worker_thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        """백그라운드 학습 시작"""
        if self.running:
            print("[BG_LEARNER] Already running")
            return False

        try:
            self.running = True
            self.stats["started_at"] = datetime.now().isoformat()

            # 출력 디렉토리 생성
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # 스레드 풀 생성
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers)

            # 워커 스레드 시작
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()

            print(f"[BG_LEARNER] Started with {self.max_workers} workers")
            return True

        except Exception as e:
            print(f"[BG_LEARNER] Failed to start: {e}")
            self.running = False
            return False

    def stop(self) -> None:
        """백그라운드 학습 중지"""
        self.running = False

        if self.executor:
            self.executor.shutdown(wait=False)
            self.executor = None

        print("[BG_LEARNER] Stopped")

    def _worker_loop(self) -> None:
        """워커 루프"""
        while self.running:
            try:
                # 작업 큐에서 태스크 가져오기
                try:
                    task = self.task_queue.get(timeout=1.0)
                except queue.Empty:
                    # 큐가 비어있으면 자동 태스크 실행
                    self._run_auto_tasks()
                    continue

                # 태스크 실행
                self._execute_task(task)

            except Exception as e:
                print(f"[BG_LEARNER] Worker error: {e}")
                self.stats["errors"] += 1
                time.sleep(1)

    def _run_auto_tasks(self) -> None:
        """자동 태스크 실행"""
        current_time = time.time()

        # 30초마다 리플레이 분석
        if self.enable_replay_analysis:
            if not hasattr(self, '_last_replay_check'):
                self._last_replay_check = 0

            if current_time - self._last_replay_check > 30:
                self._last_replay_check = current_time
                self._analyze_new_replays()

        # 60초마다 모델 훈련
        if self.enable_model_training:
            if not hasattr(self, '_last_train_check'):
                self._last_train_check = 0

            if current_time - self._last_train_check > 60:
                self._last_train_check = current_time
                self._train_model_batch()

    def _execute_task(self, task: Dict[str, Any]) -> None:
        """태스크 실행"""
        task_type = task.get("type", "")
        start_time = time.time()

        try:
            self.stats["active_workers"] += 1

            if task_type == "analyze_replay":
                result = self._do_analyze_replay(task.get("path"))
            elif task_type == "train_model":
                result = self._do_train_model(task.get("data"))
            elif task_type == "custom":
                func = task.get("func")
                args = task.get("args", [])
                result = func(*args) if func else None
            else:
                result = None

            # 결과 저장
            self.result_queue.put({
                "task": task,
                "result": result,
                "success": True,
                "duration": time.time() - start_time
            })

            self.stats["total_processing_time"] += time.time() - start_time
            self.stats["last_activity"] = datetime.now().isoformat()

        except Exception as e:
            self.stats["errors"] += 1
            self.result_queue.put({
                "task": task,
                "result": None,
                "success": False,
                "error": str(e)
            })
        finally:
            self.stats["active_workers"] -= 1

    def _analyze_new_replays(self) -> None:
        """새 리플레이 분석"""
        if not self.replay_dir.exists():
            return

        # 분석되지 않은 리플레이 찾기
        analyzed_file = self.output_dir / "analyzed_replays.json"
        analyzed = set()
        if analyzed_file.exists():
            try:
                with open(analyzed_file, 'r') as f:
                    analyzed = set(json.load(f))
            except Exception:
                pass

        # 새 리플레이 큐에 추가
        for replay_path in self.replay_dir.glob("**/*.SC2Replay"):
            if str(replay_path) not in analyzed:
                self.submit_task({
                    "type": "analyze_replay",
                    "path": str(replay_path)
                })
                analyzed.add(str(replay_path))

        # 분석된 목록 저장
        try:
            with open(analyzed_file, 'w') as f:
                json.dump(list(analyzed), f)
        except Exception:
            pass

    def _do_analyze_replay(self, replay_path: str) -> Optional[Dict[str, Any]]:
        """리플레이 분석 수행"""
        if not replay_path:
            return None

        try:
            # sc2reader로 분석 시도
            try:
                import sc2reader
                replay = sc2reader.load_replay(replay_path, load_level=2)

                result = {
                    "path": replay_path,
                    "map": replay.map_name,
                    "duration": replay.game_length.seconds if hasattr(replay, 'game_length') else 0,
                    "players": [
                        {
                            "name": p.name,
                            "race": str(p.play_race) if hasattr(p, 'play_race') else "Unknown",
                            "result": str(p.result) if hasattr(p, 'result') else "Unknown"
                        }
                        for p in replay.players
                    ],
                    "analyzed_at": datetime.now().isoformat()
                }

                self.stats["replays_analyzed"] += 1
                return result

            except ImportError:
                # sc2reader 없으면 기본 정보만
                return {
                    "path": replay_path,
                    "analyzed_at": datetime.now().isoformat(),
                    "note": "sc2reader not available"
                }

        except Exception as e:
            print(f"[BG_LEARNER] Replay analysis failed: {e}")
            return None

    def _train_model_batch(self) -> None:
        """배치 모델 훈련"""
        # 학습 데이터 수집
        training_data = self._collect_training_data()
        if training_data:
            self.submit_task({
                "type": "train_model",
                "data": training_data
            })

    def _collect_training_data(self) -> List[Dict[str, Any]]:
        """학습 데이터 수집"""
        data = []

        # 결과 큐에서 데이터 수집
        while not self.result_queue.empty():
            try:
                result = self.result_queue.get_nowait()
                if result.get("success") and result.get("result"):
                    data.append(result["result"])
            except queue.Empty:
                break

        return data

    def _do_train_model(self, data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """모델 훈련 수행"""
        if not data:
            return None

        try:
            # BatchTrainer 사용
            try:
                from local_training.scripts.batch_trainer import BatchTrainer

                trainer = BatchTrainer()
                stats = trainer.train_from_batch_results(data, epochs=5)
                self.stats["models_trained"] += 1

                return {
                    "samples": len(data),
                    "stats": stats,
                    "trained_at": datetime.now().isoformat()
                }

            except ImportError:
                # BatchTrainer 없으면 스킵
                return {
                    "samples": len(data),
                    "note": "BatchTrainer not available",
                    "trained_at": datetime.now().isoformat()
                }

        except Exception as e:
            print(f"[BG_LEARNER] Model training failed: {e}")
            return None

    def submit_task(self, task: Dict[str, Any]) -> None:
        """태스크 제출"""
        self.task_queue.put(task)

    def submit_custom_task(self, func: Callable, *args) -> None:
        """커스텀 태스크 제출"""
        self.submit_task({
            "type": "custom",
            "func": func,
            "args": args
        })

    def get_stats(self) -> Dict[str, Any]:
        """통계 반환"""
        return self.stats.copy()

    def get_results(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """결과 가져오기"""
        results = []
        while len(results) < max_results and not self.result_queue.empty():
            try:
                results.append(self.result_queue.get_nowait())
            except queue.Empty:
                break
        return results

    def is_running(self) -> bool:
        """실행 상태 확인"""
        return self.running

    def wait_for_completion(self, timeout: float = 30.0) -> bool:
        """모든 태스크 완료 대기"""
        start = time.time()
        while time.time() - start < timeout:
            if self.task_queue.empty() and self.stats["active_workers"] == 0:
                return True
            time.sleep(0.1)
        return False


# 싱글톤 인스턴스
_instance: Optional[BackgroundParallelLearner] = None


def get_background_learner(
    max_workers: int = 2,
    enable_replay_analysis: bool = True,
    enable_model_training: bool = True
) -> BackgroundParallelLearner:
    """싱글톤 인스턴스 반환"""
    global _instance
    if _instance is None:
        _instance = BackgroundParallelLearner(
            max_workers=max_workers,
            enable_replay_analysis=enable_replay_analysis,
            enable_model_training=enable_model_training
        )
    return _instance


def main():
    """테스트 실행"""
    print("=" * 60)
    print("BACKGROUND PARALLEL LEARNER TEST")
    print("=" * 60)

    learner = BackgroundParallelLearner(max_workers=2)
    learner.start()

    print("[TEST] Running for 10 seconds...")
    time.sleep(10)

    print("\n[STATS]")
    stats = learner.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    learner.stop()
    print("\n[TEST] Complete")


if __name__ == "__main__":
    main()
