# SC2 지휘관봇 테스트 기반 개선사항 리스트

생성 시각: 2026-05-29 (자동 테스트 실행 결과 기반)

## 테스트 환경
- Python 3.11.15
- pytest 9.0.3 (asyncio-1.4.0, timeout-2.4.0)
- 외부 의존성: `burnysc2`, `sc2==0.11.2`, `s2clientprotocol==5.0.15`, `protobuf<3.21`, `loguru`, `scipy`

## 전체 테스트 결과 (초기 스냅샷)
- **수집된 테스트**: 659개
- **통과**: 652개
- **실패**: 7개
- **수집 에러**: 1개 (`tests/test_sprint8_qa.py` — `mpyq` 미설치)

---

## P0 — 즉시 수정 (실제 코드 버그)

### #1. `unit_factory.py:91` — Korean 주석과 코드가 한 줄에 붙어 NameError 발생
- **현상**: `NameError: name 'strategy' is not defined`
- **영향**: `TestGasRatioTarget`의 5개 테스트 모두 실패
  - `test_protoss_ratio`, `test_terran_ratio`, `test_zerg_ratio`, `test_unknown_race_fallback`, `test_strategy_manager_race`
- **원인**: 깨진 한글 주석 뒤에 `strategy = getattr(...)` 가 줄바꿈 없이 이어붙어 있음
- **수정**: 주석과 할당문을 별도 줄로 분리

### #2. `wicked_zerg_challenger/blackboard.py:540` — `should_expand()` 가 미네랄 체크를 누락
- **현상**: 미네랄 100인 상태에서도 `should_expand()` 가 True 반환
- **영향**: `tests/test_blackboard.py::TestStateQueries::test_should_not_expand_low_minerals` 실패
- **원인**: 위협/공급/공격 체크만 하고, 미네랄 비용 (Hatchery 300) 확인이 없음
- **수정**: `minerals >= 300` 조건 추가

### #3. `wicked_zerg_challenger/local_training/production_resilience.py:761` — `_produce_army_unit` 가 third base 예약 체크 누락
- **현상**: 방어 충족 후 third Hatchery 예약 단계에서도 라바를 군대에 소비
- **영향**: `test_third_base_reserve_blocks_army_larva_when_defense_ready` 실패
- **원인**: `_check_min_defense_met` 통과 후 곧바로 `_get_counter_unit` 으로 진행
- **수정**: 방어 충족 직후 `_should_reserve_third_base_minerals()` 게이트 추가

---

## P1 — 테스트 인프라

### #4. `tests/test_sprint8_qa.py` — `mpyq` 의존성 누락 시 우아한 스킵 없음
- **현상**: 수집 단계에서 `ModuleNotFoundError: No module named 'mpyq'`
- **원인**: `run_mass_test.py` 가 `from sc2.main import run_game` → `import mpyq` 강제
- **수정**: 테스트 모듈에 `pytest.importorskip("mpyq")` 또는 try/except 가드 추가

### #5. 테스트 의존성 문서 부재
- **현상**: README 어디에도 `pip install` 절차가 없음. 개발자가 매번 시행착오로 알아내야 함
- **수정**: `requirements-test.txt` (또는 `pyproject.toml` 의 `[project.optional-dependencies].test`) 추가

---

## P2 — 코드 품질 / 결합도

### #6. `_get_counter_unit` 가 Mock-like 객체에 취약
- **현상**: `enemy_units` 가 truthy인데 iterable이 아니면 `TypeError: 'Mock' object is not iterable`
- **수정**: 진입부에서 iterable 가드 추가 (테스트와 무관하게 방어적 코딩)

### #7. `should_expand()` 의 의미 정합성
- 현재 메서드명은 "확장이 가능한가?"인데 실제로는 위협/공급만 본다.
- 향후: 비용·예상 빌딩 슬롯·BO 단계까지 종합한 expansion-decision API 분리 고려

---

## P3 — 환경/관찰

