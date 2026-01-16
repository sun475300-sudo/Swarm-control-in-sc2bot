# 프로게이머 리플레이 학습 후 데이터 경로 추적 및 재설정

**작성 일시**: 2026-01-16  
**상태**: ? **구현 완료**

---

## ? 구현 완료

### 데이터 경로 추적 및 재설정

프로게이머 리플레이 학습 후 데이터 경로를 추적하고, `D:\replays\archive`로 재설정하는 기능이 구현되었습니다.

### 구현 내용

1. **학습 데이터 경로 추적**
   - 학습된 파라미터 저장 경로 추적
   - 소스 리플레이 디렉토리 추적
   - 아카이브 디렉토리 추적
   - 타임스탬프 추적

2. **경로 재설정**
   - 기본 아카이브 디렉토리: `D:\replays\archive`
   - 학습 데이터 자동 아카이브
   - 경로 추적 정보 저장

3. **경로 추적 정보**
   - `D:\replays\archive\learning_path_tracking.json`
   - 최대 100개 항목 유지
   - 각 학습 세션의 경로 정보 기록

---

## ? 데이터 경로 구조

### 아카이브 디렉토리 구조

```
D:\replays\archive\
├── training_YYYYMMDD_HHMMSS\
│   ├── learned_build_orders.json
│   └── strategy_db.json (if applicable)
├── training_YYYYMMDD_HHMMSS\
│   └── ...
└── learning_path_tracking.json
```

### 로컬 학습 디렉토리

```
local_training\scripts\
└── learned_build_orders.json (최신 학습 데이터)
```

---

## ? 워크플로우

### Step 1: 프로게이머 리플레이 학습

- **소스**: `D:\replays\replays` 또는 `replays_archive`
- **학습**: 빌드 오더 추출 및 분석
- **출력**: 학습된 파라미터

### Step 2: 데이터 저장

- **아카이브 경로**: `D:\replays\archive\training_YYYYMMDD_HHMMSS\learned_build_orders.json`
- **로컬 경로**: `local_training\scripts\learned_build_orders.json`
- **둘 다 저장**: 아카이브용 + 즉시 사용용

### Step 3: 경로 추적

- **추적 파일**: `D:\replays\archive\learning_path_tracking.json`
- **추적 정보**:
  - 타임스탬프
  - 소스 리플레이 디렉토리
  - 아카이브 디렉토리
  - 저장 경로
  - 학습된 파라미터 수

### Step 4: 경로 재설정

- **기본 아카이브**: `D:\replays\archive`
- **자동 생성**: 디렉토리 자동 생성
- **경로 추적**: 모든 학습 세션 추적

---

## ? 경로 추적 정보 예시

```json
[
  {
    "timestamp": "2026-01-16T14:30:00",
    "source_replay_dir": "D:/replays/replays",
    "archive_dir": "D:/replays/archive",
    "saved_path": "D:/replays/archive/training_20260116_143000/learned_build_orders.json",
    "learned_params_count": 7
  },
  ...
]
```

---

## ? 사용 방법

### 자동 실행

`post_training_learning_workflow.py`를 실행하면 자동으로:
1. 프로게이머 리플레이 학습
2. `D:\replays\archive`로 데이터 저장
3. 경로 추적 정보 저장

### 수동 설정

```python
from tools.post_training_learning_workflow import learn_from_pro_replays, track_and_reset_data_paths
from pathlib import Path

# 학습 및 경로 추적
archive_dir = Path("D:/replays/archive")
data_paths = learn_from_pro_replays(max_replays=50, archive_dir=archive_dir)

# 경로 추적 및 재설정
if data_paths:
    track_and_reset_data_paths(data_paths, target_archive_dir=archive_dir)
```

---

## ? 경로 추적 파일 구조

### learning_path_tracking.json

```json
[
  {
    "timestamp": "ISO 8601 형식",
    "source_replay_dir": "소스 리플레이 디렉토리",
    "archive_dir": "아카이브 디렉토리",
    "saved_path": "저장된 파일 경로",
    "learned_params_count": 7
  }
]
```

### 특징

- **최대 항목 수**: 100개 (자동 관리)
- **최신 우선**: 최신 항목이 리스트 끝에 추가
- **자동 관리**: 100개 초과 시 오래된 항목 자동 제거

---

## ? 기대 효과

### 데이터 관리

- ? **중앙 집중식 아카이브**: 모든 학습 데이터를 `D:\replays\archive`에 저장
- ? **경로 추적**: 모든 학습 세션의 경로 정보 추적
- ? **이력 관리**: 학습 이력 자동 관리

### 자동화

- ? **자동 저장**: 학습 후 자동으로 아카이브 저장
- ? **자동 추적**: 경로 정보 자동 추적
- ? **자동 관리**: 추적 데이터 자동 관리

---

**완료!** 프로게이머 리플레이 학습 후 데이터 경로가 자동으로 추적되고 `D:\replays\archive`로 재설정됩니다.
