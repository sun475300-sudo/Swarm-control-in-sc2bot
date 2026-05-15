# SC2 지휘관봇 개선 추적 — 2026-05-15

> 브랜치: `claude/stoic-shannon-RSzB9`
> 환경: sc2/numpy 미설치 (CI/web sandbox와 동일 조건)
> 목적: 테스트 인프라 복구 → 런타임 실패 정리 → 봇 로직 개선의 반복 사이클

## A. 테스트 컬렉션 실패 (27건)

전체 715 tests collected, 27 collection errors.

### A1. `sc2` 모듈 미설치로 인한 직접 임포트 실패 (22건)
다음 파일들이 `from sc2.ids.unit_typeid import UnitTypeId` 등을 try/except 없이 직접 임포트:
- `tests/test_queen_transfusion.py`
- `wicked_zerg_challenger/tests/test_aggressive_strategies_expansion_gate.py`
- `wicked_zerg_challenger/tests/test_build_order_optimizer.py`
- `wicked_zerg_challenger/tests/test_build_order_system.py`
- `wicked_zerg_challenger/tests/test_combat_manager.py`
- `wicked_zerg_challenger/tests/test_creep_expansion_system.py`
- `wicked_zerg_challenger/tests/test_defense_coordinator_expansion_gate.py`
- `wicked_zerg_challenger/tests/test_difficulty_progression.py`
- `wicked_zerg_challenger/tests/test_economy_manager.py`
- `wicked_zerg_challenger/tests/test_opponent_modeling.py`
- `wicked_zerg_challenger/tests/test_production_controller.py`
- `wicked_zerg_challenger/tests/test_production_resilience.py`
- `wicked_zerg_challenger/tests/test_proxy_hatchery_expansion_gate.py`
- `wicked_zerg_challenger/tests/test_resource_manager_expansion_gate.py`
- `wicked_zerg_challenger/tests/test_smart_resource_balancer.py`
- `wicked_zerg_challenger/tests/test_sprint6_rl_pipeline.py`
- `wicked_zerg_challenger/tests/test_sprint8_qa.py`
- `wicked_zerg_challenger/tests/test_strict_upgrade_priority.py`
- `wicked_zerg_challenger/tests/test_tech_coordinator_expansion.py`
- `wicked_zerg_challenger/tests/test_upgrade_manager_expansion_reserve.py`
- `wicked_zerg_challenger/tests/test_worker_harassment_defense.py`

### A2. `numpy` 미설치로 인한 임포트 실패 (3건)
- `wicked_zerg_challenger/tests/test_actor_critic.py`
- `wicked_zerg_challenger/tests/test_observation_space.py`

### A3. `Blackboard` symbol 누락 (1건)
- `wicked_zerg_challenger/tests/test_blackboard.py` — `blackboard.py`에 `Blackboard` alias 없음 (`GameStateBlackboard`만 존재)

### A4. `UnitTypeId.OVERLORD` 누락 (1건)
- `wicked_zerg_challenger/scouting/advanced_scout_system_v2.py` — sc2 폴백 스텁이 빈 클래스 (`class UnitTypeId: pass`)
- 함수 시그니처 `def fn(... = UnitTypeId.OVERLORD)`에서 임포트 타임 실패
- 영향: `test_bot_step_emergency_expansion_gate.py` 등 간접 임포트 체인의 테스트

### A5. `scripts.*` 모듈 누락 (2건)
- `wicked_zerg_challenger/tests/test_ladder_tracker.py` → `scripts.ladder_tracker`
- `wicked_zerg_challenger/tests/test_meta_adapter.py` → `scripts.meta_adapter`

## B. 폴백 스텁 일관성 부재

`wicked_zerg_challenger` 전반에서 sc2 미설치 시 폴백 스텁이 파일별로 다르게 정의됨:
- 일부는 풍부한 enum-like (예: `bot_step_integration.py` — 모든 유닛 타입 포함)
- 일부는 빈 클래스 (예: `scouting/advanced_scout_system_v2.py`)
- 일부는 try/except 자체가 없어 강제 sc2 의존

조치: 공용 `sc2_stub.py` 모듈을 만들고, `tests/conftest.py`에서 `sys.modules`에 주입하면 모든 테스트가 일관되게 컬렉트 가능.

## C. 우선순위 작업 계획

