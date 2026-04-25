# SC2 지휘관봇 개선 트래커 (Iterative)

테스트/점검 사이클로 발견된 개선사항을 추적합니다. 항목 단위로 수정 → 커밋 → 푸시 → 다음 항목.

## 사이클 1: 정적 import / __init__ / 테스트 인프라 ✅

### 인프라 (Infra)
- [x] **A1** pytest-asyncio 누락 — uv tool로 설치 (83건 async 테스트 unblock)
- [x] **A2** numpy 누락 — 설치 후 추가 4건 실패 노출

### Phase 6xx 모듈 import 결함
- [x] **I1** `qmix_marl/sc2_qmix_agent.py` torch 부재 시 NameError → nn/F/optim placeholder
- [x] **I2** `mappo_marl/sc2_mappo_agent.py` 동일 결함 + `__init__.py` export 4건 정정
- [x] **I3** `comm_learning/__init__.py` 존재하지 않는 심볼 4개 정정 + alias 유지
- [x] **I4** `attention_policy/__init__.py` 4개 정정 + alias 유지
- [x] **I5** `world_model/__init__.py` 4개 정정 + alias 유지

### 검증
- [x] **I6** 전 패키지 import 청결 검증 — 65개 패키지 모두 OK
- [x] **I7** dev 환경 deps (pytest-asyncio, pytest-timeout, numpy) requirements 명시
       + CI에서 silent-failure 모드 제거

## 사이클 2: flake8 critical (E9/F63/F7/F82) ✅

22건 검출 → 19건 수정, 3건 잔존(F824 cosmetic).

런타임 NameError 위험 19건:
- [x] **L1** `formation_tactics._handle_unburrowed_unit` enemy_units 파라미터 추가
- [x] **L2** `early_defense_system` UpgradeId stub 누락 추가
- [x] **L3** `production_resilience._boost_early_game` game_time 변수명 정정
- [x] **L4** `bot_step_integration.draw_debug_info` iteration 외부참조 → game_loop
- [x] **L5** `spell_unit_manager` "WickedZergBotPro" 미해결 → impl alias
- [x] **L6** `chat_manager` 빈 __all__ → no-op stub 클래스 정의
- [x] **L7** `migrate_prints_to_logger` logger 미정의 → import logging 추가
- [x] **L8** `mappo_marl` rewards 루프 외부 미초기화 정정
- [x] **L9** `system_mcp_server` import sys 누락
- [x] **L10** `integration_hub` f-string 잘못된 보간 → 일반 문자열로 변경
- [x] **L11** `grpc_advanced/interceptor` except `as e` 클로저 NameError 패턴 정정

## 사이클 3: 통합 테스트 + sc2-less 환경 ✅

- [x] tests/integration/test_full_pipeline.py 10/10 PASS
- [x] wicked_zerg_challenger/tests 컬렉션 에러 분석:
  - sc2 없는 환경에서 `_assign_patrol(unit_type=UnitTypeId.OVERLORD)` 기본값 평가 실패 → lazy lookup
  - `Units = None` 상태에서 `Units([], None)` 호출 TypeError → list 기반 stub 클래스
- [x] test_unit_helpers 4 fail → 0 fail (40 PASS)

## 사이클 4: dead-method 중복 정의 제거 (silent override) ✅

flake8 F811로 발견한 4건의 동일 클래스 내 중복 메서드 정의:
- [x] **D1** `opponent_modeling.on_step` (단순화된 dup이 정상 버전 가림 — 22프레임 throttling/blackboard 업데이트가 죽어 있던 상태)
- [x] **D2** `combat_manager._find_harass_target`
- [x] **D3** `economy_manager._prevent_resource_banking`
- [x] **D4** `economy_manager._reduce_gas_workers`
- [x] **D5** `production_resilience.build_terran_counters`

## 사이클 5: redundant import (F811 import dups) ✅

14건 모두 정리: micro_combat, creep_manager, replay_to_rl_trainer,
run_with_training, spell_unit_manager, background_parallel_learner.

---

## 누적 결과

| 지표 | Before | After |
|---|---|---|
| pytest pass | 223 (env-broken: 83 fail) | **340 PASS / 19 skip / 0 fail** |
| flake8 critical (E9/F63/F7/F82) | 22 | **3** (F824 cosmetic만) |
| 패키지 import 결함 | 5+ broken | **0** |
| 중복 메서드 정의 (silent shadow) | 4 | **0** |

## 사이클 6+ (예정)
- [ ] integration_hub.py 추가 결함 audit
- [ ] mypy strict-equality 정리
- [ ] 봇 핵심 코드 path-dependency / config-loader 일관성
- [ ] 보안 스캔(detect-secrets) 결과 점검
- [ ] CI에 `pytest tests/` 실패가 fail 빌드로 전파되는지 PR로 검증

## 진행 로그

| 사이클 | 항목 | 커밋 |
|---|---|---|
| 1 | A1, A2 (env) + I1-I7 | 46fa8c7, 055a9ea, 673fb91, 43f5750 |
| 2 | L1–L11 critical lint | ba17cb1 |
| 3 | sc2-less robustness | 99a2abc |
| 4 | dead-method removal | e35d9ca |
| 5 | redundant import cleanup | 8011bb5 |