### #8. burnysc2 와 sc2 패키지 충돌
- 두 패키지가 같은 namespace를 쓰면서 protobuf 버전이 갈림
- `pys2clientprotocol` (protobuf>=6) 과 `s2clientprotocol` (protobuf<=3.20) 가 동시에 설치되면 import가 깨짐
- 권장: 단일 stack 으로 통일 (sc2-0.11.2 + s2clientprotocol-5.0.15 + protobuf-3.20.3)

---

## 진행 로그

### Sweep #1 (커밋 `1cb55d5`)
- [x] #1 unit_factory.py 줄바꿈 수정
- [x] #2 blackboard.should_expand 미네랄 체크
- [x] #3 _produce_army_unit third-base 게이트
- [x] #4 test_sprint8_qa importorskip
- [x] #5 requirements-test.txt 생성
- [x] #6 _get_counter_unit iterable 가드
- [x] 추가: test_ladder_tracker / test_meta_adapter importlib 절대경로 로드

### Sweep #2 (이번 커밋)
- [x] #9 test_combat_phase_fsm.py: `asyncio.get_event_loop()` → `asyncio.run()` (Py 3.10+ 호환)
- [x] #10 cffi 의존성 추가 (`cryptography._rust` PyO3 panic 해결)

### 현재 상태
- 수집: 1176 tests
- 통과: **1161**
- 실패: 0
- 스킵: 15 (네이티브/외부 의존성으로 의도적 스킵)

### Sweep #3 (이번 커밋) — 정적 분석 (ruff E9/F63/F7/F82)
- [x] #11 `unit_factory.py:439` — 깨진 한글 주석이 `unit_requests = {}` 와 같은 줄에 붙어 F821 (5개 위치에서 undefined-name)
- [x] #12 `production_resilience.py:1451` — `force_resource_dump()` 안에서 `game_time` 정의 누락 (F821)
- [x] #13 `wicked_zerg_bot_pro_impl.py:689` — 함수 안에서 `import traceback` 이 모듈 임포트를 가려 F823 (같은 함수의 line 572 가 정의 전 참조)

결과: ruff syntax-level (E9/F63/F7/F82) 0 errors. 테스트 1161/1161 유지.

### Sweep #4 (이번 커밋) — encoding-corruption cleanup + safe ruff fixes
- [x] #14 `unit_factory.py` 3건 추가 한글 주석/코드 동일줄 패턴 (line 167, 185, 216) 정리. 이중 할당이라 런타임 버그는 아니지만 가독성 / 향후 디버깅 위험.
- [x] #15 `ruff --select=F401 --fix` 4건 unused-import 제거.

결과: 인코딩 깨짐으로 인한 "주석 안에 코드" 패턴 0건 (`grep` 광역 스캔으로 확인). 테스트 1161/1161 유지.

### Sweep #5 (커밋 `5331597`) — black + isort 포맷팅
- [x] #16 내가 sweep #1-#4 에서 수정한 모든 파일에 `black` + `isort` 적용. CI 의 black 체크가 통과되도록 (전체 repo 는 미수정).

### Sweep #6 (이번 커밋)
- [x] #17 pytest.ini 에 `asyncio_default_fixture_loop_scope = function` 추가 — `PytestDeprecationWarning` 제거 (sweep마다 30개 정도씩 누적되던 노이즈)
- [x] #18 CI failure 분석: Lint & Type Check (3.11) 가 `black --check .` (전체 repo) 에서 실패. 이는 sweep #5 이전부터 기존 문제 — 내가 만든 회귀 아님. 향후 PR 분리 권장.

