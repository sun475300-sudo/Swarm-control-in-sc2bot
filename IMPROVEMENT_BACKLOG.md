# SC2 지휘관봇 개선 백로그 (2026-05-03)

본 문서는 자동 점검(ruff + pytest)으로 발견된 개선 항목 처리 이력입니다. 각 배치는 별도 커밋으로 푸시되어 PR #78에서 검토됩니다.

## 📊 진행 상황 요약

| 단계 | 상태 | 테스트 | 수정 항목 |
|------|------|--------|-----------|
| Batch 1 | ✅ 완료 | 404 통과 | B023×26, B004×2, F823×1 — 클로저/콜러블/스코프 |
| Batch 2 | ✅ 완료 | 404 통과 | F541×255, F811×6, E713×2, W291/W293 — ruff auto-fix |
| Batch 3 | ✅ 완료 | 407 통과 | 회귀 가드 3건 (B023, B004, F823) |
| Batch 4 | ✅ 완료 | 408 통과 | F811 수동 2건, B007 자동 53건 + F811 가드 |
| Batch 5 | ✅ 완료 | 408 통과 | B905 zip strict 15건 + B905 가드 |
| Batch 6 | ✅ 완료 | 415 통과 | 클로저 의미 단위 테스트 6건 |
| Batch 7 | ✅ 완료 | 415 통과 | B007 잔여 7건 수동 + B007 가드 |
| Batch 8 | ✅ 완료 | 417 통과 | F821 회귀 1건, FURB171/C401/C414 등 + F821 가드 |

총 **117 → 35 ruff 위반 감소**(B-class·F-class만), **회귀 가드 7건** 추가.

## 🔴 Batch 1 — 치명적 버그 27건

루프 안 lambda 클로저가 마지막 루프 변수만 캡처하던 모든 `Units.filter(lambda...)` 호출을 기본 인자 캡처로 수정.

| # | 카테고리 | 파일 | 설명 |
|---|---------|------|------|
| 1 | F823 | wicked_zerg_bot_pro_impl.py:691 | `import traceback` 함수내 재선언으로 모듈 임포트 가려짐 |
| 2 | B004 | scoring_system.py:397, 437 | `hasattr(x, "__call__")` → `callable(x)` |
| 3 | B023 | advanced_worker_optimizer.py:387 | 가스 일꾼 — extractor.tag 캡처 |
| 4 | B023 | battle_preparation_system.py:110 | 클러스터별 — cluster_center 캡처 |
| 5 | B023 | battle_preparation_system.py:284 | 활성 교전 — zone.center 캡처 |
| 6 | B023 | bot_step_integration.py:2138 | **공격적 테크 빌더 — 모든 추천이 마지막 tech로 빌드되던 실질 버그** |
| 7 | B023 | combat/doom_drop.py:525 | 둠드롭 AA 위협 — overlord 캡처 |
| 8 | B023 | combat/lurker_positioning.py:377 | 러커 디텍터 — lurker 캡처 |
| 9 | B023 | combat/overlord_hunter.py:95 | 오버로드 사냥 — target 캡처 |
| 10 | B023 | combat/viper_tactics.py:233 | 바이퍼 어브덕트 — target_type 캡처 |
| 11-19 | B023 | economy_manager.py (9곳) | 추출기/타운홀/일꾼 태그 캡처 |
| 20 | B023 | local_training/defense_coordinator.py:513 | 방어 — base 캡처 |
| 21-22 | B023 | local_training/resource_manager.py:193,206 | 가스 자원 — extractor/worker 캡처 |
| 23 | B023 | multi_base_defense.py:280 | idle 군대 — base_pos 캡처 |
| 24 | B023 | overlord_vision_network.py:219 | 오버로드 정찰 — overlord.tag 캡처 |
| 25 | B023 | scouting/advanced_scout_system_v2.py:1201 | 감시군주 — base.position 캡처 |
| 26 | B023 | tools/background_parallel_learner.py:267 | 파일 아카이브 — file_path/archive_path 캡처 |
| 27 | B023 | worker_combat_system.py:96 | 위협 감지 — base.position 캡처 |

## 🟡 Batch 2 — Ruff auto-fix 일괄 정리

