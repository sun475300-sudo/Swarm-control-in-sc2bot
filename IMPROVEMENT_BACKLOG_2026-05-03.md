# SC2 지휘관봇 개선 백로그 - 2026-05-03

테스트 + 린트 + 정적 분석 결과로 식별된 대규모 개선사항 리스트입니다.
각 항목은 우선순위별로 분류되어 있으며 순차적으로 커밋/푸시합니다.

## 진단 결과 요약

| 항목 | 결과 |
|------|------|
| pytest 통과 | 305 |
| pytest 스킵 | 34 |
| pytest 실패 | 1 (`test_gas_overflow_threshold_lowered`) |
| black 미적용 파일 | 1 (`combat_manager.py`) |
| isort | clean |
| flake8 critical (E9/F7/F8) | clean |
| flake8 전체 경고 | 1737 |

## 우선순위 1 (즉시, CI 차단 가능)

- [x] **P1-1**: `test_gas_overflow_threshold_lowered` 어셔션 1000 → 800 동기화
  - 위치: `tests/test_phase10_improvements.py:319`
  - 코드는 이미 800으로 낮춰져 있음 (`gas_overflow_prevention_threshold = 800`)
  - 테스트 docstring/assertion이 stale
- [x] **P1-2**: `combat_manager.py` black 포맷 적용 (line 4341 trailing blank lines)

## 우선순위 2 (코드 품질 - 기계적 정리)

- [ ] **P2-1**: F541 f-string 미사용 placeholder 정리 (255건)
  - `f"text"` → `"text"` (정적 문자열에 f-prefix 불필요)
- [ ] **P2-2**: F841 사용 안 되는 `except X as e` 정리 (128건 in wicked_zerg_challenger)
  - 안전한 케이스: `except ... as e: pass/log without e` → `except ...: ...`
- [ ] **P2-3**: E741 모호한 변수명 `l` (22건)
  - `l` → `lvl` 등 명확한 이름

## 우선순위 3 (코드 품질 - 명확화)

- [ ] **P3-1**: W293 blank line whitespace (283건) - black 적용 시 일부 자동 해결
- [ ] **P3-2**: E712 `== True/False` → `is True/False` (42건, 대부분 테스트)
- [ ] **P3-3**: E501 줄 길이 102자 초과 (318건, 100자 한도)
- [ ] **P3-4**: F811 `math` redefinition (14건)

## 우선순위 4 (로직/성능 개선)

- [ ] **P4-1**: REMAINING_ISSUES.md Issue #3 - Transfusion 우선순위 개선
  - 고가 유닛(울트라/브루드로드) 우선 수혈
- [ ] **P4-2**: 가스 오버플로우 임계값 조정 검증 (이미 800으로 낮아짐, 효과 측정)
- [ ] **P4-3**: macro hatchery mineral threshold (이미 550, 추가 튜닝 여지)

## 진행 상태

P1 → P2 → P3 → P4 순서로 작업, 각 단계마다 커밋/푸시.
