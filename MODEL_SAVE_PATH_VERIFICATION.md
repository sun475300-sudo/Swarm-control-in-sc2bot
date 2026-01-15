# 모델 저장 경로 검증 보고서

**작성일**: 2026-01-15  
**목적**: 학습 후 신경망 모델이 저장되는 경로 확인 및 검증

---

## ? 검증 결과 요약

### 모델 저장 경로: `local_training/models/` ? **맞습니다**

**확인된 경로**:
- **우선 경로**: `wicked_zerg_challenger/local_training/models/`
- **대체 경로**: `wicked_zerg_challenger/models/` (local_training/models/가 없을 때만)

---

## ? 코드 분석 결과

### 1. **zerg_net.py - 모델 저장 경로 설정**

**위치**: `wicked_zerg_challenger/zerg_net.py` (line 41-54)

```python
# Model storage directory - Priority: local_training/models/ > wicked_zerg_challenger/models/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Try local_training/models/ first (where training saves models)
LOCAL_TRAINING_MODELS_DIR = os.path.join(SCRIPT_DIR, "local_training", "models")
# Fallback to current directory models/
DEFAULT_MODELS_DIR = os.path.join(SCRIPT_DIR, "models")

# Use local_training/models/ if it exists, otherwise use default
if os.path.exists(LOCAL_TRAINING_MODELS_DIR):
    MODELS_DIR = LOCAL_TRAINING_MODELS_DIR
    print(f"[MODEL] Using local_training/models/ directory: {MODELS_DIR}")
else:
    MODELS_DIR = DEFAULT_MODELS_DIR
    print(f"[MODEL] Using default models/ directory: {MODELS_DIR}")
```

**결과**:
- ? `local_training/models/` 디렉토리가 존재하면 우선 사용
- ? 존재하지 않으면 `wicked_zerg_challenger/models/` 사용

---

### 2. **zerg_net.py - save_model() 메서드**

**위치**: `wicked_zerg_challenger/zerg_net.py` (line 470-535)

```python
def save_model(self):
    """
    Save model (with file locking handling)
    """
    max_retries = 5
    retry_delay = 0.5

    for attempt in range(max_retries):
        try:
            # IMPROVED: Save to local_training/models/ for consistency with training
            # Ensure we're saving to local_training/models/ if it exists
            if "local_training" not in self.model_path:
                local_training_models = os.path.join(SCRIPT_DIR, "local_training", "models")
                if os.path.exists(local_training_models) or os.path.exists(os.path.dirname(local_training_models)):
                    model_name = os.path.basename(self.model_path)
                    self.model_path = os.path.join(local_training_models, model_name)
                    print(f"[MODEL] Saving to local_training/models/: {self.model_path}")
            
            # Create model directory if it doesn't exist
            model_dir = os.path.dirname(self.model_path)
            if model_dir:
                os.makedirs(model_dir, exist_ok=True)

            # Temporary file path (for atomic saving)
            temp_path = self.model_path + ".tmp"

            # Step 1: Save to temporary file
            torch.save(self.model.state_dict(), temp_path)

            # Step 2: Move to original file (atomic operation)
            # ... (backup and atomic replacement logic)
            
            print(f"[OK] Model saved: {self.model_path}")
            return
```

**결과**:
- ? `local_training/models/` 디렉토리가 존재하면 자동으로 해당 경로로 저장
- ? 모델 경로에 `local_training`이 없으면 자동으로 `local_training/models/`로 변경
- ? 디렉토리가 없으면 자동 생성 (`os.makedirs(model_dir, exist_ok=True)`)

---

### 3. **zerg_net.py - _load_model() 메서드**

**위치**: `wicked_zerg_challenger/zerg_net.py` (line 282-361)

