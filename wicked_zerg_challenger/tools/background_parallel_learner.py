# -*- coding: utf-8 -*-
"""
Background Parallel Learning System

백그라운드에서 병렬로 리플레이 분석 및 신경망 학습을 수행하는 시스템.
메인 게임 실행을 방해하지 않고 별도 프로세스에서 학습을 진행합니다.

Features:
- Multiprocessing 기반 백그라운드 학습
- 리플레이 분석 병렬 처리
- 신경망 모델 백그라운드 학습
- 리소스 모니터링 및 자동 조절
- 학습 결과 자동 통합
"""

import json
import multiprocessing
import os
import sys
import time
import traceback
from pathlib import Path
import threading
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Set
from typing import Any
from typing import Union

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import psutil
 PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("[WARNING] psutil not available - resource monitoring disabled")


@dataclass
class LearningTask:
    """학습 작업 정의"""
    task_type: str  # 'replay_analysis' or 'model_training'
 task_id: str
 priority: int = 0 # 높을수록 우선순위 높음
 data: Optional[Dict] = None


@dataclass
class LearningResult:
    """학습 결과"""
 task_id: str
 success: bool
 result_data: Optional[Dict] = None
 error: Optional[str] = None
 processing_time: float = 0.0


class ResourceMonitor:
    """시스템 리소스 모니터링"""

def __init__(self):
    self.cpu_threshold = 80.0 # CPU 사용률 임계값 (%)
 self.memory_threshold = 85.0 # 메모리 사용률 임계값 (%)
 self.gpu_memory_threshold = 90.0 # GPU 메모리 사용률 임계값 (%)

def get_system_resources(self) -> Dict:
    """현재 시스템 리소스 상태 반환"""
 if not PSUTIL_AVAILABLE:
     return {"cpu": 0, "memory": 0, "gpu": 0, "available": True}

 cpu_percent = psutil.cpu_percent(interval=0.1)
 memory = psutil.virtual_memory()
 memory_percent = memory.percent

 # GPU 메모리 체크 (NVIDIA만)
 gpu_memory_percent = 0
 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
import torch
 if torch.cuda.is_available():
     allocated = torch.cuda.memory_allocated(0)
 reserved = torch.cuda.memory_reserved(0)
 total = torch.cuda.get_device_properties(0).total_memory
 gpu_memory_percent = (reserved / total) * 100
 except Exception:
     pass

 available = (
 cpu_percent < self.cpu_threshold and
 memory_percent < self.memory_threshold and
 gpu_memory_percent < self.gpu_memory_threshold
 )

 return {
     "cpu": cpu_percent,
     "memory": memory_percent,
     "gpu": gpu_memory_percent,
     "available": available
 }

def can_start_learning(self, current_workers: int, max_workers: int) -> bool:
    """새로운 학습 프로세스를 시작할 수 있는지 확인"""
 if current_workers >= max_workers:
     return False

 resources = self.get_system_resources()
     return resources["available"]


def analyze_replay_worker(replay_path: str, output_queue: Queue) -> Dict:
    """
 리플레이 분석 워커 함수 (별도 프로세스에서 실행)

 Args:
 replay_path: 리플레이 파일 경로
 output_queue: 결과를 전달할 큐

 Returns:
 분석 결과 딕셔너리
    """
 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     sys.path.insert(0, str(PROJECT_ROOT))

 # 리플레이 분석 모듈 import

 extractor = ReplayBuildOrderExtractor()

 # 리플레이 분석 수행
 start_time = time.time()
 learned_params = extractor.learn_from_replays(max_replays=1)
 processing_time = time.time() - start_time

 result = {
     "success": True,
     "learned_params": learned_params,
     "replay_path": replay_path,
     "processing_time": processing_time
 }

 output_queue.put(result)
 return result

 except Exception as e:
     error_msg = f"Replay analysis error: {str(e)}\n{traceback.format_exc()}"
 result = {
     "success": False,
     "error": error_msg,
     "replay_path": replay_path,
     "processing_time": 0.0
 }
 output_queue.put(result)
 return result


def train_model_worker(model_path: str, training_data: Dict, output_queue: Queue) -> Dict:
    """
 모델 학습 워커 함수 (별도 프로세스에서 실행)

 Args:
 model_path: 모델 파일 경로
 training_data: 학습 데이터
 output_queue: 결과를 전달할 큐

 Returns:
 학습 결과 딕셔너리
    """
 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     sys.path.insert(0, str(PROJECT_ROOT))

 # 신경망 학습 모듈 import
