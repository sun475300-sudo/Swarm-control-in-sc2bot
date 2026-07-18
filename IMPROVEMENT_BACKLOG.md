# WickedZergBotPro Improvement Backlog

> 생성: 자동화 테스트/점검 세션 (반복 작업용 대규모 리스트)
> 목적: `ROADMAP.md`는 Sprint 1~8 항목이 이미 대부분 코드에 구현되어 있음이
> 확인됨 (아래 "ROADMAP 검증 결과" 참고). 이 문서는 다음 반복 세션에서
> 우선적으로 작업할 실제 결함/개선 사항을 모아둔 백로그다.

## 이번 세션에서 완료한 작업

1. **테스트 인프라 복구** — `burnysc2`(sc2) 미설치로 `tests/`가 전혀 실행되지
   않는 상태였음. Debian의 `setuptools`/`wheel`이 `mpyq` 빌드에서 깨지는
   문제를 사용자 site-packages에 최신 `setuptools`/`wheel`을 설치하고
   `pip install --no-build-isolation`으로 우회하여 해결. 전체
   `requirements.txt`(crypto/discord/aws 등 무관한 의존성 포함) 대신 SC2
   관련 패키지만 설치하는 편이 훨씬 빠름 — 아래 "CI/개발환경" 항목 참고.
2. **`tests/test_combat_phase_fsm.py`**: `asyncio.get_event_loop()`가
   Python 3.11에서 메인 스레드에 실행 중인 루프가 없으면 예외를 던짐
   (`RuntimeError: There is no current event loop`). `asyncio.run(...)`으로
   교체하여 12개 테스트 실패를 수정.
3. **`crypto_trading`/`cryptography` 임포트 실패**: `_cffi_backend` 누락으로
   `cryptography.fernet` 임포트 시 Rust 바인딩이 패닉. `cffi` 설치로 해결
   (테스트 8개).
4. **버그: 러커가 적 사거리 안에서도 잠복 공격을 하지 않음**
   (`wicked_zerg_challenger/combat/formation_tactics.py` `BurrowController`).
   `_handle_unburrowed_unit`에 `enemy_units`가 전달되지 않아 러커 잠복 로직이
   `pass`로 죽어있었음 (ROADMAP Task 4.1). 호출부에서 `enemy_units`를
   전달하도록 수정하고 사거리 9 이내 적 감지 시 잠복하도록 구현.
   회귀 테스트: `wicked_zerg_challenger/tests/test_burrow_controller.py`.
5. **버그: 다각도 협공(Phase 21)에서 저글링 런바이/뮤탈 견제가 실제로
   발동하지 않음** (`combat/harassment_coordinator.py`). `_trigger_zergling_runby`
   / `_trigger_mutalisk_harassment`가 빈 placeholder였음 —
   `coordinate_multi_angle_attack`이 조건은 체크하고 로그도 남기지만 실제
   유닛은 전혀 움직이지 않았음. 기존에 구현되어 있던
   `_manage_zergling_runby` / `_manage_mutalisk_harassment`를 호출하도록 연결.
   회귀 테스트: `tests/test_harassment_coordinator.py::test_multi_angle_attack_triggers_real_runby_and_mutalisk_logic`.

테스트 결과: `tests/` 503 passed / 14 skipped (0 failed),
`wicked_zerg_challenger/tests/` 665 passed (0 failed). 총 1168개 테스트 통과.

## ROADMAP 검증 결과 (Sprint 1~8)

`ROADMAP.md`에 나열된 Task 1.1~8.2를 실제 소스와 대조한 결과, 문서 상단의
"Phase 56 완료, 342/342 테스트 통과"라는 상태 요약은 **크게 낡은 정보**다.
현재 테스트는 1168개이고, grep으로 확인한 결과 거의 모든 Sprint 항목이 이미
구현되어 있음 (`respond_to_worker_harassment`, `harass_units` 태그 시스템,
`OVERLORD_SCOUT_INTERVAL_*`, `BUILD_PATTERNS`(25개 패턴), `AIR_THREAT_INCOMING`,
`CLOAK_UNITS`, `ThreatLevel`, `_get_gas_timing_by_matchup`, `spend_larva`,
`micro_combat.py`/`mutalisk_micro.py`/`base_defense.py`, `manage_combat` 프레임
스킵, `use_rl_micro`, `building_manager.py`, `utils/distance_cache.py`,
`utils/game_constants.py` 모두 존재).

**액션 아이템**: `ROADMAP.md` 상단 상태 요약과 각 Task를 "완료"로 갱신하고,
아직 실전 검증(Sprint 8: Medium AI 30연전, AI Arena 패키지 검증)이 안 된
항목만 남겨서 문서를 최신화할 것. `TODO.md`도 2026-01-25/26 기준으로 멈춰
있고 이미 끝난 항목(정찰 강화, 견제 시스템, 1분 멀티 등)을 "우선순위 높음"
으로 잘못 표시하고 있음 — 삭제 또는 `docs/history/`로 이동 대상.

## 우선순위 높음 — 다음 세션에서 먼저 확인/수정

1. **테스트 격리 버그**: `tests/test_harassment_coordinator.py`를 단독으로
   실행하면 (`pytest tests/test_harassment_coordinator.py`) `utils.logger`
   모듈을 찾지 못해 23개 테스트가 전부 skip된다. 전체 스위트(`pytest tests/`)
   로 실행할 때만 다른 테스트 파일이 먼저 `sys.path`에
   `wicked_zerg_challenger/`를 직접 추가해 놓아서 우연히 통과함. 근본 원인은
   `wicked_zerg_challenger/combat/harassment_coordinator.py`가
   `from utils.logger import get_logger` 처럼 패키지 프리픽스 없이 임포트하는
   것 — `wicked_zerg_challenger`가 sys.path에 있어야만 동작. `tests/conftest.py`
   에 `wicked_zerg_challenger/`를 sys.path에 추가하는 fixture를 넣거나, 내부
   임포트를 전부 `wicked_zerg_challenger.utils.logger`로 통일해야 함. 이런
   패턴의 테스트가 더 있을 가능성 높음 — 전수 조사 필요.
