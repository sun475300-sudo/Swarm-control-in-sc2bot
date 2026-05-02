# SC2 지휘관봇 개선 백로그 (Iterative Improvements)

**Branch**: `claude/stoic-shannon-Pf1zz`
**Last updated**: 2026-05-02

이 문서는 반복적인 테스트/점검 사이클에서 식별된 개선 사항을
우선순위별로 정리한 라이브 리스트입니다. 작업 단위(=커밋)별로
체크박스를 갱신합니다.

---

## ✅ Cycle 1 — Test infrastructure stabilization

- [x] **Critical**: `wicked_zerg_challenger/utils/unit_helpers.py` 의
      `Units([], None)` fallback이 sc2 미설치 환경에서 `TypeError`
      유발 → `_empty_units()` 헬퍼 도입.
      *(tests/test_unit_helpers.py 4건 PASS)*
- [x] `tests/test_phase10_improvements.py::test_gas_overflow_threshold_lowered`
      봇의 실제 임계값(800)과 일치하도록 동기화.

---

## ✅ Cycle 2 — Coverage backfill (utils)

- [x] `wicked_zerg_challenger/tests/test_game_constants.py` 추가 — 23 케이스
      (FPS, supply 우선순위, 인젝트 쿨다운 = 640/22.4, 거리/HP 임계값
      순서, 변환 함수 round-trip 등 관계 검증).
- [x] `wicked_zerg_challenger/tests/test_position_utils.py` 추가 — 26 케이스
      (빈 입력 / 단일 / 다수, health=0 분모 보호, supply 가중,
      perimeter, clamp, bounding box 등).
- [x] `position_utils.py` 가 sc2 미설치 환경에서도 import 되도록
      `Point2` 경량 폴백 추가 — 단위 테스트가 sc2 없이 실행 가능.

## ✅ Cycle 3 — Manager robustness & code hygiene

- [x] `economy_manager.py`: 두 곳의 stale 한국어 docstring (`3000+ 가스`)
      현재 임계값(800)과 동기화. `_prevent_gas_overflow` docstring을
      `gas_overflow_prevention_threshold` 변수 + 한 호출당 6명 캡 명시.
- [x] `utils/unit_helpers.find_nearby_enemies`: 인자 `range`(builtin
      shadow) → `radius` 로 교체. 호출부 모두 positional이므로 무영향.
- [x] `tests/test_phase10_improvements.py`:
      `test_gas_overflow_threshold_in_sane_range` (500 ≤ T ≤ 2000) +
      `test_prevent_gas_overflow_noop_below_threshold` (임계 미만 시
      `bot.do` 호출 0회) 추가. sc2 미설치 환경에서는 자동 skip.

## 🚧 Cycle 4 — 추가 후보

- [ ] `queen_manager._heal_with_transfusion` 빌딩 수혈 루프 — 한 프레임
      내 같은 큐가 여러 빌딩 후보에 대해 distance 검사를 도는데, 시도
      실패 후에도 `last_transfuse_time` 갱신이 누락되지 않는지 확인.
- [ ] CI lint(black) 사전 디트레인 — main 브랜치의 다수 파일이 black
      포맷에서 어긋나 있어 PR마다 lint 실패가 비결정적. 이건 별도
      대규모 PR 필요 (현재 PR 범위 밖).

## 📦 Cycle 4 — Code quality / DRY

- [ ] `position_utils.get_center_position` 미사용처 (combat_manager,
      rally_point, harassment_coord) 마이그레이션 진행률 점검.
- [ ] 매직 넘버 잔존 위치 grep → constants 마이그레이션.

## 🔭 Cycle 5+ — Strategic / runtime

- [ ] Pathfinding 캐싱 효율 측정.
- [ ] Blackboard 업데이트 빈도 분석 (frame_cache 활용 가능 여부).
- [ ] Counter-build 시스템 회귀 시나리오 (mutalisk → spore, baneling → roach).

---

## Test environment notes

- `python -m pytest tests/` (root):  279 pass, 23 skip, 1 warn.
  `tests/test_security.py`, `tests/test_crypto_trading.py` 는 환경 의존
  (`_cffi_backend` 누락)으로 제외 — 봇 로직과 무관.
- `python -m pytest wicked_zerg_challenger/tests/` (sc2 미설치 시):
  234 pass, 39 skip. 5개 파일은 `import sc2` 가 collect-time 에 실패
  하므로 `--ignore` 사용.

## 작업 규칙

1. 각 사이클은 *테스트 작성 → 코드 수정 → 테스트 통과* 순서.
2. 사이클 종료 시 본 문서의 체크박스 갱신 + 커밋 + 푸시.
3. 새로 발견된 회귀/리스크는 다음 사이클 항목으로 추가.