import torch

 # 모델 로드
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
 model = ZergNet()

 if os.path.exists(model_path):
     try:
         model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
 except Exception as e:
     print(f"[WARNING] Failed to load model: {e}, starting fresh")

 model = model.to(device)

 # 학습 수행
 learner = ReinforcementLearner(model, learning_rate=0.001, model_path=model_path)

 start_time = time.time()
 # 학습 데이터로 모델 업데이트
     if "states" in training_data and "actions" in training_data and "rewards" in training_data:
     # REINFORCE 알고리즘으로 학습
     learner.episode_states.extend(training_data["states"])
     learner.episode_actions.extend(training_data["actions"])
     learner.episode_rewards.extend(training_data["rewards"])

 # 학습 수행
 if len(learner.episode_states) > 0:
     learner.train_episode()
 learner.save_model()

 processing_time = time.time() - start_time

 result = {
     "success": True,
     "model_path": model_path,
     "processing_time": processing_time,
     "episodes_trained": len(training_data.get("states", []))
 }

 output_queue.put(result)
 return result

 except Exception as e:
     error_msg = f"Model training error: {str(e)}\n{traceback.format_exc()}"
 result = {
     "success": False,
     "error": error_msg,
     "model_path": model_path,
     "processing_time": 0.0
 }
 output_queue.put(result)
 return result


class BackgroundParallelLearner:
    """
 백그라운드 병렬 학습 매니저

 메인 게임 실행 중 백그라운드에서 리플레이 분석 및 모델 학습을 병렬로 수행합니다.
    """

def __init__(
 self,
 max_workers: int = 2,
 replay_dir: Optional[str] = None,
 model_path: Optional[str] = None,
 enable_replay_analysis: bool = True,
 enable_model_training: bool = True
 ):
     """
 Args:
 max_workers: 최대 병렬 워커 수
 replay_dir: 리플레이 디렉토리 경로
 model_path: 모델 파일 경로
 enable_replay_analysis: 리플레이 분석 활성화
 enable_model_training: 모델 학습 활성화
     """
 self.max_workers = max_workers
 self.enable_replay_analysis = enable_replay_analysis
 self.enable_model_training = enable_model_training

 # 경로 설정
 if replay_dir is None:
     replay_dir = os.environ.get("REPLAY_ARCHIVE_DIR", "D:/replays/replays")
 self.replay_dir = Path(replay_dir)

 if model_path is None:
     model_path = PROJECT_ROOT / "local_training" / "models" / "zerg_net_model.pt"
 self.model_path = str(model_path)

 # 리소스 모니터
 self.resource_monitor = ResourceMonitor()

 # 워커 관리
 self.active_workers: List[multiprocessing.Process] = []
 self.worker_results: Queue = multiprocessing.Queue()
 self.task_queue: Queue = Queue()

 # 학습 통계
 self.stats = {
     "replays_analyzed": 0,
     "models_trained": 0,
     "total_processing_time": 0.0,
     "errors": 0
 }

 # 백그라운드 스레드
 self.background_thread: Optional[threading.Thread] = None
 self.running = False

     print(f"[BACKGROUND LEARNER] Initialized with {max_workers} max workers")
     print(f"[BACKGROUND LEARNER] Replay dir: {self.replay_dir}")
     print(f"[BACKGROUND LEARNER] Model path: {self.model_path}")

def start(self):
    """백그라운드 학습 시작"""
 if self.running:
     print("[WARNING] Background learner already running")
 return

 self.running = True
 self.background_thread = threading.Thread(target=self._background_loop, daemon=True)
 self.background_thread.start()
     print("[BACKGROUND LEARNER] Started background learning thread")

def stop(self):
    """백그라운드 학습 중지"""
 self.running = False

 # 모든 워커 종료 대기
 for worker in self.active_workers:
     if worker.is_alive():
         worker.terminate()
 worker.join(timeout=5)

 if self.background_thread and self.background_thread.is_alive():
     self.background_thread.join(timeout=5)

     print("[BACKGROUND LEARNER] Stopped")

def _background_loop(self):
    """백그라운드 학습 메인 루프"""
 while self.running:
     pass
 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     # 활성 워커 정리
 self._cleanup_workers()

 # 리소스 체크 및 새 작업 시작
 if len(self.active_workers) < self.max_workers:
     if self.resource_monitor.can_start_learning(
 len(self.active_workers), self.max_workers
 ):
 self._start_next_task()

 # 결과 수집
 self._collect_results()

 # 잠시 대기 (CPU 부하 감소)
 time.sleep(1.0)

 except Exception as e:
     print(f"[ERROR] Background loop error: {e}")
 time.sleep(5.0)

def _cleanup_workers(self):
    """완료된 워커 프로세스 정리"""
 active = []
 for worker in self.active_workers:
     if worker.is_alive():
         active.append(worker)
 else:
     pass
 worker.join()
 self.active_workers = active

def _start_next_task(self):
    """다음 학습 작업 시작"""
 # 리플레이 분석 우선
 if self.enable_replay_analysis and len(self.active_workers) < self.max_workers:
     replay_files = self._get_replay_files()
 if replay_files:
     replay_path = replay_files[0]
 self._start_replay_analysis(replay_path)
 return

 # 모델 학습 (리플레이 분석이 없거나 비활성화된 경우)
 if self.enable_model_training and len(self.active_workers) < self.max_workers:
     # 학습 데이터가 있는지 확인
 training_data = self._get_pending_training_data()
 if training_data:
     self._start_model_training(training_data)

