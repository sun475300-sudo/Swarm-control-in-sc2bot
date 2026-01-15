# 신경망 모델 학습 시작 가이드

**작성일**: 2026-01-15  
**목적**: 게임 실행하여 신경망 모델 생성 및 학습 시작

---

## ? 준비 완료 사항

### 1. **모델 저장 경로 확인** ?
- 경로: `wicked_zerg_challenger/local_training/models/`
- 상태: 디렉토리 생성 완료
- 저장 파일: `zerg_net_model.pt` (또는 `zerg_net_model_{instance_id}.pt`)

### 2. **학습 데이터 통합** ?
- 빌드 오더: `local_training/scripts/learned_build_orders.json` (hive_supply 수정 완료)
- 학습 파라미터: 게임 실행 시 자동 로드

---

## ? 모델 학습 시작 방법

### 방법 1: 배치 파일 사용 (가장 간단) ?

```cmd
cd wicked_zerg_challenger
bat\start_model_training.bat
```

**실행 내용**:
- StarCraft II 게임 자동 실행
- 신경망 학습 활성화 (`train_mode=True`)
- 실시간 모델 학습 및 저장

---

### 방법 2: Python 스크립트 직접 실행

```cmd
cd wicked_zerg_challenger
python run_with_training.py
```

**실행 내용**:
- 게임 실행 (`AbyssalReefLE` 맵)
- Terran VeryHard vs Zerg Bot
- 신경망 학습 활성화

---

### 방법 3: 통합 학습 파이프라인 (전체 학습)

```cmd
cd wicked_zerg_challenger\local_training
python main_integrated.py
```

**실행 내용**:
- 리플레이 학습 + 게임 학습 통합
- 신경망 모델 학습
- 빌드 오더 파라미터 학습

---

## ? 학습 구성

### 신경망 아키텍처

- **입력 차원**: 15차원
  - Self (5): Minerals, Gas, Supply Used, Drone Count, Army Count
  - Enemy (10): Enemy Army Count, Tech Level, Threat Level, Unit Diversity, Scout Coverage, Main Distance, Expansion Count, Resource Estimate, Upgrade Count, Air/Ground Ratio

- **출력 차원**: 4차원
  - Actions: ATTACK, DEFENSE, ECONOMY, TECH_FOCUS

- **은닉층**: 64개 뉴런

### 학습 알고리즘

- **알고리즘**: REINFORCE (Policy Gradient)
- **학습률**: 0.001
- **디바이스**: GPU (CUDA) 우선, 없으면 CPU

---

## ? 학습 프로세스

### 게임 실행 중 학습 흐름

1. **게임 시작**:
   - 모델 로드 시도 (`local_training/models/zerg_net_model.pt`)
   - 모델이 없으면 새 모델 생성
   - GPU 감지 및 설정

2. **게임 진행 중**:
   - 매 프레임마다 상태 관측 수집
   - 신경망으로 행동 선택
   - 행동 실행 및 보상 수집

3. **게임 종료 후**:
   - REINFORCE 알고리즘으로 학습
   - 모델 저장 (`local_training/models/zerg_net_model.pt`)
   - 학습 로그 기록

---

## ? 모델 저장 위치

### 저장 경로

```
wicked_zerg_challenger/
├── local_training/
│   ├── models/
│   │   ├── zerg_net_model.pt          ? 첫 게임 후 생성됨
│   │   └── zerg_net_model_0.pt        (인스턴스별 저장)
│   └── scripts/
│       └── learned_build_orders.json  ? 빌드 오더 파라미터
```

### 모델 파일 확인

```cmd
dir wicked_zerg_challenger\local_training\models
```

---

## ?? 학습 설정 변경

### 학습률 조정

`wicked_zerg_bot_pro.py`에서 학습률 변경:
```python
self.neural_network = ReinforcementLearner(
    model, learning_rate=0.001,  # 기본값: 0.001
    instance_id=self.instance_id
)
```

### 신경망 아키텍처 변경

`zerg_net.py`에서 구조 변경:
```python
model = ZergNet(
    input_size=15,      # 입력 차원
    hidden_size=64,     # 은닉층 크기
    output_size=4       # 출력 차원
)
```

---

## ? 학습 확인 방법

### 1. 모델 파일 생성 확인

```cmd
dir wicked_zerg_challenger\local_training\models\*.pt
```

**예상 결과**:
```
zerg_net_model.pt  (게임 실행 후 생성됨)
```

### 2. 학습 로그 확인

```cmd
type wicked_zerg_challenger\logs\training_log.log
```

**확인 사항**:
- `[OK] Model saved: ...` 메시지
- `[OK] Neural network initialized` 메시지
- 학습 진행 상황

### 3. 모델 파일 크기 확인

게임을 여러 번 실행하면 모델 파일 크기가 증가합니다 (학습 진행 중).

---

## ?? 주의 사항

### 1. 첫 실행 시

- 모델 파일이 없으면 새 모델 생성
- 첫 게임 후 모델이 저장됨
- 이후 게임에서는 기존 모델 로드 후 계속 학습

### 2. GPU 사용

- NVIDIA GPU가 있으면 자동으로 GPU 사용
- GPU 메모리 부족 시 CPU 모드로 전환
- CPU 모드는 학습 속도가 느릴 수 있음

### 3. 학습 시간

- 게임당 학습 시간: 게임 길이에 따라 다름 (보통 5-20분)
- 모델 저장 시간: 게임 종료 후 약 1-2초

---

## ? 다음 단계

### 1. 여러 게임 실행

- 모델 학습은 게임을 여러 번 실행할수록 개선됨
- 권장: 최소 10-20 게임 실행

### 2. 학습 데이터 확인

- `local_training/models/` 디렉토리에서 모델 파일 확인
- 학습 로그에서 학습 진행 상황 확인

### 3. 모델 성능 평가

- 게임 승률 추적
- 전략 선택 패턴 분석
- Telemetry 데이터로 성능 분석

---

## ? 실행 예시

### 첫 번째 실행

```cmd
C:\> cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
C:\...\wicked_zerg_challenger> bat\start_model_training.bat

[OK] StarCraft II API available
[INFO] Training Configuration:
  - 15-dimensional state vector (Self 5 + Enemy 10)
  - REINFORCE algorithm for policy learning
  - Model auto-saves after each game
  - Training enabled: train_mode=True

[STEP 1] Starting game with neural network training...
[INFO] Game window will open - you can watch the training in real-time!

[OK] Neural network initialized
[OK] Model -> GPU: cuda
[OK] ? GPU confirmed
[OK] Neural network active
[OK] ? GPU: NVIDIA GeForce RTX 3060 (30% usage)

... (게임 진행) ...

[OK] Model saved: local_training/models/zerg_net_model.pt
TRAINING COMPLETE
```

### 두 번째 실행 이후

```cmd
[INFO] Model file not found in any expected location.
[INFO] Starting with a new model (will be saved after first game)

... (게임 진행) ...

[MODEL] Saving to local_training/models/: local_training/models/zerg_net_model.pt
[OK] Model saved: local_training/models/zerg_net_model.pt
```

---

**준비 완료**: ? **모델 학습을 시작할 수 있습니다**

**추천 실행 방법**: `bat\start_model_training.bat` 실행

**예상 결과**: 
1. 게임 실행
2. 신경망 학습 활성화
3. 게임 종료 후 모델 저장 (`local_training/models/zerg_net_model.pt`)

---
