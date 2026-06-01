# 지휘관봇 - 테스트/점검 기반 개선 목록 (Backlog)

테스트 실행 결과를 기반으로 한 우선순위별 개선 항목입니다.

## 현황 (Baseline)
- 전체 423 tests collected, 33 skipped
- **12 failed**: `tests/test_combat_phase_fsm.py` (asyncio event-loop 충돌)
- **1 collection error**: `tests/test_queen_transfusion.py` (sc2 import 충돌)
- **383 passed**

---

## P0 (Critical - 즉시 수정)

### [P0-1] test_combat_phase_fsm.py — 폐기된 `asyncio.get_event_loop()` 사용
- **증상**: pytest-asyncio 가 이전 async 테스트의 이벤트 루프를 닫은 뒤, 동기 테스트에서 `asyncio.get_event_loop()` 호출 시 `RuntimeError: There is no current event loop in thread 'MainThread'`
- **위치**: lines 283, 326, 360, 393, 436 (5곳)
- **수정**: `asyncio.new_event_loop()` + `run_until_complete()` + `close()` 패턴 또는 `asyncio.run()` 으로 교체

### [P0-2] test_queen_transfusion.py — 모듈 레벨에서 sc2 import → 컬렉션 실패
- **증상**: `ModuleNotFoundError: No module named 'sc2'` 시 전체 컬렉션 중단
- **위치**: top-level `from sc2.ids.unit_typeid import UnitTypeId`
- **수정**: `test_combat_phase_fsm.py` 처럼 try/except + `pytest.skip(..., allow_module_level=True)` 가드

---

## P1 (High - 다음 라운드)

### [P1-1] test_queen_transfusion_manager.py — 동일한 sc2 import 패턴 점검
### [P1-2] test_harassment_coordinator.py — sc2 import 가드 점검
### [P1-3] test_advanced_scout_system_v2.py — sc2 import 가드 점검
### [P1-4] test_spatial_query_optimizer.py — sc2 import 가드 점검
### [P1-5] wicked_zerg_challenger/tests/test_production_resilience.py:388 — 폐기된 `asyncio.get_event_loop()`

---

## P2 (Medium)

- pytest 의존성을 `requirements-dev.txt` 에 명시 (pytest-asyncio, pytest-timeout)
- conftest.py 에 sc2 모듈 부재 시 skip 마커 정의 (`@pytest.mark.requires_sc2`)
- CI/SessionStart hook 에서 누락된 의존성 자동 설치
- 33개 skip 사유 정리: `skip-reason` 로깅 추가

---

## P3 (Low / 후속 라운드)

- 33 skipped 테스트 — skip 원인 분류 및 가능한 것 활성화
- 테스트 커버리지 측정 (`pytest-cov` 도입)
- 느린 테스트 식별 (`pytest --durations=20`) 후 분리/최적화

---

## 진행 로그

### Round 1 ✅
- [x] **P0-1** `test_combat_phase_fsm.py` — `asyncio.get_event_loop()` 5곳 → `asyncio.run()`
- [x] **P0-2** `test_queen_transfusion.py` — sc2 import 가드 추가
- 결과: 12 failed → 0 failed, 383 → 395 passed

### Round 2 ✅
- [x] **P1-5** `wicked_zerg_challenger/tests/test_production_resilience.py:388` — `asyncio.get_event_loop()` → `asyncio.run()`
- [x] **P1-6** `tests/test_p606_infra.py` — 존재하지 않는 클래스명(`FuzzTarget`, `ContractViolation`, `PackageType`, `ProfileMetric`)을 실제 export 된 클래스명(`SC2Fuzzer`, `ContractStatus`, `SBOMGenerator`, `SC2Profiler`)으로 교체
- [x] **P2-1** `requirements-dev.txt` 확인 — 이미 `pytest>=7.0.0`, `pytest-asyncio>=0.23.0`, `pytest-timeout>=2.1.0` 포함 (조치 불필요)
- 결과: numpy 설치 시 432 passed, 16 skipped

### Round 3 ✅ (정적 점검)
- [x] **R3-1** `wicked_zerg_challenger/run_single_game.py` 의 UTF-8 BOM 제거 — `# -*- coding: utf-8 -*-` 디렉티브와 BOM 충돌로 `ast.parse` 실패하던 문제 해결
- [x] **R3-2** `src/`, `wicked_zerg_challenger/` 전체 138+ 파일의 AST syntax 점검 — 0 errors
- [x] **R3-3** bare `except:` 없음 확인 (0건)
- [x] **R3-4** mutable default arg / `== None` 패턴 점검 — 0건
- [x] P1-1~P1-4 — 점검 결과 이미 try/except 가드 됨 (조치 불필요)

### 발견된 추가 사항 (Round 4+ 대상)
- **165 empty `except: pass` 블록** (`realtime_awareness_engine.py` 다수) — SC2 API 호출 silent failure 가능성. 단, 봇 특성상 의도적일 수 있어 모듈별 개별 검토 필요.
- 16 skip 잔여:
  - 6: python-sc2 미배포 (환경 의존, 액션 불가)
  - 6: pyupbit 미설치 + 1: pandas 의존 (crypto 모듈, 봇 핵심 아님)
  - 3: config.yaml 부재 (실행 환경 의존)
  - 1: micro_controller (sc2 종속)