### Cycle 1 (완료): 테스트 컬렉션 0 errors 달성
- [x] 조사 완료
- [x] 공용 sc2 stub 모듈 추가 + 최상위 conftest.py에서 주입 (`tests/_sc2_stub.py`)
- [x] numpy 설치 (uv pip install numpy pytest-mock)
- [x] `Blackboard` alias 추가 (`wicked_zerg_challenger/blackboard.py`)
- [x] sc2 스텁의 ``UnitTypeId.OVERLORD`` 등 모든 속성 자동 노출 (metaclass __getattr__)
- [x] tests/conftest.py 에서 `wicked_zerg_challenger` 를 PROJECT_ROOT 보다 우선 sys.path 에 둠
- [x] ``scripts`` namespace 패키지 캐시가 ``local_training/scripts`` 로 묶이는 문제 해소
  (test_production_resilience.py 에서 local_training 을 sys.path 상단에 끼우던 코드 제거)

### 결과
- 컬렉션 에러: **27 → 0**
- 컬렉트된 테스트: **715 → 1174 (+459)**

### Cycle 2 (완료): 런타임 실패 처리
- [x] 컬렉트 후 실제 실행 시 실패한 테스트 분류 (105 failed / 1055 passed)
- [x] pytest-asyncio / pytest-timeout 설치 (async def 함수 86개 normalize)
- [x] sc2 스텁 강화: `_IdLike.name` / `_IdLike.value` 속성 노출
- [x] sc2 스텁 강화: `Race["Zerg"]` 인덱스 액세스 지원
- [x] sc2 스텁 강화: `__instancecheck__` 로 `isinstance(Race.Terran, Race)` 가 True
- [x] **봇 버그 수정**: `GameStateBlackboard.should_expand` — `is_supply_block` 오타 → `is_supply_blocked`
- [x] **봇 버그 수정**: `GameStateBlackboard.should_expand` — 미네랄 여유 체크 누락 → 300 마이너스 요건 추가

### 결과
- 테스트 실행: **105 failed / 1055 passed → 0 failed / 1160 passed**, 14 skipped

### Cycle 3 (완료): 정적 분석 / 봇 로직 버그
- [x] `wicked_zerg_challenger/game_analytics_system.py`: IndentationError + 중복 except 블록 — 봇 임포트 자체가 실패하던 syntax bug
- [x] `wicked_zerg_challenger/wicked_zerg_bot_pro_impl.py:572`: F823 — `traceback` UnboundLocalError. 함수 안쪽의 local `import traceback` 제거.
- [x] `wicked_zerg_challenger/opponent_modeling.py`: F811 — `OpponentModeling.on_step` 이 같은 클래스에서 두 번 정의되어 풍부한 구현(빌드/타이밍/테크 트래킹)이 minimal 구현에 덮여 dead code 였음. 안전 가드 통합 후 단일 메서드로 정리.
- [x] `wicked_zerg_challenger/local_training/production_resilience.py`: F811 — `build_terran_counters` 중복 정의. TechCoordinator 통합본만 유지.
- [x] E713 (not in 안티패턴 2건) auto-fix
- [x] F401 unused imports 4건 auto-fix

### Cycle 4 (완료): 추가 정밀 점검
- [x] `wicked_zerg_challenger/tests/test_blackboard.py`: 회귀 가드 테스트 2건 추가 (`test_should_not_expand_when_supply_blocked`, `test_should_not_expand_under_attack`)
- [x] `wicked_zerg_challenger/bot_step_integration.py:2166`: B023 — for-loop 안에서 `lambda: self._build_tech(tech_type)` 가 loop variable 을 캡처. 매 iteration 마다 같은 변수를 참조하므로 비동기 호출 / 저장 시 마지막 값만 쓰이는 위험. default 인자 바인딩으로 수정.

### Cycle 5 (계속): 남은 정적 분석 카테고리
- [ ] B023 다른 후보 (advanced_worker_optimizer, battle_preparation_system) — 즉시 평가되므로 영향 적으나 안전성 위해 일괄 정리 검토
- [ ] E741 ambiguous variable names (23건)
- [ ] F541 f-string missing placeholders (254건) — 단순 스타일
- [ ] F841 unused-variable (131건)
- [ ] STRATEGY_PLAN.md 미구현 단계 추적
- [ ] BUG_ERROR_LOG.md 미해결 잔존

## D. 측정 가능한 진척 지표
- collection errors: 27 → 0
- collected tests: 715 → ~750+ (현재 collect 단계 차단된 파일도 포함)
- pass rate: 측정 가능해진 뒤 다음 사이클에서 추적
