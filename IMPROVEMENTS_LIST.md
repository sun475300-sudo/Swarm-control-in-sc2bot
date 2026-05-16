# SC2 지휘관봇 개선사항 리스트 (Improvements List)

테스트와 정적 점검을 통해 발견한 개선 항목들. 본 리스트는 반복 사이클마다
갱신되며, 완료된 항목은 ✅, 진행 중은 🚧, 신규는 ⬜ 로 표시한다.

## 환경 세팅
- ✅ `pytest-asyncio` 미설치로 인해 83개 `async def` 테스트가 실패하던 문제 해결 (uv tool install).
- ⬜ `wicked_zerg_challenger/requirements.txt`에 `pytest-asyncio`, `pytest`, `protobuf` 핀 추가.

## 사이클 1 (완료): 컬렉션 에러 / 임포트 깨짐
- ✅ **#1** `wicked_zerg_challenger/blackboard.py`: `Blackboard = GameStateBlackboard` 별칭 추가
  → `wicked_zerg_bot_pro_impl.py`, `production_controller.py`, `tests/test_blackboard.py`,
  `tests/test_sprint8_qa.py` 컬렉션 복구.
- ✅ **#2** `wicked_zerg_challenger/game_analytics_system.py:419` SyntaxError 제거 (중복 `except` 블록 삭제).
- ✅ **#3** `wicked_zerg_challenger/check_proxy.py`: 임포트 시 `sys.exit(1)` 실행 → `main()`/`__main__` 가드로 격리.
- ✅ **#7** `check_proxy.py` `logger.info` 다중 인자 호출 3건 → f-string.
- ✅ **#8** `check_proxy.py` 최상위 사이드 이펙트 → `main()` 캡슐화.

## 사이클 1 (완료): src/bot/swarm 패키지 깨짐
- ✅ **#4** `src/__init__.py`, `src/bot/__init__.py`, `src/bot/swarm/__init__.py` 추가.
- ✅ **#5** `src/bot/swarm/formation_controller.py` 신규 추가 → 30개 behavior 임포트 복구.
- ✅ **#12** `tests/test_swarm_behaviors.py` 신규 — 모든 30 behavior 임포트 + tick 계약 + center_of_mass 검증.

## 사이클 1 (완료): 테스트 중 발견된 로직 버그
- ✅ **#13** `blackboard.py:544` 오타 `is_supply_block` → `is_supply_blocked`.
- ✅ **#14** `GameStateBlackboard.should_expand()`가 자원 부족을 검사하지 않아
  `test_should_not_expand_low_minerals` 실패 → `EXPANSION_MIN_MINERALS = 300` 가드 추가.

## 사이클 2 (예정): 정적/구조적 후보
- ⬜ **#6** 30개 `behavior_XX.py` 가 한 줄 차이를 제외하고 동일 → 공통 base class로 추출.
- ⬜ **#9** `pytest.ini` 의 `asyncio_mode = auto` 가 있으나 `pytest-asyncio` 가 명시적 의존성으로 선언되지 않음.
- ⬜ **#10** `wicked_zerg_challenger/tests/` 일부 conftest 가 `sys.path` 조작으로 동작 — pyproject.toml 정비.
- ⬜ **#11** 30개 behavior placeholder 를 의미 있는 행동 모듈로 분리하거나 단일화.

## 사이클 2 (예정): 코드 품질
- ⬜ **#15** `wicked_zerg_challenger/blackboard.py`: `ResourceState`/`ThreatInfo` 가 typed 가 아니어서 None 안정성 부족.
- ⬜ **#16** 30+ Korean log/comment 인코딩이 UTF-8 인지 모두 검증 + .editorconfig 확인.
- ⬜ **#17** `src/bot/swarm/` behavior 30개에 docstring 보강 + type hints.

## 사이클 1 결과
- 상위 `tests/`: **562 passed**, 14 skipped, 0 failed.
- `wicked_zerg_challenger/tests/`: **661 passed**, 38 warnings, 0 failed.
- 컬렉션 실패: 0 (이전 21건).

---

이 리스트는 사이클이 끝날 때마다 다시 커밋된다.