### Sweep #7 (이번 커밋) — hidden test 가 드러낸 진짜 버그
- [x] #19 `tests/test_opponent_modeling.py` 의 `TestOpponentModeling` 이 `unittest.TestCase` 였는데 async test 메서드 9개를 가지고 있어서 silent skip 되고 있었음. `unittest.IsolatedAsyncioTestCase` 로 변경.
- [x] #20 (#19에서 드러남) `opponent_modeling.py` 가 `current_opponent` 와 `current_opponent_id` 두 속성을 일관성 없이 사용. `__init__` / `on_start` 는 `_id` 를, `on_game_start` / `on_step` / `on_game_end` 는 비-`_id` 를 사용. 실제 게임에서 `on_step` 이 attribute error 일 가능성이 있었음. 모두 `current_opponent_id` 로 통일 (8곳).
- [x] #21 `bot_step_integration.py` 의 `EnhancedScoutSystem` import 에 `warnings.catch_warnings()` 추가. 의도된 legacy fallback인데 매번 DeprecationWarning 출력하는 노이즈 제거.
- [x] #22 ruff `--select=F541 --fix` — 250건 의미 없는 `f"..."` (placeholder 없는 f-string) → 평범한 string 으로 정리.

### 결과 누적 (sweep #1~#7)
- 테스트: **1161/1161 통과** (sweep #1 이전: 652/659)
- 경고: 137 → **118** (sweep #1 이전 수치는 unknown, 약 150+ 추정)
- 실제 잠재 버그 8개 해결 + 테스트 인프라 3개 수정

### Sweep #8 (이번 커밋) — 두 번째 silent-skip 클러스터
- [x] #23 AST 스캐너로 `unittest.TestCase` 안의 `async def test_…` 패턴 광역 검색. 추가 발견: `TestProductionResilience` 의 async 테스트 9개도 동일 silent skip 중.
- [x] #24 `TestProductionResilience` 를 `IsolatedAsyncioTestCase` 로 변경 → 3개 stale 테스트 (`test_get_counter_unit_terran_marine/protoss/zerg`) 가 드러남. `_get_counter_unit` 의 시그니처가 바뀌었는데 (sync, `enemy_units + 3 tech flags`) 테스트는 이전 async 시그니처 `_get_counter_unit(race_name)` 를 호출 중이었음. 시그니처에 맞춰 재작성.
- [x] AST 스캐너로 재검사 → 0건.

### 결과 누적 (sweep #1~#8)
- 테스트: **1161 통과**, 0 실패, 0 silent-skip
- 경고: 137 → **100**
- 진짜 production 버그: 8개 (#1~#3, #11~#13, #20, #24의 시그니처 mismatch)
- 테스트 인프라: 5건 (#4, #5, #9, #10, #19, #23)

### Sweep #9 (이번 커밋)
- [x] #25 `adaptive_trainer.calculate_win_rate` 의 race_name 인자가 무시되던 spec 버그 해결. GameStatistics 가 `by_difficulty` 와 `by_race` 만 가지므로 결합 카운트는 마지널의 평균과 min 으로 추정. 호출자가 없는 dead code 지만 spec 일치.
- [x] #26 `pytest.ini` 에 `filterwarnings` 추가 — `s2clientprotocol.*` 과 `google.protobuf.*` 의 외부 deprecation 노이즈 제거. 경고 100 → **0** 으로 표시.

### 결과 누적 (sweep #1~#9)
- 테스트: **1161 통과**, 0 실패, 0 silent-skip
- 경고: 137 → **0 (표시)** (외부는 필터, 내부는 모두 수정)
- 실제 production 버그: 9개 (#1~#3, #11~#13, #20, #24, #25)
- 테스트 인프라: 6건 (#4, #5, #9, #10, #19, #23)

### Sweep #10 (이번 커밋) — lifecycle smoke test 추가
- [x] #27 `wicked_zerg_challenger/tests/test_bot_lifecycle_smoke.py` 신규: WickedZergBotProImpl 의 constructor 와 lazy-init 속성 검증 (4개) + sweep #7 회귀 가드 (OpponentModeling on_start → on_step 경로) (1개). 총 5개 테스트 추가.
- [x] sweep #7 회귀 가드는 일부러 verbose 한 코멘트를 달아서 향후 다시 `current_opponent` ↔ `current_opponent_id` 같은 drift 가 생기면 즉시 잡히게 함.

### 결과 누적 (sweep #1~#10)
- 테스트: **1166 통과**, 0 실패, 0 silent-skip (1161 → 1166)
- 경고: 0 표시
- 실제 production 버그: 9개
- 테스트 인프라: 6건
- 회귀 가드 테스트: 5건

### Sweep #11 (이번 커밋) — `bot.intel` vs `bot.intel_manager` drift
- [x] #28 AST-기반 스캐너로 `self.bot.<X>` 를 읽지만 어디에서도 set 되지 않는 attribute 광역 탐색. `intel_manager` 가 발견됨.
- [x] #29 `manager_registry.py` 는 IntelManager 를 `bot.intel` 로 등록하지만 4개 파일이 `bot.intel_manager` 로 잘못 읽고 있었음. `intel` 우선, `intel_manager` 폴백으로 통일:
  - `realtime_awareness_engine.py:225` — SITREP 의 enemy_build_pattern, threat_level 가 항상 unknown/none 이었던 잠재 버그
  - `combat/creep_denial_system.py:205` — crep tumor placement 의 위험 판단이 항상 비활성화되던 버그
  - `scoring_system.py:305, 530` — 스코어링 시스템의 적 빌드 인지 보너스가 항상 0점이던 버그
  - `composition_optimizer.py:246` — historical enemy unit counts 가 항상 무시되던 버그

### 결과 누적 (sweep #1~#11)
- 테스트: **1166 통과**, 0 실패, 0 silent-skip
- 경고: 0 표시
- 실제 production 버그: **13개** (4개 추가)
- 테스트 인프라: 6건
- 회귀 가드 테스트: 5건

### Sweep #12 (이번 커밋) — combat/economy manager drift
- [x] #30 manager_registry 의 36개 attribute_name 을 자동 스캔. `combat` 와 `economy` 가 drift 발견.
- [x] #31 `logic_optimizer.apply_combat_improvements` 와 `apply_economy_improvements` — `combat_manager` / `economy_manager` 로 잘못 읽고 있어서 difficulty 별 적용되어야 할 task priority/economy threshold 가 항상 무시되던 잠재 버그. 4번째 silent-failure 카테고리.

### 결과 누적 (sweep #1~#12)
- 테스트: **1166 통과**, 0 실패, 0 silent-skip
- 경고: 0 표시
- 실제 production 버그: **15개** (2개 추가)
- 테스트 인프라: 6건
- 회귀 가드: 5건

### Sweep #13 (이번 커밋) — opponent_modeling 의 3가지 mypy 실제 버그
- [x] #32 `opponent_modeling.py:765` — `async def on_step` 이 두 번 정의되어 두 번째가 첫 번째를 가림. 첫 번째 (line 341) 가 update_interval throttling + build-order tracking + timing-attack detection + tech-progression + blackboard update 등 다 하는데, 두 번째 (line 765) 는 early-signal detection 만 함. Python silently used the second. shadowing 정의 삭제, 첫 번째에 current_opponent_id 가드 통합.
- [x] #33 `opponent_modeling.py:783-784` — GameHistory dataclass 에 `game_won`/`game_lost` 필드 없는데 dynamic attribute 로 set. 실제 필드 `game_result: str` 에 "win"/"loss"/"unknown" 으로 매핑.
- [x] #34 `opponent_modeling.py:786, 824` — `observed_signals` 는 `Set[str]` 인데 `s.value` 로 enum 처럼 접근. AttributeError 위험. `list(self.observed_signals)` 로 변경.

### 결과 누적 (sweep #1~#13)
- 테스트: **1166 통과**, 0 실패, 0 silent-skip
- 경고: 0 표시
- 실제 production 버그: **18개** (3개 추가)
- 테스트 인프라: 6건
- 회귀 가드: 5건

### Sweep #14 (이번 커밋) — duplicate method definitions 광역 스캔
- [x] #35 AST 기반 스캐너로 같은 클래스 내 중복 메서드 정의 4건 발견. 모두 shadowing 패턴 (두 번째가 첫 번째를 가려서 첫 번째는 dead code).
  - `combat_manager.CombatManager._find_harass_target` (line 2815 ↔ 5011) — 단순 fallback 버전 삭제, sophisticated worker-priority 버전이 활성.
  - `economy_manager.EconomyManager._prevent_resource_banking` (line 1708 ↔ 3286) — queens+static defense 버전을 `_prevent_resource_banking_via_defense` 로 rename, macro-hatchery+expansion 버전이 활성.
  - `economy_manager.EconomyManager._reduce_gas_workers` (line 3427 ↔ 4110) — 단순 버전을 `_reduce_gas_workers_simple` 로 rename, severity-aware 버전이 활성.
  - `production_resilience.ProductionResilience.build_terran_counters` (line 1466 ↔ 1984) — 직접 b.build() 버전 삭제, TechCoordinator 버전이 활성.

### 결과 누적 (sweep #1~#14)
- 테스트: **1166 통과**, 0 실패, 0 silent-skip
- 경고: 0 표시
- 실제 production 버그: **22개** (4개 추가 — silently shadowed legacy code)
- 테스트 인프라: 6건
- 회귀 가드: 5건
- 재검증: AST 스캐너로 0건 (shadowing 완전 정리)

### Sweep #15 (이번 커밋) — kd_tree.py mypy + module-level 중복 검사
- [x] #36 모듈 레벨 함수 중복 AST 스캔 — 0건 (클래스 내부만 문제였음).
- [x] #37 `utils/kd_tree.py` mypy 3건 타입 어노테이션 누락:
  - `nearest_neighbor`: `best: List[Any]` 어노테이션 추가, 결과 unpack 도 명시적 타입
  - `range_query`: `results: List[Tuple[Tuple[float, float], Any, float]]` 어노테이션
  - `knn_search`: `heap: List[Tuple[float, Tuple[float, float], Any]]` 어노테이션
  결과: kd_tree.py mypy clean.

### 결과 누적 (sweep #1~#15)
- 테스트: **1166 통과**, 0 실패, 0 silent-skip
- 경고: 0 표시
- 실제 production 버그: **22개**
- 타입 정리: 1개 파일 (`utils/kd_tree.py`)
- 테스트 인프라: 6건
- 회귀 가드: 5건

### Sweep #16 (이번 커밋) — harassment_coord vs harassment_coordinator + dead-feature 식별
- [x] #38 `combat_manager.py:506, 794` 가 `self.bot.harassment_coordinator` 로 읽지만 `BotStepIntegrator:437` 가 `self.bot.harassment_coord` 로 attach. 두 spot 모두 unit lock 체크가 항상 비활성화되던 버그. 두 이름 모두 받도록 수정 (해러스 미션에 락된 유닛이 메인 공격에 재할당되는 버그가 production 에 존재했을 가능성 매우 높음).
- [x] hasattr-target AST 스캐너로 dead feature 식별:
  - `CompleteDestructionTrainer` 클래스는 정의되어 있지만 어디서도 instantiate 되지 않음 → `bot.complete_destruction` 가드는 항상 false. 4개 파일의 관련 코드 전체가 dead. (수정 보류 — feature design 결정 필요)
  - `MapMemorySystem` 도 동일 패턴. (수정 보류)

### 결과 누적 (sweep #1~#16)
- 테스트: **1166 통과**, 0 실패
- 경고: 0 표시
- 실제 production 버그: **23개**
- Dead feature 발견: 2개 (CompleteDestruction, MapMemory) — 문서화만
- 테스트 인프라: 6건
- 회귀 가드: 5건

### Sweep #17+ 후보
- [ ] BotStepIntegrator 의 다른 `bot.X_coord` 등록 vs 소비자 일치 검사 (단축어/축약 패턴)
- [ ] F841 / E402 정리
- [ ] black 점진적 적용
- [ ] integration 테스트 확대
