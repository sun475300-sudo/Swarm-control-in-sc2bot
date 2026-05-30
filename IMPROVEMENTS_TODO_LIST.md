# SC2 지휘관봇 개선사항 대규모 목록

> 생성: 2026-05-30 · 브랜치: `claude/cool-edison-vkR4d`
> 출처: 반복 테스트 + 코드 점검 결과
> 진행 방식: Round 단위로 항목 처리 → commit → push → 다음 라운드

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
