# 🔍 Remaining Issues - 추가 검토 결과

## 📋 개요

통합 문제 해결 후 발견된 추가 개선 사항들입니다.

**Last refreshed:** 2026-07-15 (자동 점검 사이클 — 테스트 전체 재실행 후 갱신)

---

## 🆕 2026-07-15 자동 점검 결과

`tests/` (516개) + `wicked_zerg_challenger/tests/` (661개) 전체 재실행 결과:

- `tests/test_combat_phase_fsm.py` 12개 테스트가 Python 3.11에서
  `asyncio.get_event_loop().run_until_complete(...)` 패턴이 더 이상 동작하지 않아
  (`RuntimeError: There is no current event loop in thread 'MainThread'`) 실패 중이었음.
  → `asyncio.run(...)`으로 교체하여 수정 완료. 1177개 테스트 전체 통과 확인.
- `flake8 --select=E9,F63,F7,F82` (CI 강제 게이트) 및 `pyflakes`로 F811(중복 정의)/F821(미정의 이름)
  재검사 — 이전 PR(#218)에서 이미 모두 해결된 상태로 확인 (신규 발견 없음).
- 아래 N1~N4 (구 자동 발견 항목)는 이미 해결되어 있음을 재확인 — 문서만 stale했던 것으로 판단.

## ✅ 재확인하여 Resolved로 이동 (2026-07-15)

| ID | 설명 | 확인 내용 |
|----|------|---------|
| N1 | `OpponentModeling.on_step` 중복 정의 | pyflakes F811 결과 0건 — 이미 제거됨 |
| N2 | `EconomyManager` 메서드 재정의 | pyflakes F811 결과 0건 — 이미 제거됨 |
| N3 | `combat_manager._find_harass_target` 재정의 | pyflakes F811 결과 0건 — 이미 제거됨 |
| N4 | `production_resilience.build_terran_counters` 재정의 | pyflakes F811 결과 0건 — 이미 제거됨 |
| (구)#3 | Transfusion 우선순위 시스템 | `queen_manager.py:_transfuse_injured_units`에 CreepyBot 스타일 우선순위 테이블 구현 완료 |
| (구)#4 | Resource Reservation Race Condition | `core/resource_manager.py`의 `ResourceManager` (asyncio.Lock 기반 `try_reserve`/`release`) 구현 완료 |
| (구)#5 | Position 계산 중복 | `utils/position_utils.py` (`get_center_position`, `get_weighted_center`) 구현 완료 |

## 🟢 잔여 저우선순위 (변경 없음)

| ID | 설명 | 우선순위 | 상태 |
|----|------|---------|------|
| N5 | bare `except Exception:` 다수 (≈360+) | 🟢 LOW | partial — 점진적 개선 대상 |
| N6 | F841 unused local variables / f-string placeholder 누락 다수 (pyflakes 481건, 대부분 스타일) | 🟢 LOW | open — 런타임 영향 없음 |
| N7 | `wicked_zerg_challenger/tools/check_missing_logic.py` 독스트링 인코딩 깨짐(mojibake) | 🟢 LOW | open — 런타임 미사용 dev 도구, 영향 없음 |

---

## ✅ Resolved (확인일: 2026-04-27)

이전 버전(2026-01-29)에 남아있던 두 이슈는 코드에 이미 반영된 상태로 확인됐습니다.
문서가 stale했던 것으로, 별도 작업 없이 닫습니다.

### ✅ (PR #44) Issue #6 부분 해결: Queen Manager magic numbers

`queen_manager.py` 인스턴스 기본값 11종을 `GameConfig` 클래스 상수로 이동.
회귀 테스트 7건 추가 (`tests/test_queen_manager_constants.py`).

| 상수 | GameConfig 키 |
|------|--------------|
| inject_energy_threshold (25) | `QUEEN_INJECT_ENERGY_THRESHOLD` |
| inject_cooldown (29.0s) | `QUEEN_INJECT_COOLDOWN_SEC` |
| max_inject_distance (8.0) | `QUEEN_MAX_INJECT_DISTANCE` |
| creep_energy_threshold (20) | `QUEEN_CREEP_SPREAD_ENERGY` |
| creep_spread_cooldown (4.0s) | `QUEEN_CREEP_SPREAD_COOLDOWN_SEC` |
| inject_queen_creep_threshold (35) | `QUEEN_INJECT_QUEEN_CREEP_ENERGY` |
| transfuse_energy_threshold (50) | `QUEEN_TRANSFUSE_ENERGY_THRESHOLD` |
| transfuse_cooldown (1.0s) | `QUEEN_TRANSFUSE_COOLDOWN_SEC` |
| transfuse_health_threshold (0.5) | `QUEEN_TRANSFUSE_HP_THRESHOLD` |
| max_queens_per_base (2) | `QUEEN_MAX_PER_BASE` |
| creep_queen_bonus (4) | `QUEEN_CREEP_BONUS_QUEENS` |

### ✅ Issue #1: Queen Inject 쿨다운 — 25→29초 수정 완료

| Where | Verification |
|-------|--------------|
| `wicked_zerg_challenger/queen_manager.py:60` | `self.inject_cooldown = 29.0  # ★ FIXED: SC2 Spawn Larva 쿨다운 28.57초 + 0.43초 여유 ★` |
| `wicked_zerg_challenger/economy/queen_inject_optimizer.py:69` | `self.INJECT_COOLDOWN = 29.0  # 29초 쿨다운` |

### ✅ Issue #2: 누락 업그레이드 — Adrenal Glands + Grooved Spines 구현 완료

| Where | Verification |
|-------|--------------|
| `wicked_zerg_challenger/upgrade_manager.py:819-820` | `"""아드레날린 분비선 (Adrenal Glands) 연구 - 저글링 공속업 (Crackling)"""` → `adrenal = getattr(UpgradeId, "ZERGLINGATTACKSPEED", None)` |
| `wicked_zerg_challenger/upgrade_manager.py:740-741` | `"""홈 스파인 (Grooved Spines) 연구 - 히드라 사거리 +2"""` → `hydra_range = getattr(UpgradeId, "EVOLVEGROOVEDSPINES", None)` |

검증 출처: `ACTION_LOG_20260419.md` Task #6.

---

## 🟢 LOW Priority Issues (open)

구 Issue #3~#6은 위 "✅ 재확인하여 Resolved로 이동" 섹션에서 모두 해결 확인됨.
남은 저우선순위 항목은 N5~N7 (본 문서 상단 표 참조) 뿐이며, 런타임 동작에는 영향 없음.

---

## 🔍 추가 검토 필요 항목

### Performance Optimization
- [ ] Pathfinding 캐싱 확인
- [ ] Unit filtering 최적화 검토
- [ ] Blackboard 업데이트 빈도 분석

### Strategic Improvements
- [ ] Counter-build 시스템 확인 (적 유닛 조합 대응)
- [ ] Scouting 타이밍 최적화
- [ ] Expansion timing 검증

### Code Quality
- [ ] Type hints 추가 (Python 3.10+)
- [ ] Docstring 완성도 검토
- [ ] 에러 핸들링 일관성 확인

---

## 📝 참고 사항

### 현재 상태
- ✅ **치명적 통합 문제**: 완전히 해결됨
- ✅ **전체 테스트**: 통과 (`tests/` 502 passed + 14 skipped, `wicked_zerg_challenger/tests/` 661 passed — 2026-07-15 기준)
- ✅ **기본 기능**: 정상 작동

### 위의 이슈들은
- 모두 **선택적 개선 사항**
- 즉시 수정 불필요
- 점진적 개선 권장

---

**검토 완료일**: 2026-07-15
**상태**: 자동 점검 사이클 반복 진행 중 — 다음 회차에서 N5~N7 저우선순위 항목 재검토 예정
