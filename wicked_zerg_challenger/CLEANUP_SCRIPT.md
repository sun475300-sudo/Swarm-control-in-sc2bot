# local_training/ 폴더 정리 가이드

**주의**: 이 작업은 `local_training/`의 중복 봇 소스코드를 삭제합니다.
**전제 조건**: 루트 폴더에 봇 소스코드가 있어야 합니다 (현재는 없음).

## 삭제 대상 파일 목록

### 봇 소스코드 (삭제)
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

### 가상환경 (삭제)
- `venv/` 폴더

## 유지 대상 파일

### 훈련 스크립트 (유지)
- `main_integrated.py` - 훈련 실행 스크립트 (삭제 금지!)
- `build_order_learner.py` - 빌드 오더 학습기
- `curriculum_manager.py` - 커리큘럼 학습
- `scripts/` 폴더 - 훈련 관련 스크립트

### 데이터 폴더 (유지)
- `data/`
- `models/`
- `logs/`
- `stats/`
- `replays/`

---

**현재 상태**: 루트에 봇 소스코드가 없으므로 삭제 전 확인 필요
