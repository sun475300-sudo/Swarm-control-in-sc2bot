# ?? 중요: local_training/ 폴더 정리 전 주의사항

**작성 일시**: 2026-01-14  
**상태**: ?? **삭제 전 확인 필요**

---

## ? 중요한 문제

### 현재 상황
- **루트 폴더에 봇 소스코드가 없습니다**
- `run.py`가 루트의 `wicked_zerg_bot_pro`를 import합니다
- `local_training/main_integrated.py`가 루트의 봇을 참조하도록 수정되었습니다

### 문제점
**`local_training/`의 봇 소스코드를 삭제하면:**
1. `run.py`가 실행되지 않습니다 (루트에 `wicked_zerg_bot_pro.py`가 없음)
2. `local_training/main_integrated.py`가 실행되지 않습니다 (루트에 봇 소스코드가 없음)

---

## ? 삭제 대상 파일

### 봇 소스코드 (삭제 대상)
- `wicked_zerg_bot_pro.py`
- `combat_manager.py`
- `combat_tactics.py`
- `economy_manager.py`
- `intel_manager.py`
- `production_manager.py`
- `production_resilience.py`
- `queen_manager.py`
- `scouting_system.py`
- `micro_controller.py`
- `personality_manager.py`
- `map_manager.py`
- `unit_factory.py`
- `telemetry_logger.py`
- `zerg_net.py`
- `config.py`

### 가상환경 (삭제 대상)
- `venv/` 폴더 (이미 .gitignore에 포함되어 있음)

---

## ? 유지 대상 파일

### 훈련 스크립트 (유지)
- **`main_integrated.py`** - 훈련 실행 스크립트 (삭제 금지!)
- `build_order_learner.py` - 빌드 오더 학습기
- `curriculum_manager.py` - 커리큘럼 학습
- `scripts/` 폴더 - 훈련 관련 스크립트

---

## ? 해결 방안

### 옵션 1: 루트로 파일 이동 후 삭제 (권장)
1. `local_training/`의 봇 소스코드를 루트로 복사/이동
2. `local_training/`의 중복 파일 삭제

### 옵션 2: 현재 상태 유지
- 루트에 봇 소스코드를 생성한 후 삭제 진행

---

**권장 사항**: 루트 폴더에 봇 소스코드를 생성한 후 삭제 작업을 진행하세요.
