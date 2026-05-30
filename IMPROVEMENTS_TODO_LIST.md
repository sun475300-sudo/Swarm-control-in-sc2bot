# SC2 지휘관봇 개선사항 대규모 목록

> 생성: 2026-05-30 · 브랜치: `claude/cool-edison-vkR4d`
> 출처: 반복 테스트 + 코드 점검 결과
> 진행 방식: Round 단위로 항목 처리 → commit → push → 다음 라운드
> 진행 현황: R1~R7 완료 (커밋 63ae827, 3a64102, 8271dbf, 90ef660, a4c3938, e74eb59)

## Round 1 — 테스트 인프라 복구 (BLOCKER)

### R1.1 — `test_queen_transfusion.py` 컬렉션 에러 ❌
- **증상**: `pytest tests/` 실행 시 `ModuleNotFoundError: No module named 'sc2'` 로 전체 컬렉션이 1 error로 중단
- **원인**: 모듈 최상위에서 `from sc2.ids.unit_typeid import UnitTypeId` 직접 import
- **수정**: 다른 테스트(test_advanced_scout_system_v2 등)와 같이 try/except + `pytest.skip(..., allow_module_level=True)` 적용
- **검증**: `pytest tests/ --collect-only` 가 error 없이 완료

### R1.2 — `test_combat_phase_fsm.py` 이벤트 루프 12 fail ❌
- **증상**: 단독 실행하면 23 pass, 전체 스위트에서 실행하면 12 fail (`RuntimeError: There is no current event loop in thread 'MainThread'`)
- **원인**: 5곳에서 `asyncio.get_event_loop().run_until_complete(...)` deprecated 패턴 사용 — pytest-asyncio가 이전 테스트에서 루프를 닫은 후 발생
- **수정**: `asyncio.get_event_loop()` 을 `asyncio.new_event_loop()` 또는 `asyncio.run(...)`으로 교체
- **검증**: 전체 스위트에서 0 fail 유지

### R1.3 — pytest 의존성 가시화
- **증상**: pytest-asyncio가 uv tool 환경에 없어 async 테스트 70+ 개가 모두 fail (해결됨)
- **수정**: requirements*.txt / pyproject.toml 에 `pytest-asyncio`, `pytest-timeout` 명시 (이미 있으면 OK)

## Round 2 — 추가 테스트 인프라

### R2.1 — `wicked_zerg_challenger/tests/test_production_resilience.py` 동일 패턴
- 388번 줄 `asyncio.get_event_loop()` 잔재 — 사이드 이펙트 점검

### R2.2 — `test_queen_transfusion_manager.py` 등 다른 sc2 import 점검
- 일부는 이미 try/except 있음 — 누락 모듈 전수조사

### R2.3 — 미스킵된 테스트 경로
- `tests/test_spatial_query_optimizer.py` 의 sc2.position import 패턴 일관성 확인

## Round 3 — 코드 품질 / 핵심 봇

### R3.1 — `wicked_zerg_challenger/local_training/advanced_building_manager.py:778` TODO 처리
### R3.2 — `wicked_zerg_challenger/scouting/phase_scout_cadence.py` PLAN-NIGHTLY P1.1 TODO 추적
### R3.3 — 봇 핵심 모듈 (combat_manager, economy_manager, opponent_modeling) lint warning 스윕

## Round 4 — CI / 빌드 최적화

### R4.1 — `pytest.ini` `asyncio_mode=auto` 가 이미 설정됨 — pytest-asyncio 의존 강화
### R4.2 — coverage threshold (`--cov-fail-under=70`) 도입 검토
### R4.3 — 의존성 lockfile 도입 (pip-tools)

## 작업 규칙
- 각 Round 완료 시 commit & push
- 회귀 방지: 변경 후 즉시 `pytest tests/ -q` 로 검증
- main에 직접 push 금지 — `claude/cool-edison-vkR4d` 만 사용
- PR은 사용자 검토 대기 (자동 머지 금지)

---

## 진행 현황 요약 (R1 → R7)

### R1 — pytest 컬렉션 + 이벤트 루프 (✅ 완료, 63ae827)
- test_queen_transfusion.py 의 sc2 import 가드 추가
- test_combat_phase_fsm.py 의 5곳 `asyncio.get_event_loop()` → `new_event_loop()` 교체
- 결과: 1 collection error → 0, 395 passed

### R2/R3 — 테스트 black 포맷 + bot core F821 8건 (✅ 완료, 3a64102)
- tests/test_combat_phase_fsm.py + tests/test_queen_transfusion.py black 포맷 적용
- unit_factory.py:91, 439 mojibake 가 코드 한 줄을 주석으로 삼킨 2곳 분리
- production_resilience.py:1447 정의되지 않은 `game_time` 추가
- 결과: F821 8건 → 0건, 428 passed

### R4 — wicked_zerg_challenger/tests/ sc2 미가용 환경 자동 skip (✅ 완료, 8271dbf)
- `pytest_ignore_collect` 훅으로 sc2 의존 테스트 안전 skip
- 결과: 23 collection errors → 0 (sc2 미가용 시 skip, 가용 시 정상 실행)

### R5 — F811 중복 정의 5건 제거 (✅ 완료, 90ef660)
- combat_manager.py `_find_harass_target` (2815→dead)
- economy_manager.py `_prevent_resource_banking` (1708→dead) + `_reduce_gas_workers` (3419→dead)
- production_resilience.py `build_terran_counters` (1462→dead)
- **opponent_modeling.py `on_step` (765→stub; 341→comprehensive 복구)** — 가장 영향 큰 수정. opponent modeling이 ~15% 기능만 동작했던 회귀를 풀어냄 (build order/timing attack/tech progression/blackboard publish 등 5개 파이프라인 복구)

### R6 — current_opponent → current_opponent_id 명명 통일 (✅ 완료, a4c3938)
- opponent_modeling.py 의 4개 사이트 + wicked_zerg_bot_pro_impl.py 의 3개 사이트
- R5 가 추가했던 `current_opponent: Optional[str] = None` 도 제거 (정식 이름 사용)

### R7 — R5 잔재 빈 줄 정리 (✅ 완료, e74eb59)
- E303 3건

---

## 다음 라운드 후보 (R8+)

### R8 — IMPROVEMENT_RECOMMENDATIONS.md 정렬 + TODO/FIXME 티켓화
- `wicked_zerg_challenger/local_training/advanced_building_manager.py:778` TODO
- `wicked_zerg_challenger/tools/check_missing_logic.py` 6 TODO

### R9 — 47건 unused-exception-binding 정리
- `except X as e:` 인데 e가 본문에서 안 쓰이는 47곳 → `except X:` 로 단순화
- 가장 많은 파일: bot_step_integration.py (11+)

### R10 — F841 죽은 변수 24건 점검
- 일부는 미완성 로직의 흔적 (e.g. upgrade_manager.py:361 `race_modifiers`)
- 각 항목마다 "구현 누락" vs "단순 dead code" 분류 후 처리

### R11 — Mojibake 주석 일괄 복원/단순화
- 한국어 주석이 cp949/utf-8 사이에서 깨진 흔적 다수
- 이 자체로 봇이 작동하지만 가독성/유지보수 저해

### R12 — 봇 핵심 모듈 README 보강 (combat / economy / opponent_modeling)

