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

### Sweep #8+ 후보
- [ ] 다른 `unittest.TestCase` 안의 async test 메서드 같은 패턴 검색
- [ ] F841 (unused-variable) 132건 케이스별 검토
- [ ] E402 (module-import-not-at-top-of-file) 66건
- [ ] adaptive_trainer.calculate_win_rate dead code (race_name 무시) — 호출자 없음, 삭제 후보
- [ ] `s2clientprotocol` deprecated descriptor 호출 (외부) — filterwarnings 로 조용히 처리
- [ ] 462개 `except Exception:` 광역 검토