2. **예외 스위칭(silent except) 다수 존재**: `combat_manager.py`에만
   `except ... as e:` 후 `e`를 로그에 쓰지 않고 버리는 코드가 30곳 이상
   (`bot_step_integration.py` 13곳 등). AI Arena에서 크래시 대신 조용히
   기능이 죽어버리는 원인이 될 수 있음. 최소한 `logger.debug(f"...: {e}")`
   정도로 남기는 일괄 수정이 필요 (flake8 `F841` 목록 참고, 아래).
3. **CI/개발환경**: `.github/workflows/sc2bot-ci.yml`의 `test` job이
   `pip install -r requirements.txt`로 crypto/discord/AWS 등 SC2와 무관한
   전체 의존성을 설치함 (수십 개 패키지, 이번 세션에서 9분 넘게 걸리다 타임아웃).
   `requirements-crypto.txt`처럼 `requirements-sc2.txt`를 분리해서 SC2 CI는
   그것만 설치하도록 바꾸면 CI 시간이 크게 줄어들 것. 또한 `tests/unit`,
   `tests/integration` 경로를 참조하는데 실제로는 `tests/`에 직접 테스트
   파일이 있고 `tests/integration/`만 하위 폴더로 존재함 —
   `pytest tests/unit -v` 스텝이 존재하지 않는 디렉터리를 가리켜 CI가 실패할
   가능성이 있음 (`tests/unit` 폴더 부재 확인 필요).

## F841 (사용되지 않는 지역 변수) 정리 — 잠재적 죽은 로직 후보

`flake8 --select=F841`로 `wicked_zerg_challenger/` 전체(테스트/로컬훈련
제외)에서 100개 이상 발견. 대부분은 `except ... as e` 스타일의 무해한
케이스지만, 다음은 실제로 "계산했지만 안 쓰는" 값이라 로직 버그일 가능성이
있어 직접 확인이 필요함:

- `combat_manager.py` — 31곳 (가장 많음, 전투 로직 핵심 파일이라 우선 검토)
- `bot_step_integration.py` — 13곳
- `economy_manager.py:326` `early_window` — `_get_early_scout_pressure_state()`
  에서 계산만 하고 `pressure_active` 산출에 반영되지 않음. 게임 후반까지
  "초반 정찰 압박" 상태가 스테일하게 유지될 가능성 있음 (의도적 완화인지
  버그인지 게임 플레이 테스트로 확인 필요 — 확신 없어 이번 세션에서는
  수정하지 않음).
- `economy_manager.py:3523` `minerals` — `check_economic_recovery()`에서
  미네랄 값을 읽어오지만 이후 로직에서 쓰지 않음.
- `creep_manager.py:280` `spread_range` — `TUMOR_SPREAD_RANGE`를 지역변수로
  받아오지만 실제 후보 위치 생성은 하드코딩된 `[7.0, 9.0]` 링을 사용.
- `combat/multiprong_attack.py:341`, `combat/stutter_step_kiting.py:195`
  `map_center` — 계산 후 미사용.
- `idle_unit_manager.py:229` `main_base` — 미사용이지만 실제로는 더 나은
  대안(`closest_to(unit)`)을 이미 쓰고 있어 버그 아님, 단순 정리 대상.
- `combat_manager.py:3490` `non_combat_names` — 선언만 하고 필터링에 미사용,
  로직 자체는 이미 다른 방식(`combat_unit_names` 매칭)으로 정상 동작. 정리
  대상.

각 파일을 하나씩 열어서 "계산한 값이 진짜 안 쓰여도 되는지" 확인 후, 죽은
코드면 삭제, 원래 의도된 로직이면 연결하는 식으로 처리할 것 (이번 세션에서
고친 러커 버로우 버그와 동일한 패턴).

## 기타 (낮은 우선순위)

- `wicked_zerg_challenger/tools/*.py`에 `placeholder` 로그만 찍는 스텁이
  20개 이상 존재 (`auto_git_push.py`, `check_win_rate.py`,
  `check_crash_log.py` 등). 실제로 쓰이는지 확인 후 미사용이면 삭제, 쓰인다면
  구현.
- `monitoring/*.py`도 다수 placeholder (ngrok, manus_sync 등) — 모바일
  앱/원격 모니터링 관련 기능으로 SC2 봇 승률과 무관, 우선순위 낮음.
- 루트에 47개 이상의 역사적 `*.md` 보고서가 쌓여 있음 (`STATUS.md`에서 이미
  `docs/history/`로 이동 계획을 언급함, `PLAN-NIGHTLY.md` P1.5). 아직
  실행되지 않음 — 저장소 탐색성을 위해 다음 세션에서 처리 고려.

## Sprint 8 — 아직 실전 검증되지 않은 것으로 보이는 항목

- Task 8.1: Medium AI 30연전 테스트(ZvT/ZvP/ZvZ 각 10판) — 실제 SC2 클라이언트
  필요, 이 세션(헤드리스 컨테이너)에서는 실행 불가. 로컬/GPU 러너에서 실행
  필요.
- Task 8.2: `create_arena_package.py` 최종 체크리스트 — ZIP 크기, 320ms/step
  타임아웃 등 실측 필요.
