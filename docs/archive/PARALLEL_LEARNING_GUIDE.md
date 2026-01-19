# 백그라운드 병렬 학습 시스템 가이드

## 개요

백그라운드 병렬 학습 시스템은 메인 게임이 실행되는 동안 별도 프로세스에서 리플레이 분석 및 신경망 모델 학습을 병렬로 수행합니다. 이를 통해 게임 실행을 방해하지 않고 지속적인 학습이 가능합니다.

## 주요 기능

### 1. 백그라운드 리플레이 분석
- 프로게이머 리플레이 파일을 자동으로 분석
- 빌드 오더 파라미터 추출 및 학습
- `learned_build_orders.json` 자동 업데이트

### 2. 백그라운드 모델 학습
- 수집된 게임 데이터로 신경망 모델 학습
- REINFORCE 알고리즘 기반 정책 학습
- 모델 자동 저장 및 통합

### 3. 리소스 모니터링
- CPU, 메모리, GPU 사용률 자동 모니터링
- 시스템 리소스에 따른 자동 워커 수 조절
- 리소스 부족 시 자동 대기

### 4. 병렬 처리
- 최대 2개의 병렬 워커 프로세스
- 멀티프로세싱 기반 독립 실행
- 메인 게임과 완전 분리된 실행

## 사용 방법

### 자동 시작 (권장)

`run_with_training.py`를 실행하면 자동으로 백그라운드 학습이 시작됩니다:

```bash
python wicked_zerg_challenger/run_with_training.py
```

또는 배치 스크립트 사용:

```bash
wicked_zerg_challenger\bat\start_model_training.bat
```

### 수동 제어

Python 코드에서 직접 사용:

```python
from tools.background_parallel_learner import BackgroundParallelLearner

# 학습 매니저 생성
learner = BackgroundParallelLearner(
    max_workers=2,  # 최대 병렬 워커 수
    enable_replay_analysis=True,
    enable_model_training=True
)

# 시작
learner.start()

# ... 게임 실행 ...

# 통계 확인
stats = learner.get_stats()
print(f"Replays Analyzed: {stats['replays_analyzed']}")
print(f"Models Trained: {stats['models_trained']}")

# 중지
learner.stop()
```

## 설정

### 환경 변수

- `REPLAY_ARCHIVE_DIR`: 리플레이 디렉토리 경로 (기본값: `D:/replays/replays`)
- `NUM_INSTANCES`: 최대 병렬 워커 수 (기본값: 2)

### 리소스 임계값

`background_parallel_learner.py`에서 조정 가능:

```python
self.cpu_threshold = 80.0  # CPU 사용률 임계값 (%)
self.memory_threshold = 85.0  # 메모리 사용률 임계값 (%)
self.gpu_memory_threshold = 90.0  # GPU 메모리 사용률 임계값 (%)
```

## 동작 원리

### 1. 백그라운드 스레드
- 메인 게임과 별도의 스레드에서 실행
- 1초마다 리소스 체크 및 새 작업 시작

### 2. 멀티프로세싱 워커
- 각 학습 작업은 별도 프로세스에서 실행
- 메인 프로세스와 완전히 독립적
- 프로세스 간 통신은 `multiprocessing.Queue` 사용

### 3. 리소스 기반 스케줄링
- 시스템 리소스가 충분할 때만 새 워커 시작
- 리소스 부족 시 자동 대기
- 완료된 워커는 자동 정리

### 4. 학습 결과 통합
- 리플레이 분석 결과는 `learned_build_orders.json`에 자동 통합
- 모델 학습 결과는 `local_training/models/`에 자동 저장
- 가중 평균 방식으로 기존 데이터와 통합

## 통계 모니터링

게임이 5게임마다 백그라운드 학습 통계가 출력됩니다:

```
======================================================================
? [BACKGROUND LEARNING] STATISTICS
======================================================================
Replays Analyzed: 12
Models Trained: 8
Total Processing Time: 245.30s
Active Workers: 1/2
Errors: 0
======================================================================
```

## 주의사항

### 1. 리소스 사용
- 백그라운드 학습은 추가 CPU/메모리/GPU를 사용합니다
- 시스템 리소스가 부족한 경우 `max_workers`를 줄이세요

### 2. 리플레이 디렉토리
- 리플레이 파일이 `REPLAY_ARCHIVE_DIR`에 있어야 합니다
- `.SC2Replay` 확장자 파일만 분석됩니다

### 3. 모델 파일
- 모델 파일은 `local_training/models/zerg_net_model.pt`에 저장됩니다
- 여러 워커가 동시에 접근할 수 있으므로 파일 잠금이 필요할 수 있습니다

### 4. 프로세스 종료
- `Ctrl+C`로 훈련을 중지하면 백그라운드 학습도 자동으로 중지됩니다
- 모든 워커 프로세스가 정상적으로 종료될 때까지 대기합니다

## 문제 해결

### 백그라운드 학습이 시작되지 않음
- `tools/background_parallel_learner.py` 파일이 존재하는지 확인
- Python 경로 설정이 올바른지 확인
- 에러 메시지를 확인하여 누락된 의존성 설치

### 리플레이 분석이 작동하지 않음
- `sc2reader` 패키지가 설치되어 있는지 확인: `pip install sc2reader`
- 리플레이 디렉토리 경로가 올바른지 확인
- 리플레이 파일이 `.SC2Replay` 형식인지 확인

### 모델 학습이 작동하지 않음
- PyTorch가 설치되어 있는지 확인: `pip install torch`
- GPU가 있는 경우 CUDA가 올바르게 설정되어 있는지 확인
- 모델 파일 경로에 쓰기 권한이 있는지 확인

### 리소스 부족 오류
- `max_workers`를 줄이세요 (예: 1)
- 다른 리소스 집약적인 프로그램을 종료하세요
- 시스템 리소스 임계값을 조정하세요

## 성능 최적화

### 1. 워커 수 조절
- CPU 코어 수에 맞춰 `max_workers` 설정
- 일반적으로 CPU 코어 수의 50% 정도가 적절합니다

### 2. 리소스 임계값 조정
- 시스템 사양에 맞춰 임계값 조정
- 더 보수적인 설정: 임계값을 낮춤 (예: 70%)
- 더 공격적인 설정: 임계값을 높임 (예: 90%)

### 3. 리플레이 파일 관리
- 분석 완료된 리플레이는 별도 디렉토리로 이동
- 불필요한 리플레이 파일 삭제
- 리플레이 파일 수를 제한하여 메모리 사용량 감소

## 향후 개선 사항

- [ ] 학습 데이터 큐 시스템 구현
- [ ] 분산 학습 지원 (여러 머신)
- [ ] 실시간 학습 진행률 대시보드
- [ ] 학습 작업 우선순위 큐
- [ ] 자동 리소스 스케일링

## 관련 파일

- `wicked_zerg_challenger/tools/background_parallel_learner.py`: 백그라운드 학습 매니저
- `wicked_zerg_challenger/run_with_training.py`: 메인 훈련 스크립트 (통합됨)
- `wicked_zerg_challenger/local_training/scripts/replay_build_order_learner.py`: 리플레이 분석
- `wicked_zerg_challenger/zerg_net.py`: 신경망 모델 및 학습
