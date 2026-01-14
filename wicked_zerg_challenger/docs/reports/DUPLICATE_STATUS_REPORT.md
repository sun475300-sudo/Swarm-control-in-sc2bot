# 중복 파일 상태 리포트

**작성 일시**: 2026-01-14  
**목적**: 루트와 local_training 간 중복 파일 상태 확인 및 정리 권장사항

---

## ? 현재 상태

### 1. 루트 폴더 (`wicked_zerg_challenger/`)

**모든 필수 Core Logic 파일 존재 확인 (14개):**

- ? `wicked_zerg_bot_pro.py` (메인 실행 파일)
- ? `zerg_net.py` (신경망 모델)
- ? `combat_manager.py`
- ? `economy_manager.py`
- ? `production_manager.py`
- ? `intel_manager.py`
- ? `queen_manager.py`
- ? `scouting_system.py`
- ? `map_manager.py`
- ? `spell_unit_manager.py` (마법 유닛 제어) - **문제 해결됨 ?**
- ? `rogue_tactics_manager.py` (로그 전술) - **문제 해결됨 ?**
- ? `unit_factory.py`
- ? `config.py`
- ? `telemetry_logger.py`

### 2. local_training 폴더

**중복 파일 (12개) - 정리 필요:**

- ?? `wicked_zerg_bot_pro.py` (중복)
- ?? `zerg_net.py` (중복)
- ?? `combat_manager.py` (중복)
- ?? `economy_manager.py` (중복)
- ?? `production_manager.py` (중복)
- ?? `intel_manager.py` (중복)
- ?? `queen_manager.py` (중복)
- ?? `scouting_system.py` (중복)
- ?? `map_manager.py` (중복)
- ?? `unit_factory.py` (중복)
- ?? `config.py` (중복)
- ?? `telemetry_logger.py` (중복)

**유지해야 할 파일 (훈련 스크립트):**

- ? `main_integrated.py` (훈련 메인 스크립트)
- ? `build_order_learner.py` (빌드 오더 학습)
- ? `curriculum_manager.py` (커리큘럼 관리)
- ? `scripts/` 폴더 (훈련 관련 스크립트)
- ? `models/` 폴더 (학습 모델 저장)
- ? `replays/` 폴더 (리플레이 데이터)
- ? `logs/` 폴더 (로그 데이터)

---

## ? 문제점 해결 상태

### 1. ? 핵심 기술의 누락 문제 - **해결됨**

**이전 문제:**
- `spell_unit_manager.py`와 `rogue_tactics_manager.py`가 루트 폴더에 없었음
- 실전(대회, 앱)에서 고급 기술을 사용하지 못함

**현재 상태:**
- ? `spell_unit_manager.py`: 루트에 존재, `wicked_zerg_bot_pro.py`에서 import 확인
- ? `rogue_tactics_manager.py`: 루트에 존재, `wicked_zerg_bot_pro.py`에서 import 확인

**검증:**
```python
# wicked_zerg_bot_pro.py (line 69)
from rogue_tactics_manager import RogueTacticsManager

# wicked_zerg_bot_pro.py (line 712)
from spell_unit_manager import SpellUnitManager
```

### 2. ?? 뇌의 복제 (Code Duplication) 문제 - **정리 필요**

**현재 문제:**
- 루트와 `local_training/`에 동일한 봇 소스코드가 중복 존재 (12개 파일)
- Version Drift 위험: 양쪽 폴더의 코드가 서로 다르게 진화 가능

**영향:**
- 루트 폴더의 버그를 고쳐도 훈련 폴더에는 반영되지 않음
- 훈련 폴더에서 성능을 개선해도 실전 봇은 똑똑해지지 않음

---

## ? 정리 권장사항

### Step 1: local_training의 중복 파일 삭제

**삭제 대상 (12개 파일):**

```bash
local_training/wicked_zerg_bot_pro.py
local_training/zerg_net.py
local_training/combat_manager.py
local_training/economy_manager.py
local_training/production_manager.py
local_training/intel_manager.py
local_training/queen_manager.py
local_training/scouting_system.py
local_training/map_manager.py
local_training/unit_factory.py
local_training/config.py
local_training/telemetry_logger.py
```

### Step 2: 훈련 스크립트 Import 경로 확인

`local_training/main_integrated.py`는 이미 루트의 봇을 참조하도록 수정되어 있습니다:

```python
# main_integrated.py 상단
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from wicked_zerg_bot_pro import WickedZergBotPro as WickedZergBotIntegrated
```

### Step 3: venv 폴더 정리 (선택사항)

- `local_training/venv/` 폴더는 가상환경이므로 Git에 포함되지 않아야 함
- 로컬 개발용이므로 삭제 가능 (필요시 재생성)

---

## ? 다음 단계

1. ? 루트에 필수 파일 복사 완료
2. ? Import 경로 확인 완료
3. ? local_training의 중복 파일 삭제 (대기 중)
4. ? venv 폴더 정리 (선택사항)

---

**생성 일시**: 2026-01-14  
**상태**: 정리 준비 완료
