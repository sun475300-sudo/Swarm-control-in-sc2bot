# SC2 Commander Bot — Improvement Backlog (대규모 리스트)

> 생성: 2026-05-07 — claude/stoic-shannon-07K5T 브랜치
> 출처: pytest 실행 + 모듈 import 스캔 + 정적 분석

이 문서는 사이클 단위로 갱신된다. 각 사이클은:
1. 테스트/스캔 → 발견 사항 추가
2. 우선순위 항목 fix → commit & push
3. 다음 사이클로 반복

---

## P0 — 차단(Blocking) 이슈 (즉시 수정)

### B1. `tests/test_queen_transfusion.py` — sc2 import guard 누락 → 전체 collection 차단
- 증상: `ModuleNotFoundError: No module named 'sc2'` → pytest collection 인터럽트
- 영향: **전체 테스트 스위트가 401개 collected에서 1 error로 멈춤**
- 수정: `try/except ImportError → pytest.skip(allow_module_level=True)` 패턴 적용
- 상태: ✅ 완료 (cycle 1)

### B2. `wicked_zerg_challenger/check_proxy.py` — 모듈 import 시 sys.exit() 호출
- 증상: `import wicked_zerg_challenger.check_proxy` → Windows 경로 검사 실패 → `sys.exit(1)`
- 영향: import-scan 도구 모두 강제 종료, 빌드/배포 자동화 깨짐
- 추가 버그: `logger.info("text:", value)` 잘못된 호출(여러 인자) — Python logger는 `%s` formatting 필요
- 수정: `if __name__ == "__main__":` 가드, logger 호출 정리
- 상태: ✅ 완료 (cycle 1)

### B3. `pytest.ini` — `timeout=60` 설정만 있고 `pytest-timeout` 의존성 없음
- 증상: `PytestConfigWarning: Unknown config option: timeout` 매 실행마다
- 영향: 타임아웃이 실제로 동작하지 않음. 무한루프 테스트 발생 시 멈춤
- 수정: `requirements-dev.txt`에 이미 `pytest-timeout>=2.1.0` 있지만 dev install 가이드/CI 동기화 필요
- 상태: ⏳

### B4. `pytest.ini` — `--disable-warnings`가 모든 경고 숨김
- 증상: DeprecationWarning이 보이지 않음. 향후 Python 업그레이드 시 갑자기 깨짐
- 수정: `--disable-warnings` 제거 또는 특정 카테고리만 필터
- 상태: ⏳

---

## P1 — 코드 품질

### Q1. wicked_zerg_challenger 패키지 구조 일관성
- `wicked_zerg_challenger/`에 `__init__.py` 없음 → 패키지 아니라 디렉토리. `from xxx import ...` 형태로 패키지 내부 import가 작동하려면 cwd가 디렉토리 안이어야 함
- 일부 파일은 `from wicked_zerg_challenger.combat...`로 import (외부 패키지처럼) — 일관성 없음
- 옵션 A: `__init__.py` 추가 + 모든 import 상대경로(`from .xxx`)로 통일
- 옵션 B: 그대로 두되 conftest나 entry point에서 `sys.path.insert(0, 'wicked_zerg_challenger')` 명확히
- 상태: ⏳ (대규모 작업, 사용자 결정 필요)

### Q2. `combat.spatial_query_optimizer` — wicked_zerg_challenger를 외부 모듈처럼 import
- `import wicked_zerg_challenger`가 cwd가 디렉토리 안일 때 실패
- 수정: 상대경로 import로 교체
- 상태: ⏳

### Q3. 모듈 내 `print()` 사용 (logger 대신)
- 봇 코드 곳곳에 `print()`. 로깅 일관성 망가짐
- 수정: logger로 교체
- 상태: ⏳ (스캔 필요)

### Q4. logger.info/error 잘못된 호출 패턴
- check_proxy.py에서 발견. 다른 파일에도 있을 가능성
- 수정: regex 스캔 후 일괄 정리
- 상태: ⏳ (스캔 필요)

---

## P2 — 테스트 커버리지

