# SC2 지휘관봇 개선 백로그 (2026-05-03 발견)

본 문서는 자동 점검(ruff + pytest) 통과 후 발견된 개선 항목 목록입니다.
배치 단위로 처리하여 커밋·푸시·재점검을 반복합니다.

## 🔴 Batch 1 — 치명적 버그 (이번 커밋에서 수정 완료)

| # | 카테고리 | 파일 | 설명 |
|---|---------|------|------|
| 1 | F823 | wicked_zerg_bot_pro_impl.py:691 | `import traceback` 함수내 재선언으로 모듈 상위 임포트 가려짐 → 같은 함수의 line 574 traceback 참조 시 UnboundLocalError 위험 |
| 2 | B004 | scoring_system.py:397, 437 | `hasattr(x, "__call__")` → `callable(x)` (PEP 더 안전) |
| 3 | B023 | advanced_worker_optimizer.py:387 | 가스 일꾼 줄이기 — 루프 변수 클로저 캡처(extractor.tag) |
| 4 | B023 | battle_preparation_system.py:110 | 클러스터별 아군 검색 — cluster_center 캡처 |
| 5 | B023 | battle_preparation_system.py:284 | 활성 교전 관리 — zone.center 캡처 |
| 6 | B023 | bot_step_integration.py:2138 | 공격적 테크 빌더 — tech_type 캡처 (모든 추천이 마지막 tech로 빌드되던 버그) |
| 7 | B023 | combat/doom_drop.py:525 | 둠드롭 AA 위협 감지 — overlord 변수 캡처 |
| 8 | B023 | combat/lurker_positioning.py:377 | 러커 디텍터 감지 — lurker 변수 캡처 |
| 9 | B023 | combat/overlord_hunter.py:95 | 오버로드 사냥 — target 캡처 |
| 10 | B023 | combat/viper_tactics.py:233 | 바이퍼 어브덕트 — target_type 캡처 |
| 11-19 | B023 | economy_manager.py (9곳) | 추출기/타운홀/일꾼 태그 클로저 캡처 |
| 20 | B023 | local_training/defense_coordinator.py:513 | 방어 — base 캡처 |
| 21-22 | B023 | local_training/resource_manager.py:193,206 | 가스 자원 — extractor/worker 캡처 |
| 23 | B023 | multi_base_defense.py:280 | idle 군대 이동 — base_pos 캡처 |
| 24 | B023 | overlord_vision_network.py:219 | 오버로드 정찰 배치 — overlord.tag 캡처 |
| 25 | B023 | scouting/advanced_scout_system_v2.py:1201 | 감시군주 배치 — base.position 캡처 |
| 26 | B023 | tools/background_parallel_learner.py:267 | 파일 아카이브 — file_path/archive_path 캡처 |
| 27 | B023 | worker_combat_system.py:96 | 위협 감지 — base.position 캡처 |

**검증:** `ruff check --select=B023,B004,F823` → All checks passed.
**테스트:** 404개 통과 / 0 실패 / 134 외부 라이브러리 경고만.

## 🟡 Batch 2 — 코드 품질·정합성

- pytest.ini의 미인식 옵션 `asyncio_mode`, `timeout` (PytestConfigWarning) → pytest-asyncio·pytest-timeout 설치 필요 또는 제거
- F841 (사용되지 않는 변수) 128건 — 죽은 코드 정리
- F401 (미사용 임포트) 355건 → 가독성·로딩 시간 개선
- F541 (placeholder 없는 f-string) 255건 → `f"..."` → `"..."` 단순화
- E741 (모호한 변수명 `l`, `I`, `O` 등) 22건
- F811 (중복 정의) 8건
- E713 (`not x in y` → `x not in y`) 2건

## 🟠 Batch 3 — 테스트 커버리지 확대 (이번 커밋)

- ✅ `tests/test_closure_lint_guard.py` 추가 — ruff 기반 회귀 가드 3건
  - `test_no_b023_loop_closure_bugs` — 클로저 캡처 버그 재유입 차단
  - `test_no_b004_unreliable_callable_check` — `hasattr("__call__")` 차단
  - `test_no_f823_undefined_local` — 함수내 모듈 재임포트로 인한 가림 차단
- 테스트 수: 404 → 407 통과
- 향후 작업 (Batch 4+):
  - `scouting/advanced_scout_system_v2.py` — 클래스 정의시 default 값 평가 테스트
  - 가스/타운홀 일꾼 재분배 시나리오 통합 테스트
  - F811 잔여 2건 수동 정리 (opponent_modeling.py, production_resilience.py)

## 🟢 후속 (작업 진행 중 추가)

- B007 (사용 안 하는 루프 변수) 60건 → `_` 로 변경
- B905 (zip strict 미지정) 15건 → strict=True/False 명시
- E402 (모듈 임포트 위치) 69건
- 거대한 단일 파일(combat_manager.py 172KB, bot_step_integration.py 158KB) → 모듈화 검토
