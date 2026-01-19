# 프로게이머 리플레이 학습 → 빌드오더 학습 → 게임 훈련 적용 워크플로우

## 개요

이 워크플로우는 프로게이머 리플레이에서 빌드오더를 학습하고, 학습한 내용을 실제 게임 훈련에 자동으로 적용하여 성능을 개선합니다.

## 전체 프로세스

```
1. 프로게이머 리플레이 학습
   ↓
2. 빌드오더 파라미터 추출 (learned_build_orders.json)
   ↓
3. 게임 훈련 데이터 수집 (선택적)
   ↓
4. 훈련 데이터와 프로 리플레이 비교 분석 (선택적)
   ↓
5. 개선된 파라미터를 실제 게임에 적용
   (production_resilience.py가 자동으로 사용)
```

## 빠른 시작

### 방법 1: 통합 워크플로우 실행 (권장)

```cmd
# 기본 (30개 리플레이)
D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\bat\integrated_replay_learning.bat

# 50개 리플레이 사용
D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\bat\integrated_replay_learning.bat 50

# 또는 Python 직접 실행
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
python tools\integrated_replay_learning_workflow.py --max-replays 30
```

### 방법 2: 단계별 실행

```cmd
# Step 1: 리플레이 학습
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
bat\start_replay_learning_30.bat

# Step 2: 게임 훈련 데이터 수집 (선택적)
bat\start_training_data_collection.bat

# Step 3: 훈련 데이터 추출 및 비교 분석 (선택적)
python tools\extract_and_train_from_training.py
```

## 워크플로우 단계 상세

### Step 1: 프로게이머 리플레이 학습

**목적**: 프로게이머 리플레이에서 빌드오더 타이밍 추출 및 학습

**실행**:
- `local_training/scripts/replay_build_order_learner.py`
- 리플레이 디렉토리: `D:\replays\replays`
- 최대 리플레이 수: 30개 (기본값)

**출력**:
- `local_training/scripts/learned_build_orders.json`

**학습되는 파라미터**:
- `spawning_pool_supply`: Spawning Pool 건설 Supply (프로 기준선: 17)
- `gas_supply`: Gas Extractor 건설 Supply (프로 기준선: 17-18)
- `natural_expansion_supply`: Natural Expansion 건설 Supply (프로 기준선: 30-32)

### Step 2: 게임 훈련 데이터 수집 (선택적)

**목적**: 실제 게임 훈련에서 빌드오더 타이밍 데이터 수집

**실행**:
- `tools/collect_training_data.py`
- 입력: `training_stats.json` (게임 훈련 결과)

**출력**:
- 빌드오더 타이밍 통계
- 게임 결과 분석

### Step 3: 훈련 데이터 추출 및 비교 분석 (선택적)

**목적**: 훈련 데이터와 프로 리플레이 비교하여 개선점 도출

**실행**:
- `tools/extract_and_train_from_training.py`
- 입력: `training_stats.json`, `build_order_comparison_history.json`
- 프로 리플레이와 비교 분석

**출력**:
- 비교 분석 결과
- 개선된 파라미터 (learned_build_orders.json 업데이트)

### Step 4: 학습된 파라미터 적용

**자동 적용**: `production_resilience.py`가 자동으로 `get_learned_parameter()` 함수를 통해 학습된 파라미터를 사용합니다.

**확인 방법**:
```python
from config import get_learned_parameter

# 학습된 파라미터 가져오기
spawning_pool_supply = get_learned_parameter("spawning_pool_supply", 17.0)
gas_supply = get_learned_parameter("gas_supply", 17.0)
natural_expansion_supply = get_learned_parameter("natural_expansion_supply", 30.0)
```

## 적용되는 빌드오더

### 1. Spawning Pool (Spawning Pool)
- **프로 기준선**: Supply 17
- **적용 위치**: `production_resilience.py`
- **로직**: Supply 17 이상일 때 건설

### 2. Gas Extractor (가스 추출기)
- **프로 기준선**: Supply 17-18
- **적용 위치**: `production_resilience.py`
- **로직**: Supply 17-18 범위에서 건설

### 3. Natural Expansion (자연 확장)
- **프로 기준선**: Supply 30-32
- **적용 위치**: `production_resilience.py`
- **로직**: Supply 30-32 범위에서 건설

## 파일 구조

```
wicked_zerg_challenger/
├── local_training/
│   └── scripts/
│       ├── replay_build_order_learner.py    # 리플레이 학습 스크립트
│       └── learned_build_orders.json        # 학습된 빌드오더 파라미터
├── tools/
│   ├── integrated_replay_learning_workflow.py  # 통합 워크플로우
│   ├── collect_training_data.py                # 훈련 데이터 수집
│   └── extract_and_train_from_training.py      # 훈련 데이터 추출 및 학습
├── bat/
│   └── integrated_replay_learning.bat          # 통합 워크플로우 실행
└── local_training/
    └── production_resilience.py                # 실제 게임에 적용 (자동)
```

## 프로 기준선 파라미터

현재 학습된 파라미터 (`learned_build_orders.json`):

```json
{
  "spawning_pool_supply": 17.0,
  "gas_supply": 17.0,
  "natural_expansion_supply": 30.0,
  "roach_warren_supply": 55,
  "lair_supply": 12,
  "hive_supply": 12,
  "hydralisk_den_supply": 122
}
```

## 다음 단계

1. **리플레이 학습 완료 후**:
   ```cmd
   python run_with_training.py
   ```
   게임 훈련을 시작하면 자동으로 학습된 빌드오더가 적용됩니다.

2. **게임 훈련 결과 수집**:
   ```cmd
   python tools\collect_training_data.py
   ```

3. **비교 분석 및 개선**:
   ```cmd
   python tools\extract_and_train_from_training.py
   ```

## 문제 해결

### 리플레이를 찾을 수 없는 경우

환경 변수 설정:
```cmd
set REPLAY_ARCHIVE_DIR=D:\replays\replays
```

### 학습된 파라미터가 적용되지 않는 경우

1. `learned_build_orders.json` 파일 확인
2. `production_resilience.py`에서 `get_learned_parameter()` 호출 확인
3. 게임 재시작 후 확인

## 참고

- 리플레이 학습은 시간이 걸릴 수 있습니다 (리플레이당 약 1-2초)
- 최소 10개 이상의 리플레이를 사용하는 것을 권장합니다
- 프로 기준선 파라미터는 여러 리플레이의 평균/중앙값을 사용합니다
