# SC2 지휘관봇 종합 개선 작업 리스트

본 문서는 봇 코드베이스에 대한 반복 테스트·점검 결과 발견된 개선사항을
우선순위별로 정리한 작업 큐(work queue)다. 각 항목은 커밋 단위 작업이며,
완료 시 체크박스를 표시하고 후속 점검 라운드로 진행한다.

## 점검 방식 (라운드 루프)

1. 테스트 실행 (`pytest`, import 점검, 정적 분석)
2. 발견된 결함을 본 문서 큐에 추가 (우선순위 P0~P3)
3. 큐 상단 항목 수정 → 단위테스트 → 커밋·푸시
4. 1번으로 돌아가 새로운 결함 추적

---

## P0: 기능 차단(Blocker) 버그 — 즉시 수정

### P0-1: `unit_factory.py:91` 깨진 한글 주석이 `strategy =` 할당을 삼킴
- 증상: `tests/test_unit_factory.py::TestGasRatioTarget` 5개 테스트 전부
  `NameError: name 'strategy' is not defined` 발생
- 원인: 91번째 라인의 깨진 한글 주석 뒤에 줄바꿈이 없어
  `strategy = getattr(self.bot, "strategy_manager", None)` 가 주석으로 처리됨
- 수정: 주석과 코드를 분리, 깨진 한글을 정상 텍스트로 복구
- 영향: 가스 비율 타깃 갱신 로직 자체가 동작하지 않음 (game-time 침묵 버그)

### P0-2: `blackboard.GameStateBlackboard.should_expand()` 미네랄 조건 누락
- 증상: `tests/test_blackboard.py::test_should_not_expand_low_minerals`
  실패 (`AssertionError: True is not false`)
- 원인: `should_expand()`가 위협/서플라이/공격받는 상태만 확인,
  실제 미네랄·가스 보유량은 무시 → 미네랄 100에서도 True 반환
- 수정: 최소 미네랄(예: 400) 미달 시 False 반환 추가

### P0-3: `local_training/production_resilience.py:2177` enemy_units가 Mock일 때 iter 실패
- 증상: `test_third_base_reserve_blocks_army_larva_when_defense_ready`
  `TypeError: 'Mock' object is not iterable`
- 원인: 카운터 픽 로직이 `for enemy in enemy_units:` 를 곧장 호출,
  iterable 여부 가드 없음
- 수정: `try/except TypeError`로 감싸고 Units 형 변환·길이 체크 가드 추가

---

## P1: 중복 메서드 정의 (런타임 실버 오버라이드)

`ast` 정적 분석에서 동일 클래스 내 동일 이름 메서드가 2회 정의된 케이스.
Python은 마지막 정의만 유지하므로 첫 번째 구현은 사용되지 않는 데드코드다.

### P1-1: `combat_manager.CombatManager._find_harass_target`
- 라인 2815-2843 (29줄) / 라인 5011-5067 (57줄)
- 작업: 두 구현의 차이를 비교 → 통합 또는 첫 번째 제거 (5011 버전이 사용됨)

### P1-2: `economy_manager.EconomyManager._prevent_resource_banking`
- 라인 1708-1814 (107줄, async) / 라인 3286-3384 (99줄, async)
- 작업: 동작 비교 후 통합. 두 비동기 구현이 자원 banking 방지 로직임

### P1-3: `economy_manager.EconomyManager._reduce_gas_workers`
- 라인 3419-3444 (26줄, async) / 라인 4110-4159 (50줄, async)
- 작업: 가스 일꾼 감소 로직 통합

### P1-4: `opponent_modeling.OpponentModeling.on_step`
- 라인 341-367 (27줄, async) / 라인 765-774 (10줄, async)
- 작업: 두 번째 (10줄) 구현이 활성. 첫 번째 구현(상세 로직)이 누락된 채 동작 중

---

## P2: 깨진 테스트 코드 (가짜 통과)

### P2-1: `wicked_zerg_challenger/test_bot_initialization.py`
- 결함: `test_imports()`의 모든 `try: pass; except: ...` 블록이
  실제 import를 시도하지 않고 성공 로그만 출력
- 결함: `verify_code_patterns()`가 패턴 누락 시에도 무조건 True 반환
- 결함: `main()`이 "ALL TESTS PASSED"를 패턴 결함에도 출력
- 결함: 기본 logging 핸들러가 설정되지 않아 콘솔 출력이 침묵됨
- 수정: 실제 import 호출 추가, 누락 패턴 시 False 반환, basicConfig 호출

### P2-2: 테스트 픽스처가 사용하는 식별자가 코드와 불일치
- `verify_code_patterns()`이 찾는 `ProductionResilience(self)`, 
  `self.strategy_manager.update()`, `self.rogue_tactics.update(iteration)` 
  3개 패턴이 모두 현재 봇 impl에 없음
  → 봇이 정말 사용 안 하는지 / 리네임됐는지 확인 필요

---

## P3: 코드 품질 개선

### P3-1: `pass`만 있는 except 핸들러 163건
- 위험: 예외를 완전히 삼켜 디버깅 불가
- 작업: 최소 `logger.debug` 추가 또는 구체 예외 타입으로 한정

