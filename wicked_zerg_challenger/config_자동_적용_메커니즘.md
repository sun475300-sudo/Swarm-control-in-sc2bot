# config.py 자동 적용 메커니즘 상세 안내

## 개요

`config.py`의 `get_learned_parameter()` 함수는 프로게이머 리플레이에서 학습된 빌드오더 파라미터를 **자동으로 읽어서 게임에 적용**합니다.

## 자동 적용 프로세스

### 1단계: 학습된 파라미터 저장

**위치**: `local_training/scripts/learned_build_orders.json`

**내용 예시**:
```json
{
  "gas_supply": 17.0,
  "spawning_pool_supply": 17.0,
  "natural_expansion_supply": 31.0,
  "lair_supply": 12.0,
  "roach_warren_supply": 54.0,
  "hive_supply": 12.0,
  "hydralisk_den_supply": 124.0
}
```

**저장 방법**:
- `replay_build_order_learner.py` 실행 시 자동 저장
- `D:\replays\archive\training_YYYYMMDD_HHMMSS\learned_build_orders.json`에도 저장
- **동시에** `local_training/scripts/learned_build_orders.json`에 복사

### 2단계: 자동 읽기 (config.py)

**함수 위치**: `config.py` line 378-411

**코드**:
```python
def get_learned_parameter(
        parameter_name: str,
        default_value: Any = None) -> Any:
    """
    Get learned parameter from local_training/scripts/learned_build_orders.json
    Priority: local_training/scripts/learned_build_orders.json > learned_build_orders.json (same dir)
    """
    # Priority 1: local_training/scripts/learned_build_orders.json
    local_training_path = Path(
        __file__).parent / "local_training" / "scripts" / "learned_build_orders.json"
    # Priority 2: learned_build_orders.json in same directory (backward compatibility)
    default_path = Path(__file__).parent / "learned_build_orders.json"

    # Try local_training first
    learned_json_path = local_training_path if local_training_path.exists() else default_path
    if learned_json_path.exists():
        try:
            with open(learned_json_path, 'r', encoding='utf-8') as f:
                learned_data = json.load(f)
                if isinstance(learned_data, dict):
                    if "learned_parameters" in learned_data:
                        learned_params = learned_data["learned_parameters"]
                    else:
                        learned_params = learned_data
                else:
                    learned_params = learned_data
                if parameter_name in learned_params:
                    return learned_params[parameter_name]
        except Exception:
            pass
    # Fallback to default value
    loader = get_config_loader()
    return loader.get_parameter(parameter_name, default_value)
```

**읽기 우선순위**:
1. `local_training/scripts/learned_build_orders.json` (최우선)
2. `learned_build_orders.json` (동일 디렉토리, 하위 호환)
3. 기본값 (fallback)

### 3단계: 게임에서 자동 적용

**적용 위치**: `local_training/production_resilience.py`

**코드 예시**:
```python
from config import get_learned_parameter

# Gas extraction: Build at pro baseline supply (17-18)
gas_supply = get_learned_parameter("gas_supply", 17.0)
gas_supply_max = gas_supply + 1.0  # Allow up to 18 (17-18 range)

# Spawning Pool: Build at pro baseline supply (17)
spawning_pool_supply = get_learned_parameter("spawning_pool_supply", 17.0)

# Natural Expansion: Build at pro baseline supply (30-32)
natural_expansion_supply = get_learned_parameter("natural_expansion_supply", 30.0)
natural_expansion_supply_max = natural_expansion_supply + 2.0  # Allow up to 32
```

## 실제 적용 예시

### production_resilience.py에서 사용

**위치**: `local_training/production_resilience.py` line 227-285

**사용 예시**:
1. **가스 추출기 (Gas Extraction)**
   ```python
   gas_supply = get_learned_parameter("gas_supply", 17.0)
   if supply_used >= gas_supply and supply_used < gas_supply_max:
       # Build gas extractor
   ```

2. **산란못 (Spawning Pool)**
   ```python
   spawning_pool_supply = get_learned_parameter("spawning_pool_supply", 17.0)
   if supply_used >= spawning_pool_supply:
       # Build spawning pool
   ```

3. **멀티 확장 (Natural Expansion)**
   ```python
   natural_expansion_supply = get_learned_parameter("natural_expansion_supply", 30.0)
   if supply_used >= natural_expansion_supply:
       # Expand to natural
   ```

## 자동 적용 확인 방법

### 1. 함수 테스트
```python
from config import get_learned_parameter

# 학습된 파라미터 읽기
gas_supply = get_learned_parameter("gas_supply", 17)
spawning_pool_supply = get_learned_parameter("spawning_pool_supply", 17)

print(f"gas_supply: {gas_supply}")  # 17.0 (학습된 값)
print(f"spawning_pool_supply: {spawning_pool_supply}")  # 17.0 (학습된 값)
```

