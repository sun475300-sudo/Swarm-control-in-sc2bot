# models/ 폴더 설명

**작성 일시**: 2026-01-14  
**목적**: 루트와 local_training의 models 폴더 차이 설명

---

## ? 현재 상태

### 1. 루트 `models/` 폴더

**파일 목록:**
- ? `zerg_net_0.pt`
- ? `zerg_net_model.pt`

**용도:**
- 루트의 `zerg_net.py`를 사용할 때 모델이 저장되는 위치
- 실전 실행 (AI Arena 배포, `run.py` 실행) 시 사용

### 2. `local_training/models/` 폴더

**파일 목록:**
- ? `zerg_net_0.pt`

**용도:**
- `local_training/zerg_net.py`를 사용할 때 모델이 저장되는 위치
- 훈련 실행 (`main_integrated.py` 실행) 시 사용

---

## ? 모델 저장 경로 결정 방식

### `zerg_net.py`의 모델 경로 설정

```python
# zerg_net.py (line 42-43)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(SCRIPT_DIR, "models")
```

**중요:** `MODELS_DIR`은 `zerg_net.py` 파일이 **있는 위치**에 따라 결정됩니다:

- **루트의 `zerg_net.py`** 사용 시:
  ```python
  SCRIPT_DIR = "D:/.../wicked_zerg_challenger"
  MODELS_DIR = "D:/.../wicked_zerg_challenger/models"
  ```

- **`local_training/zerg_net.py`** 사용 시:
  ```python
  SCRIPT_DIR = "D:/.../wicked_zerg_challenger/local_training"
  MODELS_DIR = "D:/.../wicked_zerg_challenger/local_training/models"
  ```

---

## ?? 현재 문제점

### 1. 중복된 `zerg_net.py` 파일

- 루트에 `zerg_net.py` 존재
- `local_training/`에도 `zerg_net.py` 존재
- 각각 다른 `models/` 폴더를 사용

### 2. 모델 파일 분산

- 훈련 시: `local_training/models/`에 저장
- 실전 실행 시: 루트 `models/`에 저장
- 결과: 모델 파일이 두 폴더에 분산

---

## ? 해결 방안

### Option 1: 루트의 models/를 단일 저장소로 통일 (권장)

**장점:**
- Single Source of Truth (SSOT) 원칙 준수
- 모델 파일이 한 곳에 집중
- 훈련과 실전 실행이 같은 모델 사용

**구현 방법:**
1. `zerg_net.py`의 `MODELS_DIR`을 프로젝트 루트로 고정:
   ```python
   # zerg_net.py
   PROJECT_ROOT = Path(__file__).parent.parent if "local_training" in str(Path(__file__).parent) else Path(__file__).parent
   MODELS_DIR = PROJECT_ROOT / "models"
   ```

2. `local_training/zerg_net.py` 삭제 (중복 제거)

### Option 2: local_training/models/를 훈련 전용으로 유지

**장점:**
- 훈련 데이터와 실전 모델 분리
- 실험 모델과 프로덕션 모델 구분

**단점:**
- 모델 파일 분산
- 훈련 후 수동으로 모델 복사 필요

---

## ? 권장 사항

**현재 루트 `models/` 폴더가 비어 보일 수 있는 이유:**

1. **훈련이 `local_training/`에서 실행되어** `local_training/models/`에 저장됨
2. **루트의 `zerg_net.py`가 복사되었지만** 아직 루트에서 훈련이 실행되지 않음
3. **실전 실행 시** 루트 `models/`를 사용하지만, 훈련된 모델이 `local_training/models/`에 있음

**해결책:**

1. ? 루트에 필수 파일 복사 완료 (14개 파일)
2. ? `local_training/`의 중복 파일 정리 (SSOT 원칙)
3. ? `zerg_net.py`의 `MODELS_DIR`을 프로젝트 루트로 통일

---

**생성 일시**: 2026-01-14  
**상태**: 설명 완료
