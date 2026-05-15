# 🔧 SC2 지휘관봇 — 점검 & 개선 백로그

자동 점검(테스트 → 분석 → 개선 → 커밋/푸시 반복) 사이클로 발견된 항목.

세션 시작: 2026-05-15
브랜치: `claude/stoic-shannon-fXFeQ`

---

## 📊 현재 테스트 상태

| 항목 | 값 |
|------|-----|
| 수집된 테스트 | 420 |
| **수집 차단(import 실패)** | 1 (test_queen_transfusion.py) |
| 통과 | 385 (수집 차단 이후) |
| 실패 (cryptography PyO3 패닉) | 7 |
| 통과 (의존성 우회) | 365 |
| 스킵 | 22~33 |

실행 명령: `python -m pytest tests/` (plain `pytest`는 uv-tool 격리로 plugin 미인식)

---

## 🔥 Critical: 실제 버그 (즉시 수정)

봇 프로덕션 동작에 영향을 주는 항목. Python은 동일 클래스 내 중복 메서드 정의 시 *후자가 전자를 덮어쓴다.* 즉 전자 구현이 전혀 실행되지 않는 dead code다.

| ID | 파일 | 라인 | 메서드 | 영향 |
|----|------|------|--------|------|
| C1 | `wicked_zerg_challenger/opponent_modeling.py` | 341 vs 765 | `on_step` | **풀 구현이 죽고 단순 구현만 실행됨** → 빌드오더 트래킹, 타이밍 공격 감지, 테크 추적, 블랙보드 업데이트 모두 미실행 |
| C2 | `wicked_zerg_challenger/economy_manager.py` | 1681 vs 3258 | `_prevent_resource_banking` | 자원 뱅킹 방지 로직 한쪽이 무시됨 |
| C3 | `wicked_zerg_challenger/economy_manager.py` | 3391 vs 4082 | `_reduce_gas_workers` | 가스 워커 감축 로직 중복 |
| C4 | `wicked_zerg_challenger/combat_manager.py` | 2809 vs 5005 | `_find_harass_target` | 견제 타깃 탐색 중복 |
| C5 | `wicked_zerg_challenger/local_training/production_resilience.py` | 1467 vs 1977 | `build_terran_counters` | 테란 카운터 빌드 중복 |

---

## 🟠 High: 테스트 인프라 (CI 신뢰성)

| ID | 파일/주제 | 문제 | 수정 방향 |
|----|-----------|------|----------|
| H1 | `tests/test_queen_transfusion.py` | top-level `from sc2.ids.unit_typeid import UnitTypeId` 가 모듈 부재 시 **수집 전체 차단** | 조건부 import + `pytest.importorskip` |
| H2 | `tests/test_crypto_trading.py` | `cryptography` 모듈 Rust 바인딩 PyO3 패닉 (`_cffi_backend` 부재) → 7건 실패 | `pytest.importorskip("cryptography")` + try/except |
| H3 | `tests/test_security.py` | 동일 (cryptography import 패닉) | 동일 패턴 |
| H4 | `pytest.ini` | 루트 pytest.ini가 testpaths=tests로 wicked_zerg_challenger 테스트는 발견 못함 | 별도 처리 또는 명시 |

---

## 🟡 Medium: 코드 품질

| ID | 항목 | 비고 |
|----|------|------|
| M1 | bare `except Exception:` 360+ 곳 (REMAINING_ISSUES.md N5) | 점진 개선 |
| M2 | F841 unused locals (presentation 등) | 점진 |

---

## ✅ 작업 순서

1. **Phase 1**: H1/H2/H3 — 수집 차단/PyO3 패닉 회피해서 테스트가 깨끗이 통과
2. **Phase 2**: C1 — opponent_modeling on_step 중복 해소
3. **Phase 3**: C2/C3 — economy_manager 중복
4. **Phase 4**: C4 — combat_manager 중복
5. **Phase 5**: C5 — production_resilience 중복
6. **Phase 6**: 전체 테스트 재실행 + 커밋/푸시
7. **다음 사이클**: 결과 점검 후 신규 발견 항목 처리
