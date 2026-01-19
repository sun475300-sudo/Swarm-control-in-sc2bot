# D:\replays\archive 디렉토리 구조 안내

## 디렉토리 구조

### 폴더 목록

`D:\replays\archive` 디렉토리에는 **17개의 training 폴더**가 있습니다:

| 폴더명 | 생성일 | 설명 |
|--------|--------|------|
| `training_20260113_011452` | 2026-01-13 01:14:52 | 빌드오더 학습 결과 저장 |
| `training_20260113_085621` | 2026-01-13 08:56:21 | 학습 결과 + 상태 파일 |
| `training_20260114_162547` | 2026-01-14 16:25:47 | 빌드오더 학습 결과 |
| `training_20260114_163609` | 2026-01-14 16:36:09 | 빌드오더 학습 결과 |
| `training_20260114_163718` | 2026-01-14 16:37:18 | 빌드오더 학습 결과 |
| `training_20260114_165946` | 2026-01-14 16:59:46 | 빌드오더 학습 결과 |
| `training_20260114_170731` | 2026-01-14 17:07:31 | 빌드오더 학습 결과 |
| `training_20260114_175424` | 2026-01-14 17:54:24 | 빌드오더 학습 결과 |
| `training_20260114_213456` | 2026-01-14 21:34:56 | 빌드오더 학습 결과 |
| `training_20260116_174805` | 2026-01-16 17:48:05 | 빌드오더 학습 결과 |
| `training_20260116_175537` | 2026-01-16 17:55:37 | 빌드오더 학습 결과 |
| `training_20260116_204440` | 2026-01-16 20:44:40 | 빌드오더 학습 결과 |
| `training_20260116_212826` | 2026-01-16 21:28:26 | 빌드오더 학습 결과 |
| `training_20260119_092223` | 2026-01-19 09:22:23 | **최신** 빌드오더 학습 결과 |
| `training_20260119_092426` | 2026-01-19 09:24:26 | 빌드오더 학습 결과 |
| `training_20260119_094558` | 2026-01-19 09:45:58 | 빌드오더 학습 결과 |
| `training_20260119_094610` | 2026-01-19 09:46:10 | **최신** 빌드오더 학습 결과 |

### 파일 종류

#### 1. `learned_build_orders.json` (가장 중요)

**위치**: 각 training 폴더 내부

**내용**: 프로게이머 리플레이에서 학습된 빌드오더 파라미터

**예시 구조**:
```json
{
  "learned_parameters": {
    "gas_supply": 17.0,
    "spawning_pool_supply": 17.0,
    "natural_expansion_supply": 31.0,
    "lair_supply": 12.0,
    "roach_warren_supply": 54.0,
    "hive_supply": 12.0,
    "hydralisk_den_supply": 124.0
  },
  "source_replays": 43,
  "replay_directory": "D:\\replays\\replays",
  "build_orders": [...]
}
```

**용도**:
- 게임 훈련 시 자동 적용
- `config.py`의 `get_learned_parameter()` 함수가 자동 읽기
- 프로게이머 수준의 빌드오더 타이밍 적용

#### 2. `instance_*_status.json` (일부 폴더에만 존재)

**위치**: `training_20260113_085621` 등 일부 폴더

**내용**: 학습 인스턴스 상태 정보

**용도**: 병렬 학습 시 각 인스턴스 상태 추적

#### 3. `supervised_training_stats.json` (일부 폴더에만 존재)

**위치**: `training_20260113_085621` 등 일부 폴더

**내용**: 감독 학습 통계 데이터

**크기**: 약 25KB

**용도**: 학습 진행 상황 추적

## 디렉토리 용도

### 아카이브 목적

각 `training_YYYYMMDD_HHMMSS` 폴더는 **빌드오더 학습 세션의 결과**를 저장합니다:

1. **타임스탬프별 저장**: 각 학습 실행마다 새로운 폴더 생성
2. **이력 관리**: 과거 학습 결과 추적 가능
3. **비교 분석**: 시간에 따른 학습 진행 상황 비교

### 최신 학습 결과

**최신 폴더**: `training_20260119_094610` (2026-01-19 09:46:10)

**최신 학습 결과**:
- 7개 빌드오더 파라미터 학습 완료
- 파일 크기: 7.19KB
- 저장 위치: `D:\replays\archive\training_20260119_094610\learned_build_orders.json`

## 주요 특징

### 파일 구조

```
D:\replays\archive\
├── training_20260113_011452\
│   └── learned_build_orders.json
├── training_20260113_085621\
│   ├── instance_0_status.json
│   ├── instance_1_status.json
│   ├── instance_2_status.json
│   ├── supervised_training_stats.json
│   └── learned_build_orders.json (없을 수도 있음)
├── training_20260114_162547\
│   └── learned_build_orders.json
├── ...
└── training_20260119_094610\ (최신)
    └── learned_build_orders.json
```

### 파일 크기

- `learned_build_orders.json`: 3-7KB (학습된 파라미터 수에 따라 변동)
- 최신 파일: 7.19KB (7개 파라미터 포함)

### 자동 적용

**최신 학습 결과가 자동으로 적용되는 방법:**

1. `replay_build_order_learner.py` 실행
2. 학습 완료 시 `training_YYYYMMDD_HHMMSS\learned_build_orders.json` 저장
3. **동시에** `local_training/scripts/learned_build_orders.json`에도 복사
4. `config.py`의 `get_learned_parameter()`가 자동 읽기
5. 게임에서 자동 적용

## 사용 방법

### 최신 학습 결과 확인

```python
from pathlib import Path
import json

# 최신 폴더 찾기
archive_dir = Path("D:/replays/archive")
latest_training = max(archive_dir.glob("training_*"), key=lambda x: x.stat().st_mtime)

# 학습 결과 읽기
learned_file = latest_training / "learned_build_orders.json"
if learned_file.exists():
    with open(learned_file, 'r', encoding='utf-8') as f:
        learned_data = json.load(f)
    print(f"Latest learning: {latest_training.name}")
    print(f"Parameters: {learned_data.get('learned_parameters', {})}")
```

### 모든 학습 결과 비교

```python
from pathlib import Path
import json

archive_dir = Path("D:/replays/archive")
for training_folder in sorted(archive_dir.glob("training_*")):
    learned_file = training_folder / "learned_build_orders.json"
    if learned_file.exists():
        data = json.load(open(learned_file, encoding='utf-8'))
        params = data.get('learned_parameters', {})
        print(f"{training_folder.name}: {len(params)} parameters")
```

## 정리 방안

### 오래된 폴더 삭제 (선택사항)

17개의 폴더가 많으면 최근 N개만 유지 가능:

```python
from pathlib import Path

archive_dir = Path("D:/replays/archive")
folders = sorted(archive_dir.glob("training_*"), key=lambda x: x.stat().st_mtime)

# 최근 5개만 유지, 나머지 삭제
for folder in folders[:-5]:
    # folder를 삭제 (주의: 실행 전 확인)
    pass
```

### 중요 파일만 보관

- 각 폴더의 `learned_build_orders.json`만 보관
- 상태 파일(`instance_*_status.json` 등)은 삭제 가능

---

## 요약

- **17개 training 폴더**: 각 학습 세션 결과 저장
- **주요 파일**: `learned_build_orders.json` (빌드오더 파라미터)
- **최신 학습**: `training_20260119_094610` (2026-01-19 09:46:10)
- **자동 적용**: 최신 결과가 `local_training/scripts/learned_build_orders.json`으로 복사되어 게임에 자동 적용
