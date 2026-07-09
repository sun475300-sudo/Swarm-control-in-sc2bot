# PR / CI 백로그 감사 — 2026-07-09

> 이 문서는 자동화 세션(`claude/optimistic-edison-*`)의 반복 실행 결과를 점검하기 위해 작성됨.
> 이전 감사: `MASTER_TODO_SC2.md` (2026-04-26, PR #28 시점 기준, 이제 stale)

## 핵심 발견: 머지 정체로 인한 중복 작업 폭증

- **`main`의 마지막 커밋은 2026-06-25**(`8a80b7357a`, "Update ci.yml"). 그 이후 2주 넘게 `main`에 아무 것도 머지되지 않음.
- 그 사이 **`claude/optimistic-edison-*` 브랜치로 150개 이상의 draft PR**이 열림(#218 이후). 저장소 역사상 **PR #218 단 하나만 머지**됨.
- 열린 PR 제목을 보면 거의 전부가 같은 3가지 문제를 반복 재발견/재수정하고 있음:
  1. `pytest/` 디렉터리가 루트에 있어 `python -m pytest` 실행 시 실제 `pytest` 패키지를 가림
  2. `tests/test_combat_phase_fsm.py`가 `asyncio.get_event_loop().run_until_complete(...)`를 사용 — Python 3.11에서 `RuntimeError: There is no current event loop`로 즉시 실패
  3. `ci.yml`의 "pytest 실행 (전체)" 스텝이 `--co`(collect-only) 플래그를 포함해 **테스트를 전혀 실행하지 않음**, `sc2bot-ci.yml`의 test job은 존재하지 않는 `tests/unit`, `tests/integration` 경로를 가리켜 **`test` job이 항상 즉시 실패** → 그 뒤의 `build_docker`/`push_to_registry`/`deploy_to_k8s`도 전부 실행된 적 없음
- 즉, 각 세션이 "테스트 돌려보니 깨져있다"를 발견 → 고치고 draft PR을 새로 엶 → 아무도 머지하지 않음 → 다음 세션이 여전히 깨진 `main`에서 시작 → **동일한 발견을 반복**. 실제 코드 품질 문제라기보다 **머지 프로세스 부재**가 원인.

## 이번 세션에서 이 브랜치(`claude/optimistic-edison-xpidhx`)가 한 일

기존 draft PR들과 중복되지 않도록, 로컬에서 실제 의존성(`burnysc2`, `numpy`, `protobuf` 등)을 설치하고 두 테스트 스위트를 직접 실행해 재현/검증 후 수정함:

| 항목 | 수정 전 | 수정 후 |
|---|---|---|
| `tests/` (502 tests) | 20 failed (asyncio 5건, cffi 누락 8건) | **502 passed, 14 skipped** |
| `wicked_zerg_challenger/tests/` (661 tests) | 통과 (deps만 있으면) | **661 passed** |
| `black --check .` | 66 files 포맷 어긋남 | clean (865 files) |
| `isort --check-only .` | 다수 파일 import 순서 어긋남 | clean |
| `flake8 --select=E9,F63,F7,F82` | clean | clean (변화 없음, 확인만) |

### 구체적 수정
1. **`pytest/test_battle.py` 디렉터리 제거** — 저장소 루트의 `pytest/`가 실제 `pytest` 패키지 이름과 충돌해 `python -m pytest` 실행을 완전히 깨뜨림.
2. **`requirements.txt`에 `cffi>=1.15.0` 추가** — `cryptography.hazmat.bindings._rust`가 이 환경에서 `_cffi_backend`를 요구, 누락 시 `crypto_trading`/`security` 관련 8개 테스트가 `pyo3_runtime.PanicException`으로 실패.
3. **`tests/test_combat_phase_fsm.py`의 `asyncio.get_event_loop().run_until_complete(...)` 5곳을 `asyncio.run(...)`으로 교체** — Python 3.11에서 스레드에 암묵적 이벤트 루프가 더 이상 생성되지 않아 발생하는 실패.
4. **`ci.yml`**: "pytest 실행 (전체)" 스텝에서 `--co`(collect-only) 플래그 제거 — 이 스텝은 지금까지 테스트를 수집만 하고 전혀 실행하지 않았음. `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` env var 추가, `python-lint-test` job의 의존성 설치에 `pytest-asyncio`/`pytest-timeout`/`pytest-mock` 추가(없으면 `async def` 테스트가 전부 실패).
5. **`sc2bot-ci.yml`**: `test` job이 존재하지 않는 `tests/unit`, `tests/integration` 경로를 가리켜 이 job이 (그리고 이후 모든 job이) 계속 즉시 실패하던 것을 실제 경로(`tests/`, `wicked_zerg_challenger/tests`)로 수정, protobuf env var 추가.
6. 66개 파일 `black`/`isort` 포맷 적용 (동작 변경 없음, 순수 포맷팅).

이 수정들은 열려있는 draft PR #352, #364 등이 독립적으로 이미 발견/수정한 것과 상당 부분 겹친다 — 의도적으로 재검증한 것이며, 어느 쪽이 먼저 머지되든 상관없다.

## 권장 조치 (사용자 승인 필요 — 이 세션은 병합/PR 종료 권한을 사용하지 않음)

1. **PR #364**("fix: repair the two CI pipelines that have been red on main for weeks")를 우선 검토 후 머지 권장. 가장 최근, 가장 근본원인 중심, 실제 의존성 설치 후 검증된 PR임.
2. #364 머지 후, 동일 문제를 다루는 나머지 draft PR(대략 #300~#363, `claude/optimistic-edison-*`)은 "superseded by #364"로 일괄 close 권장 — 이 저장소에는 여전히 150개 가까운 열린 draft가 남아있어 review 비용이 매우 큼.
3. **근본적으로**: 자동화 세션이 daily/hourly로 새 draft PR을 계속 여는 대신, (a) 기존 열린 PR 중 CI가 그린인 것을 우선 머지하거나, (b) 최소한 새 세션 시작 시 열린 PR 목록을 먼저 확인해 중복 재작업을 피하도록 지시할 것을 권장.
