# SC2 Commander Bot — 개선 사항 마스터 리스트 (2026-05-15)

지속적인 자동 점검·테스트를 통해 식별한 개선 항목들. 우선순위는 영향 범위 ×
재현성으로 산정한다.

## 진행 상황 (2026-05-15)

| 단계 | 통과 | 실패 | 수집 오류 |
|:-----|:-----|:-----|:----------|
| 시작 시점 | 253 | 10 | 28 파일 |
| 1차 수정 후 | 263 | 0 | 28 파일 |
| 2차 수정 후 (sc2 스텁) | 661 | 0 | 0 |
| 3차 수정 후 (psutil/pyyaml) | 668 | 0 | 0 |
| 4차 수정 후 (black/isort) | 668 | 0 | 0 |
| 5차 수정 후 (opponent_modeling) | 668 | 0 | 0 |

루트 `tests/` 도 별도로 499 passed, 14 skipped (총 1,167 패스).

## 완료된 개선 사항

### A. 테스트 인프라 & 폴백 스텁 (완료)
- [x] **A1**: `utils/unit_helpers.py` — `Units([], None)` 가 `Units=None` 폴백
      환경에서 TypeError 를 일으키던 버그 수정. `_empty_units()` 헬퍼 추가.
- [x] **A2**: `tests/_sc2_stub/` — `burnysc2` 가 빌드 불가한 환경에서 테스트가
      수집되도록 `sc2`, `sc2.ids.{ability,unit_typeid,upgrade}_id`,
      `sc2.position`, `sc2.bot_ai`, `sc2.unit`, `sc2.units`, `sc2.data`,
      `sc2.main`, `sc2.player`, `sc2.maps` 스텁 패키지 제공.
- [x] **A3**: `combat/micro_combat.py::manage_lurker_positioning` — sc2 미설치
      환경에서 즉시 빈 set 을 반환하던 가드 제거. 이름 기반 매칭으로 단위 테스트
      가능.
- [x] **A4**: `combat/mutalisk_micro.py::get_regen_position` — `Point2` 가
      None 일 때 main_base/start_location 폴백이 도달 불가능하던 버그 수정.
- [x] **A5**: `build_order_system.py::_infer_zvt_action` — 업그레이드 토큰(`METABOLIC_BOOST`
      등)과 유닛 타입 식별자를 분리해 정확한 action 분류. `HIVE` 모프와 더
      많은 학습 유닛(MUTALISK, ULTRALISK, VIPER, …) 인식 추가.
- [x] **A6**: `early_defense_system.py` 폴백 `UnitTypeId` 에 SPINECRAWLER,
      SPORECRAWLER, EVOLUTIONCHAMBER 등 핵심 자원 보강.
- [x] **A7**: `build_order_system.py` 폴백 `UnitTypeId` 에 MARINE, BANELING,
      MUTALISK, BROODLORD 등 60여 종 ID 보강.
- [x] **A8**: `combat/micro_combat.py` 폴백 메타클래스 도입 — `getattr(StubIds, "X")`
      가 항상 의미있는 sentinel 을 반환하도록.
- [x] **A9**: `blackboard.py` — `Blackboard = GameStateBlackboard` 별칭 추가,
      `is_supply_block` 오타 수정, `should_expand` 가 미네랄 조건도 확인하도록 보강.
- [x] **A10**: 루트 `tests/conftest.py` 및 `wicked_zerg_challenger/tests/conftest.py`
      에서 sc2 스텁 패키지를 sys.path 에 자동 주입.
- [x] **A11**: 사전 존재하던 `game_analytics_system.py::_load_stats` 의 중복
      `except` 블록 + 잘못된 들여쓰기로 인한 `E999 IndentationError` 수정.
      CI 의 critical flake8 (E9,F63,F7,F82) 단계가 처음으로 통과.
- [x] **A12**: 저장소 전체 black 26.3.1 + isort 일괄 정리 (66 파일). CI 의
      `Lint & Type Check` 매트릭스 (3.10/3.11/3.12) 의 `black --check`,
      `isort --check-only` 단계 차단 해제.
- [x] **A13**: `opponent_modeling.py::on_step` 중복 정의 제거. 첫 번째 정의
      (line 341, 전체 추적) 이 두 번째 정의 (line 765, early-signal 만)
      에 의해 가려져 빌드오더/타이밍어택/테크 진행 추적이 무력화되어
      있던 버그 수정.

## 추가 점검 결과 (잔존 항목 — 후속 작업 후보)

### B. 컨벤션 / 시스템 무결성
- [ ] **B1**: 여러 모듈이 `try: from sc2 ... except ImportError: class UnitTypeId: pass` 라는
      비어 있는 스텁을 정의. 메타클래스 기반 sentinel 로 일관성 통일.
- [ ] **B2**: `scouting/advanced_scout_system_v2.py:1039` 의 메서드 시그니처
      `unit_type: UnitTypeId = UnitTypeId.OVERLORD` 는 sc2 미설치 시 클래스 본문
      파싱 단계에서 AttributeError. 메타클래스 적용으로 자동 해결 가능.
- [ ] **B3**: 28 개 테스트 파일이 직접 `from sc2.ids.unit_typeid import UnitTypeId`
      를 사용. 스텁 패키지로 해결되지만 향후 모듈별 폴백을 공통 헬퍼로 통합.

### C. 비즈니스 로직 후속
- [ ] **C1**: `should_expand` 의 미네랄 임계치 300 은 단순 휴리스틱. 게임 진행도
      (BO 진행률 + 동시 펜딩 확장) 와 결합한 더 정교한 판단 필요.
- [ ] **C2**: `_infer_zvt_action` 의 업그레이드 토큰 리스트는 일부만 등록.
      `knowledge_manager` 또는 `KnowledgeUpdater` 에서 자동 수집.
- [ ] **C3**: Mutalisk Magic Box / Stack point — `Point2` 가 None 인 경우의
      좌표 계산을 단위 테스트에 반영.

### D. CI / 환경
- [ ] **D1**: GitHub Actions CI 는 burnysc2 전체 설치를 가정 — 로컬 개발 환경
      (mpyq 빌드 불가) 대응 가이드 docs 에 추가.
- [ ] **D2**: `requirements-dev.txt` 에 `pytest-asyncio`, `pytest-mock`,
      `pytest-timeout` 명시적 고정 버전 포함 확인.

### E. 코드 품질
- [ ] **E1**: 184 디렉토리 중 핵심 SC2 봇 영역 외 다수 디렉토리는 빈 셀(placeholder).
      README 에 명확히 분리.
- [ ] **E2**: `early_defense_system.py` 의 폴백 `UpgradeId` 가 비어있어 `getattr`
      체인이 None 반환. 주요 업그레이드 키 사전 등록.
- [ ] **E3**: 잔존 F811 중복 정의 — 각각 동작상의 미묘한 차이를 검증한 뒤 정리:
      `combat_manager.py::_find_harass_target` (2814 vs 5014),
      `economy_manager.py::_prevent_resource_banking` (1691 vs 3275),
      `economy_manager.py::_reduce_gas_workers` (3408 vs 4099),
      `local_training/production_resilience.py::build_terran_counters`.
- [ ] **E4**: F841 미사용 지역 변수 ~100여 건 (대부분 `except Exception as e:` 의 `e`
      미사용). 보너스 작업.