### T1. 35건 → 21건 → 더 많이 줄이기
- numpy 설치 후 14건 추가 통과 (35 → 21)
- 잔여:
  - sc2 관련: 6건 (sc2 패키지 미설치 → 무시 가능)
  - config.yaml 없음: 7건 (테스트용 fixture로 보강 가능)
  - p606_infra not importable: 4건 (실제 import 오류 디버깅 필요)
  - world_model not importable: 1건
  - Combat components not available: 1건
  - test_security skip: 1건 (config.yaml 의존)
  - pyupbit: 1건 (의도적 skip)
  - numpy 잔여: 1건
- 수정: skip 사유별 분류 후 우선순위 처리
- 상태: ⏳

### T2. test_p606_infra "not importable" 정밀 진단
- skip 메시지 "not importable" 너무 모호 → 어떤 import가 실패하는지 표시
- 수정: 실제 ImportError 메시지를 skip 사유에 노출
- 상태: ⏳

### T3. test_security가 config.yaml 의존
- config.yaml 없으면 skip → CI에서 매번 skip 됨 (보안 검사 실효성 0)
- 수정: 테스트용 sample_config fixture 사용
- 상태: ⏳

### T4. 커버리지 측정 자동화
- `pytest.ini`에 cov 옵션이 주석 처리됨
- 수정: `--cov=wicked_zerg_challenger --cov-report=term`을 활성화 (선택적, CI에서)
- 상태: ⏳

---

## P3 — CI / 인프라

### C1. requirements-dev.txt가 CI에 누락
- `ci.yml`은 `pip install flake8 pytest pytest-cov` (수동 나열)
- `pytest-asyncio`, `pytest-timeout`, `pytest-mock` 미설치 → async 테스트가 모두 fail
- 수정: `pip install -r requirements-dev.txt`로 일원화
- 상태: ⏳

### C2. ci.yml의 pytest 단계가 실제로 실패해도 빌드 통과
- `pytest tests/test_crypto_trading.py tests/test_security.py -v --tb=short || true`
- 어떤 실패도 무시됨 → CI 신뢰도 0
- 수정: `|| true` 제거, 실패 정책 정립
- 상태: ⏳ (정책 결정 필요)

### C3. sc2bot-ci.yml의 strict mypy/black/bandit이 main에서 통과 가능?
- MASTER_TODO에 따르면 거의 모두 fail 추정
- 수정: 변경 파일만 검사하도록 단계적 도입
- 상태: ⏳

### C4. fail-fast 정책 검토
- matrix에서 한 잡 실패가 모두 cancel → 디버깅 어려움
- 수정: `fail-fast: false`
- 상태: ⏳

### C5. lockfile 도입
- `requirements.txt` 핀 부족 → resolution-too-deep 발생 가능성
- 수정: pip-tools(`pip-compile`)로 `requirements.lock` 생성
- 상태: ⏳

---

## P4 — 봇 핵심 로직

### L1. opponent_modeling.py 등 다수 파일 import 오류
- 비-sc2 import 오류: 39건 (cwd가 wicked_zerg_challenger일 때 기준)
- numpy 의존, psutil 의존이 다수 (필수 의존성으로 빠진 것 같음)
- 수정: 전체 코드가 시스템 numpy 사용 → requirements 수동 검증
- 상태: ⏳

### L2. UnitTypeId AttributeError — sc2 stub의 OVERLORD 누락
- `bot_step_integration.py`, `wicked_zerg_bot_pro_impl.py`, `scouting/advanced_scout_system_v2.py`가 OVERLORD 사용 중인데 stub에 없음
- 수정: stub 위치 확인 후 OVERLORD/BANELING/MUTALISK 등 핵심 unit IDs 추가
- 상태: ⏳

### L3. local_training/scripts에 batch_trainer/replay_learning_tracker_sqlite 누락
- 일부 스크립트가 import할 모듈이 없음
- 수정: 모듈 위치 추적, 또는 deprecated 표시
- 상태: ⏳

---

## P5 — 문서/메타

### D1. README/CONTRIBUTING이 너무 분산
- 루트에 60+ 마크다운 (대부분 자동 생성된 보고서)
- `docs/history/`로 일부 이동되어 있으나 중복 多
- 수정: 캐논 문서 1개 + `docs/history/`로 정리
- 상태: ⏳

### D2. 구버전/실험 폴더 (지휘관bot*) 관리
- 30+ 디렉토리 (alpine, electron, ember, expo, flutter2 등) — 실험적 포팅?
- 사용 여부 불명확. 정리 필요
- 상태: ⏳ (사용자 결정)