### P3-2: `except Exception` 광범위 캐치 581건
- 위험: 시스템 예외(KeyboardInterrupt 제외)·프로그래밍 오류까지 삼킴
- 작업: 핫패스에서 구체 예외로 좁히기

### P3-3: 200줄 이상 거대 함수 12개
- `bot_step_integration.execute_game_logic`: **1726줄** — 분해 우선순위 최상
- `combat_manager._execute_multitasking`: 764줄
- `bot_step_integration.__init__`: 303줄
- `bot_step_integration._safe_hierarchical_rl_step`: 253줄
- `economy_manager._check_proactive_expansion`: 235줄
- `realtime_awareness_engine._detect_problems`: 237줄
- `combat_manager._offensive_attack`: 231줄
- `logic_optimizer._initialize_system_configs`: 257줄

### P3-4: 거대 모듈 분해
- `combat_manager.py` 194 KB
- `economy_manager.py` 179 KB
- `bot_step_integration.py` 159 KB
- `strategy_manager.py` 124 KB
- 작업: 클래스 추출·서브모듈 분리

---

## P4: 추가 점검 항목 (라운드 누적)

(라운드마다 본 섹션에 발견 사항 누적)

---

## 진행 체크리스트

- [x] P0-1 unit_factory.py 깨진 주석/할당 복구
- [x] P0-2 should_expand 미네랄 조건 추가
- [x] P0-3 production_resilience Mock iter 가드
- [x] P1-1 CombatManager._find_harass_target 통합
- [x] P1-2 EconomyManager._prevent_resource_banking 통합
- [x] P1-3 EconomyManager._reduce_gas_workers 통합
- [x] P1-4 OpponentModeling.on_step 통합
- [x] P2-1 test_bot_initialization.py 가짜 통과 수정 (pytest 모듈로 재작성)
- [x] P2-2 verify_code_patterns 식별자 동기화 (실제 호출 위치 검증)
- [ ] P3-1~4 코드 품질 점진 개선 (라운드마다 1~2건)

## 라운드 2 후속 작업 (큐)

- [ ] R2-1 `bot_step_integration.execute_game_logic` 1726줄 분해
- [ ] R2-2 `combat_manager._execute_multitasking` 764줄 분해
- [ ] R2-3 `pass`만 있는 except 핸들러 163건 가운데 핫패스 정리
- [ ] R2-4 `wicked_zerg_bot_pro_impl.py` 잔존 mojibake 한글 주석 정리
- [ ] R2-5 신규 점검: `ast` 분석으로 미사용 import / 사용되지 않는 메서드 추가 발견

## 라운드 2-6 작업 완료 요약

라운드별로 발견·수정한 잠재 결함:

### Round 2 (mojibake → 코드 삼킴)
- `unit_factory.py:439` — `unit_requests = {}` 주석에 갇혀 NameError 위험
- `unit_factory.py:48/167/216` — 부수적 mojibake 정리
- `dynamic_resource_balancer.py:175` — 주석 내부 가짜 `return {`

### Round 3 (없는 메서드 호출)
- `strategy_manager_v2.evaluate_strategy_effectiveness`
  → `_estimate_enemy_army` (없음) → `_estimate_enemy_army_supply`
  → `_get_worker_count` (없음) → `_count_workers`
- `nydus_network_trainer._manage_nydus_operations`
  → `_command_deployed_units` (구현 없음) — 호출 제거

### Round 4 (typo 추가 발견)
- `strategy_manager_v2.evaluate_opponent_profile:1782` 동일한 `_estimate_enemy_army` typo

### Round 5 (조건부 import의 module-level class 정의)
- `local_training/imitation_learner.py` `class ImitationNetwork(nn.Module)`
  → torch 미설치 시 `nn=None` 으로 `AttributeError` 발생
- `local_training/ppo_agent.py` 동일 패턴 `ActorCriticNetwork`
- `_NetworkBase` placeholder 도입으로 import 안전 확보

### Round 6 (pyflakes 정적 분석)
- `production_resilience.force_resource_dump:1452` `game_time` 미정의
- `production_resilience.build_terran_counters` 중복 정의 (L1467, L1985)

### Round 7~9 (추가 점검)
- pyflakes 전체 디렉토리 스캔 — undefined / redefinition 없음
- `is_engaging`, `is_destroyed`, `is_active` 등 `is_*` 속성은
  내부 데이터 클래스 정의로 false positive 확인
- mock 환경에서 `on_start` 50+ 서브시스템 정상 초기화 검증

## 점검 결과 통계

| 라운드 | 신규 결함 | 누적 통과 테스트 |
|--------|----------|-----------------|
| 0 (baseline) | 7 실패 | 661 |
| 1 (P0+P1+P2) | 7 fix | 678 |
| 2 (mojibake) | 5 fix | 678 |
| 3 (없는 메서드) | 3 fix | 678 |
| 4 (typo) | 1 fix | 678 |
| 5 (조건부 import) | 2 fix | 678 |
| 6 (pyflakes) | 2 fix | 678 |
| **합계** | **20개 결함 수정** | **678 통과** |