def _get_replay_files(self) -> List[str]:
    """분석할 리플레이 파일 목록 반환"""
 if not self.replay_dir.exists():
     return []

     replay_files = list(self.replay_dir.glob("*.SC2Replay"))
 return [str(f) for f in replay_files[:10]] # 최대 10개

def _get_pending_training_data(self) -> Optional[Dict]:
    """대기 중인 학습 데이터 반환"""
 # 실제 구현에서는 게임에서 수집된 데이터를 큐나 파일에서 읽어옴
 # 여기서는 예시로 None 반환
 return None

def _start_replay_analysis(self, replay_path: str):
    """리플레이 분석 워커 시작"""
 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     process = multiprocessing.Process(
 target=analyze_replay_worker,
 args=(replay_path, self.worker_results)
 )
 process.start()
 self.active_workers.append(process)
     print(f"[BACKGROUND LEARNER] Started replay analysis: {Path(replay_path).name}")
 except Exception as e:
     print(f"[ERROR] Failed to start replay analysis: {e}")

def _start_model_training(self, training_data: Dict):
    """모델 학습 워커 시작"""
 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     process = multiprocessing.Process(
 target=train_model_worker,
 args=(self.model_path, training_data, self.worker_results)
 )
 process.start()
 self.active_workers.append(process)
     print(f"[BACKGROUND LEARNER] Started model training")
 except Exception as e:
     print(f"[ERROR] Failed to start model training: {e}")

def _collect_results(self):
    """워커 결과 수집"""
 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     while True:
         pass
 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     result = self.worker_results.get_nowait()
 self._process_result(result)
 except Empty:
     break
 except Exception as e:
     print(f"[ERROR] Result collection error: {e}")

def _process_result(self, result: Dict):
    """학습 결과 처리"""
    if result.get("success"):
        pass
    if "learned_params" in result:
    # 리플레이 분석 결과
    self.stats["replays_analyzed"] += 1
    self._integrate_learned_params(result["learned_params"])
    print(f"[BACKGROUND LEARNER] Replay analyzed: {result.get('replay_path', 'unknown')}")
    elif "model_path" in result:
    # 모델 학습 결과
    self.stats["models_trained"] += 1
    print(f"[BACKGROUND LEARNER] Model trained: {result.get('episodes_trained', 0)} episodes")

    self.stats["total_processing_time"] += result.get("processing_time", 0.0)
 else:
     self.stats["errors"] += 1
     print(f"[ERROR] Learning task failed: {result.get('error', 'unknown error')}")

def _integrate_learned_params(self, learned_params: Dict):
    """학습된 파라미터 통합"""
 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     # learned_build_orders.json 업데이트
     build_orders_path = PROJECT_ROOT / "local_training" / "scripts" / "learned_build_orders.json"

 if build_orders_path.exists():
     with open(build_orders_path, 'r', encoding='utf-8') as f:
 current_params = json.load(f)
 else:
     pass
 current_params = {}

 # 새 파라미터 통합 (가중 평균)
 for key, value in learned_params.items():
     if key in current_params:
         # 기존 값과 새 값의 가중 평균 (기존 70%, 새 30%)
 current_params[key] = current_params[key] * 0.7 + value * 0.3
 else:
     pass
 current_params[key] = value

 # 저장
     with open(build_orders_path, 'w', encoding='utf-8') as f:
 json.dump(current_params, f, indent=2, ensure_ascii=False)

     print(f"[BACKGROUND LEARNER] Integrated {len(learned_params)} learned parameters")

 except Exception as e:
     print(f"[ERROR] Failed to integrate learned params: {e}")

def get_stats(self) -> Dict:
    """학습 통계 반환"""
 return {
 **self.stats,
    "active_workers": len(self.active_workers),
    "max_workers": self.max_workers
 }

def submit_training_data(self, training_data: Dict):
    """게임에서 수집된 학습 데이터 제출"""
 # 실제 구현에서는 큐에 추가하거나 파일로 저장
 # 여기서는 예시로 출력만
    print(f"[BACKGROUND LEARNER] Training data submitted: {len(training_data.get('states', []))} states")


def main():
    """테스트용 메인 함수"""
    print("\n" + "=" * 70)
    print("BACKGROUND PARALLEL LEARNING SYSTEM - TEST")
    print("=" * 70)

 learner = BackgroundParallelLearner(
 max_workers=2,
 enable_replay_analysis=True,
 enable_model_training=True
 )

 learner.start()

 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     # 30초간 실행
 time.sleep(30)

 # 통계 출력
 stats = learner.get_stats()
     print("\n" + "=" * 70)
     print("LEARNING STATISTICS")
     print("=" * 70)
     print(f"Replays Analyzed: {stats['replays_analyzed']}")
     print(f"Models Trained: {stats['models_trained']}")
     print(f"Total Processing Time: {stats['total_processing_time']:.2f}s")
     print(f"Errors: {stats['errors']}")
     print(f"Active Workers: {stats['active_workers']}")

 finally:
     pass
 learner.stop()


if __name__ == "__main__":
    main()
