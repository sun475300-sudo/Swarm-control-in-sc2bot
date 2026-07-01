# SC2 지휘관봇 테스트 개선 리스트 (대규모)

테스트 실행 결과 및 점검을 통해 발견된 개선 사항 우선순위 리스트.
실행 환경: Python 3.11.15, pytest 9.0.3, burnysc2 7.3.0, protobuf 3.20.3

## 현재 테스트 현황 (이 PR 기준)

| 항목 | 시작 | 현재 |
| --- | --- | --- |
| 통과 | 462 | **528** |
| 실패 | 21 | **0** |
| 건너뜀 | 14 | 14 |
| 에러 | 19 | **0** |
| 합계 | 516 | 542 |

## 완료된 작업

### P0 - 즉시 수정
- [x] `tests/test_combat_phase_fsm.py` asyncio 이벤트 루프 수정 (`get_event_loop` → `new_event_loop`)
- [x] `wicked_zerg_challenger/scouting/advanced_scout_system_v2.py` 디폴트 인자 (`UnitTypeId.OVERLORD`)
- [x] `tests/test_harassment_coordinator.py` Mock 수정
- [x] `tests/test_combat_phase_fsm.py` 미사용 import 제거

### P1 - 환경 / 의존성
- [x] `requirements.txt`: `protobuf<4`, `loguru`, `scipy` 명시
- [x] `wicked_zerg_challenger/run_single_game.py` UTF-8 BOM 제거
- [x] cryptography PyO3 - cffi 설치 후 해결됨

### P2 - 코드 품질
- [x] `Dict[str, any]` (builtin) → `Dict[str, Any]` (typing) 6개 파일에서 수정
  - advanced_micro_controller_v3.py
  - combat/multitasking.py
  - combat/spatial_query_optimizer.py
  - core/resource_manager.py
  - economy/queen_transfusion_manager.py
  - strategy/adaptive_build_order.py
- [x] `bot.on_step`의 silent `except Exception: pass` → `logger.debug(...)` 변환 (scoring_system, awareness_engine)
- [x] `jarvis_features/workflow_orchestrator.py`: `asyncio.get_event_loop()` → `asyncio.get_running_loop()` (async 함수 내부)
- [x] `expansion_manager.py`: 스카웃 필터 컴프리헨션에서 `townhalls.first.position` 반복 호출 제거 + exists guard 추가

### P3 - 신규 테스트
- [x] `tests/test_bot_on_step_resilience.py` - AST 기반 4개 회귀 락
- [x] `tests/test_typing_annotations.py` - 6개 (annotation `any` → `Any` 락)
- [x] `tests/test_bot_module_imports.py` - 16개 핫패스 모듈 import 스모크
- [x] `tests/test_expansion_timing.py` - 22개 (path setup 추가로 isolation 환경에서도 통과)

## 남은 작업 후보 (다음 단계)

### P4 - 추가 코드 품질
- [ ] 161개의 `except Exception: pass` 패턴 중 hot-path 식별 후 logging으로 전환
- [ ] `run.py:74,78`의 `except (ConnectionAlreadyClosed, Exception)` 중복 (Exception이 부모) 정리
- [ ] `blackboard.get` 후 mutation 패턴 (`completed.append()` + `set`) - 명확화

### P5 - 신규 테스트 커버리지
- [ ] 빌드 오더 회귀 테스트 (build_order_system.py)
- [ ] `_track_build_order` HATCHERY 카운팅 (시작 해처리 포함 여부)
- [ ] `_known_unit_tags` < 22 iteration 라이프타임의 unit_lost 처리
- [ ] queen_transfusion 우선순위 vs 거리 트레이드오프 테스트

### P6 - 빌드/메타
- [ ] CI에 cffi/cryptography 명시
- [ ] dev-only 의존성 분리 (requirements-dev.txt)
- [ ] 다수의 보고서 .md 파일 통합/정리
