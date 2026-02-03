# Scouting System Cleanup Report

## 문제점 분석

현재 3개의 정찰 시스템이 혼재하여 중복 실행되고 있습니다:

### 1. **scouting_system.py** (구형 - DEPRECATED)
- 오버로드 센서 네트워크 + 저글링 정찰
- 기능: 확장 정찰, 프록시 체크, 희생 정찰
- **상태**: wicked_zerg_bot_pro_impl.py (Line 220)에서 import
- **문제**: 구형 시스템, advanced_scout_system_v2와 기능 중복

### 2. **active_scouting_system.py** (중간 - DEPRECATED)
- 능동형 정찰 시스템, 저글링 주력
- 기능: 동적 정찰 주기, Changeling 관리
- **상태**:
  - wicked_zerg_bot_pro_impl.py (Line 585)에서 import
  - bot_step_integration.py (Line 954)에서 실행
- **문제**: advanced_scout_system_v2와 기능 중복

### 3. **scouting/advanced_scout_system_v2.py** (최신 - ACTIVE)
- Phase 10 구현, Unit Authority Manager 연동
- 기능: 다양한 유닛 사용 (일꾼, 저글링, 대군주, 감시군주+변신수)
- 동적 정찰 주기 (기본 25초, 긴급 15초)
- **상태**: bot_step_integration.py (Line 269, 392, 1014)에서 초기화 및 실행
- **장점**: 가장 발전된 시스템, Unit Authority Manager 연동

## 권장 조치사항

### Phase 1: 구형 시스템 비활성화 ✅
1. `scouting_system.py` → DEPRECATED 표시 추가
2. `active_scouting_system.py` → DEPRECATED 표시 추가
3. wicked_zerg_bot_pro_impl.py에서 import 제거 (주석 처리)

### Phase 2: Advanced Scout System V2만 사용 ✅
- bot_step_integration.py에서 구형 시스템 실행 제거
- advanced_scout_system_v2.py만 실행

### Phase 3: 테스트 및 검증
- 정찰 기능 정상 동작 확인
- Unit Authority Manager 연동 확인
- 메모리 누수 방지 (Line 68-69의 cleanup 로직)

## 구현 완료 항목

✅ DEPRECATED 경고 추가:
- scouting_system.py 파일 상단에 경고 추가
- active_scouting_system.py 파일 상단에 경고 추가

✅ Import 정리:
- wicked_zerg_bot_pro_impl.py의 구형 import 주석 처리

✅ 실행 로직 정리:
- bot_step_integration.py에서 ActiveScoutingSystem 실행 제거

## 최종 아키텍처

```
AdvancedScoutingSystemV2 (scouting/advanced_scout_system_v2.py)
├─ Worker Scout (초반)
├─ Zergling Patrol (주력)
├─ Overlord Scout (속업 후)
└─ Overseer + Changeling (정보 수집)
   └─ Unit Authority Manager 연동 (충돌 방지)
```

## 제거 가능 파일 (Optional)

향후 완전히 제거 가능한 파일들:
- `scouting_system.py` (구형)
- `active_scouting_system.py` (중간형)

**주의**: 제거 전 advanced_scout_system_v2.py가 모든 기능을 커버하는지 확인 필요!

---

**생성일**: 2026-02-03
**작성자**: Claude Code
**상태**: ✅ Cleanup 완료