---

## 사이클 진행 기록

### Cycle 1 — 2026-05-07
- ✅ B1 fix: test_queen_transfusion sc2 import guard
- ✅ B2 fix: check_proxy.py main guard + logger format
- 결과: pytest 372 passed → 405 passed (numpy install 후), 0 fail

### Cycle 2 — 2026-05-07
- ✅ B4: pytest.ini `--disable-warnings` 제거, 카테고리별 filterwarnings로 교체
- ✅ T2: test_p606_infra skip 사유에 모듈 경로 + 실제 ImportError 노출
- ✅ T3 (부분): test_combat_components 모듈-레벨 skip 분해 → 컴포넌트별 skipif. numpy 없는 환경에서 0 → 13 tests pass.
- ✅ T5 (신규): `world_model/__init__.py`가 존재하지 않는 심볼(`DreamerAgent`, `WorldModel`, `LatentImagination`, `demo`)을 import해 패키지 import 깨짐. 실제 정의된 `SC2WorldModel`, `DreamerActor` 등으로 교체.
- 결과: 405 passed → 406 passed (full suite, with numpy). CI 환경(numpy 없음)에서는 +13 tests recovered.

### Cycle 3 — 2026-05-07
- ✅ L2 fix: `scouting/advanced_scout_system_v2.py`의 `_assign_patrol(... unit_type=UnitTypeId.OVERLORD)` 기본값이 sc2 stub(빈 클래스) 환경에서 `AttributeError`로 클래스 정의 자체를 실패시켜 `bot_step_integration` 등 여러 모듈이 줄줄이 깨짐. 기본값을 `None`으로 바꾸고 함수 본문에서 fallback. import-scan AttributeError 1건 → 0건.
- 결과: 봇 핵심 모듈(combat_manager, economy_manager, opponent_modeling, intel_manager, bot_step_integration, scouting/advanced_scout_system_v2 등) 모두 sc2 stub 환경에서 import 가능. 76개 ModuleNotFoundError 잔존하나 모두 외부 라이브러리(numpy/sc2/torch 등) 의존이라 별도 환경 설정 작업.

### Cycle 4 — 2026-05-07
- ✅ T2 후속: `tests/test_p606_infra.py`가 존재하지 않는 클래스명(`FuzzTarget`, `ContractViolation`, `PackageType`, `ProfileMetric`)을 import 시도해 4건 skip. 실제 정의된 `SC2Fuzzer/FuzzInput`, `Contract/ContractStatus`, `Package/SBOMGenerator`, `Timer/CPUProfiler`로 교체.
- 코드 품질 스캔: bare except, mutable default args, eval/exec/shell=True/yaml unsafe load 모두 0 hits. except-pass 38건은 대부분 optional feature fallback 패턴.
- 결과: 406 passed → 410 passed, 20 skipped → 16 skipped.

### Cycle 5 — 2026-05-07
- ✅ T3: `tests/test_crypto_trading.py::TestConfigLoader`가 프로젝트 루트의 `config.yaml`이 없으면 클래스 전체 skip(7건). 임시 디렉토리에 `sample_config`로 yaml을 생성하는 fixture(`_temp_config_yaml`, `_config_loader`) 추가. 글로벌 캐시도 매 테스트마다 reset.
- ✅ T3: `tests/test_security.py::test_no_hardcoded_keys_in_yaml`도 같은 패턴으로 sample yaml 생성 후 검사. PyYAML 미설치는 importorskip로 자연스럽게 skip.
- 결과: 410 passed → 417 passed, 16 skipped → 9 skipped.

## 누적 진행
| Cycle | passed | skipped | 비고 |
|-------|--------|---------|------|
| Pre   |   0    |    -    | collection error로 차단 |
| 1     |  372   |   35    | 차단 해제 |
| 1+numpy | 405 |   21    | numpy 설치 효과 |
| 2     |  406   |   20    | world_model fix |
| 3     |  406   |   20    | sc2 stub fix (import-scan만 영향) |
| 4     |  410   |   16    | p606 클래스명 정정 |
| 5     |  417   |    9    | config.yaml fixture로 7건 회복 |
