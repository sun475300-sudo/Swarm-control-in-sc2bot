# SC2 지휘관봇 개선 작업 목록 (2026-05-15)

테스트 실행과 코드 점검을 통해 발견한 개선사항 종합 리스트.

## 🔴 Critical Bugs (테스트 차단)

### B1. `Blackboard` 별칭 누락 (blackboard.py)
- 증상: `from blackboard import Blackboard` 실패 → `wicked_zerg_bot_pro_impl.py` 임포트 실패
- 영향: `test_blackboard.py` 수집 단계에서 실패, `WickedZergBotProImpl` 로드 불가
- 해결: `blackboard.py` 끝에 `Blackboard = GameStateBlackboard` 별칭 추가
- 위치: `wicked_zerg_challenger/blackboard.py`

### B2. `test_sprint8_qa.py` 수집 실패 (run_mass_test 의존성)
- 증상: `run_mass_test` 임포트 시 sc2.main → portpicker 등 외부 런타임 필요
- 영향: Sprint8 QA 테스트 전부 스킵
- 해결: sc2 런타임 모듈을 lazy import 또는 `pytest.importorskip` 사용
- 위치: `wicked_zerg_challenger/tests/test_sprint8_qa.py`, `wicked_zerg_challenger/run_mass_test.py`

## 🟡 테스트 인프라

### T1. `pytest.ini`의 `asyncio_mode` 옵션
- 증상: pytest-asyncio 미설치 환경에서 `Unknown config option: asyncio_mode` 경고
- 해결: `asyncio` marker만 사용하고 `asyncio_mode`는 pytest-asyncio 설치 시에만 활성화 (조건부 설정)
- 위치: `pytest.ini`

### T2. 누락된 conftest 환경 변수
- 증상: `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION` 미지정 시 protobuf descriptor 에러
- 해결: 최상위 `conftest.py`로 끌어올려서 모든 테스트가 영향받게 함
- 위치: `wicked_zerg_challenger/tests/conftest.py`, 최상위 `conftest.py`

### T3. 테스트 실행 가이드
- 증상: README/SETUP_GUIDE에 mpyq 빌드 실패 등 의존성 이슈 미기재
- 해결: `SETUP_GUIDE.md`에 Linux/CI 환경에서의 mpyq 수동 설치 절차 명시

## 🟠 Blackboard 기능 일관성

### BB1. `production_queue`와 `request_production` 우선순위 동기화
- 현재: `production_queue`는 0~3 키만 가짐, 5 이상 priority 요청 시 KeyError 가능
- 해결: `request_production`에서 priority clamp 또는 동적 키 생성

### BB2. `building_reservations` 만료 처리
- 현재: 건설 예약이 시간만 저장, 만료 자동 청소 안 됨
- 해결: `cleanup_expired_reservations(now, ttl)` 메서드 추가

### BB3. 캐시 TTL 키별 설정 정합성
- 현재: `_cache_ttls`는 있지만 `set_cache(key, value, ttl=...)` 인터페이스 부재
- 해결: TTL 인자 받는 cache setter 추가

## 🟢 코드 품질 / 정합성

### CQ1. `chat_manager.py` 거의 비어있음 (114 bytes)
- 조치: 최소한의 ChatManager 스텁이라도 갖춰서 임포트 안전성 확보

### CQ2. `intel_manager_check.txt` 0바이트 파일
- 조치: 삭제 또는 placeholder 명시

### CQ3. `improvement_log.txt` 등 추적 파일 정리 정책 필요
- 조치: `.gitignore`에 패턴 추가 또는 `archive/` 폴더로 이동

## 🔵 봇 로직 개선 (게임 플레이)

### G1. 정찰 사이클 다양화
- `phase_scout_cadence.py`에 TODO 표시된 P1.1 작업 마무리
- 단계별(OPENING/EARLY/MID/LATE) 정찰 단가 차등화

### G2. 적 빌드 식별 패턴 확장
- `opponent_modeling.py`에 ZvT/ZvP/ZvZ 메타 빌드 시그니처 추가
- 빌드 확률 가중치 동적 학습

### G3. 견제 효율성 측정 메트릭
- `harassment_extension.py`에 일꾼 킬 카운트와 자원 손실 추정 메트릭 추가

### G4. 인젝트 자동화 견고성
- `queen_manager.py`의 인젝트 사이클 누락 방지 (해처리 idle 감지 강화)

### G5. 점막 확장 최적화
- `creep_expansion_system.py`의 종양 우선 위치 휴리스틱 개선 (적 위협 가중치 반영)

## 🟣 성능

### P1. `combat_manager.py` (199KB) 분할
- 매 프레임 호출되는 hot path 식별 후 모듈 분리

