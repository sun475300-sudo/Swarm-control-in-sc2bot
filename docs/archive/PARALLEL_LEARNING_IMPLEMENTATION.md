# 백그라운드 병렬 학습 시스템 구현 완료

## 구현 개요

메인 게임 실행 중 백그라운드에서 리플레이 분석 및 신경망 모델 학습을 병렬로 수행하는 시스템을 구현했습니다.

## 구현된 기능

### 1. BackgroundParallelLearner 클래스
- **위치**: `wicked_zerg_challenger/tools/background_parallel_learner.py`
- **기능**:
  - 백그라운드 스레드에서 지속적으로 학습 작업 관리
  - 멀티프로세싱 기반 병렬 워커 실행
  - 리소스 모니터링 및 자동 조절
  - 학습 결과 자동 통합

### 2. run_with_training.py 통합
- **변경 사항**:
  - 백그라운드 학습 매니저 자동 초기화 및 시작
  - 5게임마다 학습 통계 출력
  - 훈련 종료 시 백그라운드 학습 자동 중지

### 3. 리소스 모니터링
- CPU, 메모리, GPU 사용률 실시간 모니터링
- 리소스 임계값 기반 자동 워커 수 조절
- 시스템 부하에 따른 자동 대기

### 4. 학습 작업 처리
- **리플레이 분석**: 프로게이머 리플레이에서 빌드 오더 파라미터 추출
- **모델 학습**: 수집된 게임 데이터로 신경망 모델 학습
- **결과 통합**: 학습된 파라미터를 `learned_build_orders.json`에 자동 통합

## 사용 방법

### 자동 사용 (권장)
`run_with_training.py`를 실행하면 자동으로 백그라운드 학습이 시작됩니다:

```bash
python wicked_zerg_challenger/run_with_training.py
```

### 수동 제어
Python 코드에서 직접 제어:

```python
from tools.background_parallel_learner import BackgroundParallelLearner

learner = BackgroundParallelLearner(max_workers=2)
learner.start()
# ... 게임 실행 ...
learner.stop()
```

## 주요 특징

### 1. 비동기 처리
- 메인 게임과 완전히 독립된 프로세스에서 실행
- 게임 실행을 방해하지 않음
- 멀티프로세싱으로 진정한 병렬 처리

### 2. 리소스 인식
- 시스템 리소스를 실시간으로 모니터링
- 리소스 부족 시 자동으로 워커 수 조절
- CPU, 메모리, GPU 모두 고려

### 3. 자동 통합
- 리플레이 분석 결과 자동 통합
- 모델 학습 결과 자동 저장
- 가중 평균 방식으로 기존 데이터와 통합

### 4. 오류 처리
- 각 워커의 오류를 독립적으로 처리
- 오류 발생 시에도 다른 워커는 계속 실행
- 오류 통계 자동 수집

## 통계 출력

게임이 5게임마다 다음과 같은 통계가 출력됩니다:

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

## 설정

### 기본 설정
- **최대 워커 수**: 2
- **리플레이 디렉토리**: `D:/replays/replays` (환경 변수로 변경 가능)
- **모델 경로**: `local_training/models/zerg_net_model.pt`

### 리소스 임계값
- **CPU**: 80%
- **메모리**: 85%
- **GPU**: 90%

## 파일 구조

```
wicked_zerg_challenger/
├── tools/
│   └── background_parallel_learner.py  # 백그라운드 학습 매니저
├── run_with_training.py                 # 메인 훈련 스크립트 (통합됨)
└── local_training/
    ├── scripts/
    │   └── replay_build_order_learner.py  # 리플레이 분석
    └── models/
        └── zerg_net_model.pt            # 학습된 모델
```

## 성능

### 예상 성능 (RTX 2060 6GB 기준)
- **리플레이 분석**: 약 5-10초/리플레이
- **모델 학습**: 약 2-5초/에피소드
- **병렬 처리**: 최대 2개 워커 동시 실행
- **리소스 사용**: CPU 20-40%, 메모리 2-4GB, GPU 1-2GB

## 주의사항

1. **리소스 사용**: 백그라운드 학습은 추가 리소스를 사용합니다
2. **리플레이 파일**: 분석할 리플레이 파일이 필요합니다
3. **의존성**: `sc2reader`, `torch`, `psutil` 패키지가 필요합니다

## 향후 개선

- [ ] 학습 데이터 큐 시스템
- [ ] 분산 학습 지원
- [ ] 실시간 대시보드
- [ ] 우선순위 큐
- [ ] 자동 스케일링

## 관련 문서

- `PARALLEL_LEARNING_GUIDE.md`: 상세 사용 가이드
- `wicked_zerg_challenger/tools/background_parallel_learner.py`: 소스 코드