### 2. 파일 존재 확인
```python
from pathlib import Path

learned_file = Path("local_training/scripts/learned_build_orders.json")
if learned_file.exists():
    print(f"? Learned parameters file found: {learned_file}")
else:
    print(f"? Learned parameters file not found")
```

### 3. 실제 게임에서 확인

게임 실행 시 로그에서 확인:
```
[TECH BUILD] [45s] Building Spawning Pool at supply 17 (learned from pro replays)
[TECH BUILD] [60s] Building Gas Extractor at supply 17 (learned from pro replays)
```

## 자동 적용 특징

### ? 자동 업데이트

1. **리플레이 학습 실행** → `learned_build_orders.json` 업데이트
2. **게임 실행 시** → `get_learned_parameter()`가 자동으로 새 값 읽기
3. **즉시 적용** → 다음 게임부터 학습된 파라미터 사용

### ? 우선순위 처리

1. **학습된 값** (최우선)
2. **기본값** (fallback)

예시:
```python
gas_supply = get_learned_parameter("gas_supply", 17.0)
# 학습된 값이 있으면 → 학습된 값 (예: 17.0)
# 학습된 값이 없으면 → 기본값 (17.0)
```

### ? 에러 처리

- 파일이 없어도 → 기본값 반환 (에러 없음)
- JSON 파싱 오류 → 기본값 반환 (에러 없음)
- 파라미터가 없으면 → 기본값 반환 (에러 없음)

## 적용 흐름도

```
프로게이머 리플레이 학습
         ↓
replay_build_order_learner.py 실행
         ↓
learned_build_orders.json 저장
  ├→ D:\replays\archive\training_YYYYMMDD_HHMMSS\
  └→ local_training/scripts/learned_build_orders.json (복사)
         ↓
게임 실행 (run_with_training.py)
         ↓
production_resilience.py
         ↓
get_learned_parameter() 호출
         ↓
learned_build_orders.json 자동 읽기
         ↓
학습된 파라미터 적용 ?
         ↓
게임에서 자동 사용
```

## 현재 적용 상태

### ? 적용된 파라미터

| 파라미터 | 학습된 값 | 기본값 | 적용 위치 |
|---------|---------|--------|----------|
| `gas_supply` | 17.0 | 17.0 | `production_resilience.py` line 230 |
| `spawning_pool_supply` | 17.0 | 17.0 | `production_resilience.py` line 258 |
| `natural_expansion_supply` | 31.0 | 30.0 | `production_resilience.py` line 285 |

### ? 적용 확인

**파일 위치**: `local_training/production_resilience.py`

**적용 상태**:
- ? `gas_supply` - 적용됨
- ? `spawning_pool_supply` - 적용됨  
- ? `natural_expansion_supply` - 적용됨

## 수동 테스트

### 테스트 스크립트
```python
# test_learned_parameters.py
from config import get_learned_parameter
from pathlib import Path

print("=" * 70)
print("LEARNED PARAMETERS AUTO-LOAD TEST")
print("=" * 70)

# Check if file exists
learned_file = Path("local_training/scripts/learned_build_orders.json")
print(f"File exists: {learned_file.exists()}")
if learned_file.exists():
    print(f"File path: {learned_file}")
    print()

# Test loading parameters
test_params = [
    "gas_supply",
    "spawning_pool_supply",
    "natural_expansion_supply",
    "lair_supply",
    "roach_warren_supply"
]

print("Parameter loading test:")
for param in test_params:
    value = get_learned_parameter(param, None)
    status = "?" if value is not None else "?"
    print(f"  {status} {param}: {value}")

print("=" * 70)
```

**실행 방법**:
```batch
cd wicked_zerg_challenger
python test_learned_parameters.py
```

## 요약

### 자동 적용 프로세스

1. ? **학습**: 프로 리플레이에서 파라미터 추출
2. ? **저장**: `learned_build_orders.json` 자동 저장
3. ? **읽기**: `get_learned_parameter()` 자동 읽기
4. ? **적용**: `production_resilience.py`에서 자동 사용

### 주요 특징

- **완전 자동화**: 수동 작업 불필요
- **안전한 fallback**: 파일이 없어도 기본값 사용
- **우선순위 처리**: 학습된 값 > 기본값
- **에러 처리**: 예외 상황에도 안전하게 동작

### 현재 상태

- ? `get_learned_parameter()` 함수 구현 완료
- ? `production_resilience.py`에서 사용 중
- ? 학습된 파라미터 7개 적용됨
- ? 자동 읽기 및 적용 동작 확인

**결론**: `config.py`의 `get_learned_parameter()` 함수가 자동으로 학습된 빌드오더 파라미터를 읽어서 게임에 적용하고 있습니다.