```python
def _load_model(self):
    """
    Load model if saved (with file locking handling)
    Priority: local_training/models/ > default models/
    """
    # Priority 1: local_training/models/ (where training saves)
    local_training_model_path = os.path.join(SCRIPT_DIR, "local_training", "models", os.path.basename(self.model_path))
    # Priority 2: current directory models/ (backward compatibility)
    default_model_path = os.path.join(SCRIPT_DIR, "models", os.path.basename(self.model_path))

    # Determine which path to try first
    paths_to_try = []
    if os.path.exists(local_training_model_path):
        paths_to_try.append(local_training_model_path)
    if os.path.exists(default_model_path) and default_model_path not in paths_to_try:
        paths_to_try.append(default_model_path)
```

**결과**:
- ? 모델 로드 시 `local_training/models/`를 우선 확인
- ? 없으면 `wicked_zerg_challenger/models/` 확인

---

## ? 실제 디렉토리 구조

### 현재 상태

```
wicked_zerg_challenger/
├── local_training/
│   ├── models/                    ? 존재함 (생성 완료)
│   │   └── (모델 파일 저장 위치)
│   └── scripts/
│       └── learned_build_orders.json
├── models/                        ? 존재함 (대체 경로)
│   └── (대체 모델 저장 위치)
└── zerg_net.py                    (모델 저장/로드 로직)
```

---

## ? 모델 저장/로드 흐름

### 저장 흐름

1. **게임 실행 중**:
   - `ReinforcementLearner` 인스턴스 생성
   - `MODELS_DIR` 확인: `local_training/models/` 우선 사용
   - 모델 경로 설정: `local_training/models/zerg_net_model.pt` (또는 `zerg_net_model_{instance_id}.pt`)

2. **모델 저장 시** (`save_model()` 호출):
   - `local_training/models/` 디렉토리 확인
   - 없으면 자동 생성
   - 임시 파일로 저장 후 원자적 교체 (atomic operation)
   - 저장 완료: `local_training/models/zerg_net_model.pt`

### 로드 흐름

1. **게임 시작 시**:
   - `_load_model()` 호출
   - 우선 순위 1: `local_training/models/zerg_net_model.pt`
   - 우선 순위 2: `wicked_zerg_challenger/models/zerg_net_model.pt`
   - 모델 파일이 있으면 로드, 없으면 새 모델 생성

---

## ? 검증 체크리스트

### 경로 설정 확인

- [x] `LOCAL_TRAINING_MODELS_DIR` 경로: `wicked_zerg_challenger/local_training/models/`
- [x] `DEFAULT_MODELS_DIR` 경로: `wicked_zerg_challenger/models/`
- [x] `local_training/models/` 디렉토리 존재 확인: ? **존재함**
- [x] `wicked_zerg_challenger/models/` 디렉토리 존재 확인: ? **존재함**

### 저장 로직 확인

- [x] `save_model()` 메서드가 `local_training/models/`로 저장하도록 설정됨
- [x] 디렉토리 자동 생성 로직 포함 (`os.makedirs(model_dir, exist_ok=True)`)
- [x] 원자적 저장 로직 포함 (임시 파일 + 원자적 교체)

### 로드 로직 확인

- [x] `_load_model()` 메서드가 `local_training/models/`를 우선 확인
- [x] 대체 경로(`wicked_zerg_challenger/models/`) 지원

---

## ? 결론

### ? **모델 저장 경로가 올바르게 설정되어 있습니다**

1. **우선 경로**: `wicked_zerg_challenger/local_training/models/` ?
2. **대체 경로**: `wicked_zerg_challenger/models/` ?
3. **자동 생성**: 디렉토리가 없으면 자동 생성 ?
4. **일관성**: 저장과 로드 모두 동일한 경로 우선순위 사용 ?

### ? 참고 사항

- **게임 실행 시**: 모델이 `local_training/models/`에 저장됨
- **학습 파이프라인 실행 시**: 모델이 `local_training/models/`에 저장됨
- **모델 로드 시**: `local_training/models/`를 우선 확인

---

**검증 완료**: ? **모델 저장 경로가 `local_training/models/`로 올바르게 설정되어 있습니다**