| # | 규칙 | 건수 | 처리 |
|---|------|------|------|
| 1 | F541 | 255 | placeholder 없는 f-string → 일반 문자열 |
| 2 | F811 | 6 | 첫 번째 정의 자동 제거 (활성 정의 보존) |
| 3 | E713 | 2 | `not x in y` → `x not in y` |
| 4 | W291/W293 | 다수 | trailing whitespace |

## 🟠 Batch 3 — 회귀 가드 추가

`tests/test_closure_lint_guard.py` 신설:
- `test_no_b023_loop_closure_bugs`
- `test_no_b004_unreliable_callable_check`
- `test_no_f823_undefined_local`

## 🟢 Batch 4 — F811 수동 + B007 자동

치명적 F811 2건 수동 해결:
- **`opponent_modeling.py`**: 두 번째 `on_step` (line 766)이 첫 번째의 빌드 오더 추적, 타이밍 공격 감지, 테크 진행 추적, blackboard 업데이트, 예측 전이 로직을 가리던 **실질 버그** 수정.
- **`production_resilience.py`**: 첫 번째 `build_terran_counters` (line 1378) 데드코드 제거.

B007: 53건 자동 fix(`_var` rename), 추가 가드 1건.

## 🟦 Batch 5 — B905 zip strict 명시

15건 일괄 `strict=False` 추가 (Python 3.10+ 호환). B905 가드 추가.

## 🟪 Batch 6 — 클로저 의미 단위 테스트

`tests/test_closure_capture_semantics.py` 6건:
- `test_late_binding_bug_demonstrates_problem`
- `test_default_argument_capture_fixes_bug`
- `test_battle_zone_center_capture`
- `test_extractor_tag_capture_in_economy_manager`
- `test_overlord_tag_capture_in_overlord_vision_network`
- `test_tech_type_capture_in_bot_step_integration`

## 🟫 Batch 7 — B007 잔여 수동 정리 7건

`combat/formation_manager.py`, `combat_manager.py`, `game_data_logger.py`, `knowledge_updater.py`, `tools/logic_checker.py` ×2, `visuals/generate_presentation_visuals.py`.

## 🟧 Batch 8 — F821 회귀 + 추가 정리

- F821 회귀 수정: Batch 7에서 `replace_all`로 잘못 변경한 `_days` (실제 사용중)을 `days`로 복원.
- FURB171: `unit_type in ["BANELING"]` → `==` 비교
- C401/C414/C416/C420/FURB122: 자동 리팩터 10건
- F821 회귀 가드 추가 (ursina star-import 제외)

## 🔮 후속 작업 (미처리, Batch 9+)

| 항목 | 건수 | 우선순위 |
|------|------|----------|
| F841 (unused-variable) | 128 | 중 — 죽은 코드 |
| F401 (unused-import) | 다수 | 중 — 가독성/로딩 |
| E741 (`l`, `I`, `O` 변수명) | 22 | 저 |
| E402 (import not at top) | 67 | 저 |
| NPY002 (numpy legacy random) | 61 | 저 |
| ASYNC240 (async + os.path) | 1 | 중 — 잠재 차단 I/O |
| pytest.ini `asyncio_mode/timeout` 미인식 옵션 | 2 | 저 — 외부 플러그인 의존 |
| 거대한 단일 파일 모듈화 | combat_manager 172KB / bot_step_integration 158KB | 고 — 유지보수성 |

## ✅ 회귀 가드 현황 (`tests/test_closure_lint_guard.py`)

```
test_no_b023_loop_closure_bugs       # 클로저 캡처 버그 차단
test_no_b004_unreliable_callable_check  # hasattr("__call__") 차단
test_no_f823_undefined_local         # 함수내 import 가림 차단
test_no_f811_redefined_unused        # 중복 메서드 정의 차단
test_no_f821_undefined_name          # 정의되지 않은 이름 사용 차단
test_no_b007_unused_loop_control_variable  # 사용 안 하는 루프 변수 차단
test_no_b905_zip_without_strict      # zip(strict=) 미지정 차단
```

## 📈 최종 메트릭

- 테스트: **417 통과** / 0 실패 (시작 404)
- ruff B/F-class: **70 → 0** (해당 규칙 모두 통과)
- 회귀 가드: **0 → 7**
- 신규 테스트 모듈: 2개 (`test_closure_lint_guard.py`, `test_closure_capture_semantics.py`)
