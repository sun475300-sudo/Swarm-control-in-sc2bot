# 🔍 Remaining Issues - 추가 검토 결과

## 📋 개요

통합 문제 해결 후 발견된 추가 개선 사항들입니다.

**Last refreshed:** 2026-07-09 — 전면 재검증. 아래 이전 버전(2026-04-27)이 "open"으로
표시했던 항목(N1–N4, Issue #3, #4, #5, #6)은 실제 코드를 확인한 결과 **모두 이미 수정되어
있었으며, 문서만 갱신되지 않은 상태**였습니다. 자세한 확인 근거는 각 항목에 남겨둡니다.
(교훈: 다음 점검 사이클에서는 "open" 표시를 그대로 믿지 말고 코드로 재확인할 것 —
`PLAN-NIGHTLY.md` 2026-07-09 항목 참고.)

이번 사이클에서 실제로 새로 발견하고 고친 버그는 `PLAN-NIGHTLY.md`의 **P2.4** 항목 참고
(`RLAgent.save_experience_data()` 원자적 저장이 rename 실패 시 기존 파일을 지워버리는 문제).

---

## ✅ 모두 Resolved로 확인됨 (검증일: 2026-07-09)

| ID | 설명 | 검증 근거 |
|----|------|-----------|
| N1 | `OpponentModeling.on_step` 중복 정의 (F811) | `grep -n "def on_step" opponent_modeling.py` → 341번 줄 1건만 존재 |
| N2 | `EconomyManager._prevent_resource_banking` / `_reduce_gas_workers` 재정의 (F811) | 각각 1건씩만 존재 (economy_manager.py:3198, 3995) |
| N3 | `combat_manager._find_harass_target` 재정의 | 1건만 존재 (combat_manager.py:4992) |
| N4 | `production_resilience.build_terran_counters` 재정의 | 1건만 존재 (local_training/production_resilience.py:1961) |
| Issue #3 | Transfusion 우선순위 개선 필요 | `economy/queen_transfusion_manager.py`에 `HEAL_PRIORITY` 딕셔너리 기반 스마트 타겟팅 구현되어 있음 |
| Issue #4 | Resource Reservation Race Condition | `core/resource_manager.py`의 `ResourceManager.try_reserve()`가 `asyncio.Lock()`으로 정확히 이 패턴을 구현함 |
| Issue #5 | 중복 Position 계산 코드 | `utils/position_utils.py` 존재 |
| Issue #6 | 매직 넘버 | `config/constants.py` 존재 (EARLY_GAME_END_SECONDS 등 상수화됨) |
| TODO.md #1–#3, #7 (2026-01-25판) | 정찰 강화 / 견제 개선 / 확장 타이밍 | `PLAN-NIGHTLY.md` P1.1–P1.3 참고 — 완료 및 테스트 존재 |
| TODO.md #4 | 전투 로직 프레임 스킵 | `utils/frame_skip.py` + `tests/test_frame_skip_manager.py` 존재 |
| TODO.md #6 | 인코딩 에러 (⚪/✓ 등 특수문자) | `early_defense_system.py`, `build_order_executor.py`에 해당 문자 0건 |

플레이스홀더로 남아 있던 코드 예시(스마트 수혈, 자원 락, position utils, constants.py)는
실제 구현이 문서의 제안 코드보다 더 정교하게 되어 있어 별도 diff 없이 종료 처리합니다.

---

## 🟢 아직 열려 있는 항목 (LOW priority, 실질 영향 작음)

| ID | 설명 | 우선순위 | 비고 |
|----|------|---------|------|
| N5 | bare `except Exception:` 다수 (현재 460건, `/tests/` 제외) | 🟢 LOW | 대부분 방어적 코드. 일괄 치환은 위험 — 파일별 개별 검토 필요. |
| N6 | F841 unused local variables (현재 125건, `/tests/` 제외) | 🟢 LOW | 대부분 `visuals/`, `tools/` 프레젠테이션 코드. `utils/error_handler.py:126,149`의 `last_exception`은 실제 소스코드지만 단순 dead code(루프 내 `e`로 이미 로깅됨) — 동작에 영향 없음. |

두 항목 모두 낮은 우선순위 유지. 대규모 일괄 수정보다는 다른 작업 중 지나가면서 정리하는 것을 권장.

---

## 📝 참고 사항

### 현재 상태 (2026-07-09 검증)
- ✅ **테스트**: `wicked_zerg_challenger/tests/` 664 pass / 0 skip / 0 fail
- ✅ **정적 분석**: flake8 F811/F821/F823/F401/E999 — 사실상 clean (미사용 import 2건만)
- ✅ **위에 나열된 모든 "치명적/중요" 이슈**: 코드에 이미 반영되어 있음을 확인

### 다음 우선순위는 `PLAN-NIGHTLY.md`의 P2.2/P2.3 참고
(벤치마크 러너 — 실제 SC2 클라이언트 필요, 빌드오더 config 외부화 — 별도 세션 권장)

**검토 완료일**: 2026-07-09
