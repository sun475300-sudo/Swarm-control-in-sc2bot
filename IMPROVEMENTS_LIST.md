# SC2 지휘관봇 개선사항 리스트 (Improvements List)

테스트와 정적 점검을 통해 발견한 개선 항목들. 본 리스트는 반복 사이클마다
갱신되며, 완료된 항목은 ✅, 진행 중은 🚧, 신규는 ⬜ 로 표시한다.

## 환경 세팅
- ✅ `pytest-asyncio` 미설치로 인해 83개 `async def` 테스트가 실패하던 문제 해결 (uv tool install).
- ✅ **#9** `wicked_zerg_challenger/requirements.txt`에 `pytest`, `pytest-asyncio` 핀 추가.

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

## 사이클 2 (완료): 죽은 코드 / 포맷팅
- ✅ **#18** `smart_resource_balancer.py:_get_current_worker_ratio` 함수 본문에 `return` 뒤로 23줄의
  중복 코드(unreachable)가 따라붙어 있었음 → 삭제.
- ✅ **#20** `smart_resource_balancer.py:_move_workers_to_minerals` 마지막 `return moved` 뒤로 22줄의
  중복 코드가 존재했음 → 삭제.
- ✅ **#19** `economy_manager.py:_force_expansion_if_stuck` 와 `_check_proactive_expansion` 두 함수에
  return 이후 dead code (총 ~80줄, 옛 expand 로직 잔재) → 삭제.
- ✅ **블랙 포맷**: 내가 편집한 `blackboard.py`, `smart_resource_balancer.py`, `economy_manager.py`,
  `check_proxy.py` 에 `black` 포맷터 적용.
  *(repo 전체 black 적용은 범위 밖 — main 에 67개 pre-existing violations 존재. 내 PR이 추가로 도입한
  위반은 0.)*

## 사이클 3 (예정): 정적/구조적 후보
- ⬜ **#6** 30개 `behavior_XX.py` 가 한 줄 차이를 제외하고 동일 → 공통 base class로 추출.
- ⬜ **#10** `wicked_zerg_challenger/tests/` 일부 conftest 가 `sys.path` 조작으로 동작 — pyproject.toml 정비.
- ⬜ **#11** 30개 behavior placeholder 를 의미 있는 행동 모듈로 분리하거나 단일화.
- ⬜ **#15** `wicked_zerg_challenger/blackboard.py`: `ResourceState`/`ThreatInfo` 가 typed 가 아니어서 None 안정성 부족.
- ⬜ **#16** Korean log/comment 인코딩이 UTF-8 인지 모두 검증 + .editorconfig 확인.
- ⬜ **#17** `src/bot/swarm/` behavior 30개에 docstring 보강 + type hints.
- ⬜ **#21** 다른 wicked_zerg_challenger/*.py 파일에 dead-code (return 뒤 코드) 검출용 CI guard 추가.
- ⬜ **#22** Repo-wide black 적용 (67 파일) — main 에 별도 PR.

## CI 상태 (PR #180)
- ✅ `SC2 봇 검증 & 테스트` — success
- ✅ `no-empty-logger-calls` — success
- ✅ `Node.js 린트 & 테스트` — success
- ✅ `Phase 68 멀티언어 벤치마크` — success
- ✅ `CodeQL` (4/4) — success
- ❌ `Lint & Type Check (3.11)` — failure (**pre-existing**: repo-wide black 위반 67개)
- 🔄 `Python 린트 & 테스트` — running

## 누적 테스트 결과
- 상위 `tests/`: **562 passed**, 14 skipped, 0 failed.
- `wicked_zerg_challenger/tests/`: **661 passed**, 38 warnings, 0 failed.
- **합계: 1223 passed**, 0 failed.

---

이 리스트는 사이클이 끝날 때마다 다시 커밋된다.