### P2. `economy_manager.py` (182KB) 분할
- 자원 채취/일꾼 배정/확장 결정 모듈로 분리

### P3. 프레임 스킵 매니저 활용 확대
- `frame_skip_manager.py`를 더 많은 비핵심 시스템에 적용

## ⚪ 문서 및 빌드

### D1. README_BOT.md 최신화
- 현재 의존성 설치 가이드가 mpyq 빌드 실패에 대한 회피책 누락

### D2. ARCHITECTURE.md 최신 모듈 반영
- Sprint 7/8 구조 변경 반영

### D3. `.dashboard_port` 등 런타임 산출물 분리
- 산출물 → `runtime/` 디렉토리 격리

---

## 작업 순서 (이 세션에서 진행)

1. ✅ B1: Blackboard 별칭 추가 — 테스트 즉시 통과
2. ✅ T2: 최상위 conftest 환경 변수
3. ✅ T1: pytest-asyncio 없을 때 경량 async 러너
4. ✅ B2: sprint8_qa lazy import / importorskip
5. ✅ BB1: production_queue 우선순위 clamp
6. ✅ BB2: 건설 예약 만료 청소
7. ✅ CQ2: intel_manager_check.txt 0바이트 파일 정리
8. ✅ phase_scout_cadence `_infer_enemy_main` 빈 리스트 반환 결함 수정 + 12개 테스트
9. ✅ sc2_coach 패턴 10개 → 20개 확장 + 19개 테스트
10. ✅ game_constants 회귀 가드 테스트 18개
11. ✅ frame_cache `cached_per_frame` kwargs 키 누락 결함 수정 + 10개 테스트
12. ✅ adaptive_build 단위 테스트 13개
13. ✅ common_helpers 단위 테스트 27개 + logger dead code 제거
14. ✅ error_handler 단위 테스트 19개 + retry_on_failure dead var 제거
15. ✅ personality_module 단위 테스트 14개

### 누적 결과

#### 수정한 결함

- B1: `Blackboard` 별칭 누락 → `wicked_zerg_bot_pro_impl` 임포트 실패
- B1.1: `should_expand` 미네랄 미체크 + `is_supply_block` 오타
- B2: `run_mass_test` 모듈 임포트 시 SC2 런타임 강제 의존
- BB1: `request_production`의 priority KeyError 가능성
- BB2: `building_reservations`가 무한 누적
- phase_scout_cadence: `_infer_enemy_main`이 빈 리스트를 None 대신 반환
- frame_cache: `cached_per_frame`이 kwargs를 캐시 키에 미포함
- logger: setup_logger에 의미 없는 `pass` dead code
- error_handler: `retry_on_failure` 안의 미사용 `last_exception` 변수
- **proxy_detector: factory/starport 프록시 탐지 누락** (ProxyType과 분리)
- **meta_game_analyzer: race/map_performance.losses 절대 갱신 안됨**
- **map_manager: `_load_stats`가 self.logger 사용 전 호출되어 손상 JSON 시 크래시**
- sc2_coach: 코칭 패턴 10 → 20개 확장 (점막/은폐/업그레이드/런바이/올인/라바)

#### 추가한 테스트 (14개 파일, 약 195개 테스트)

- test_phase_scout_cadence.py (12)
- test_sc2_coach.py (19, repo 루트)
- test_game_constants.py (18)
- test_frame_cache.py (10)
- test_adaptive_build.py (13)
- test_common_helpers.py (27)
- test_error_handler.py (19)
- test_personality_module.py (14)
- test_adaptive_learning_rate.py (11)
- test_scoring_system.py (10)
- test_proxy_detector.py (13)
- test_meta_game_analyzer.py (18)
- test_map_manager.py (11)
- test_unit_authority_manager.py (14)
- test_micro_focus_mode.py (15)

#### 테스트 통과 수

- 작업 전: 604개
- 작업 후: **870개** (+266개)
- 모든 신규 테스트는 SC2 런타임 없이 실행 가능 (stub 기반)

### 남은 항목 (다음 세션)

- CQ1: chat_manager 스텁을 실제 매니저 또는 더 강한 가드로 채움
- G1~G5: 봇 로직 개선 (정찰 사이클, opponent modeling, 견제, 인젝트, 점막)
- P1~P3: combat_manager / economy_manager 분할, frame_skip 적용 확대
- D1~D3: README/ARCHITECTURE 최신화, 런타임 산출물 분리
- CI 측 black/isort: main 자체에 67개 미정형 파일이 있어 lint job이
  지속적으로 fail 중. 이 PR 범위 외이므로 별도 정리 PR이 필요.
