# 🔍 Remaining Issues - 추가 검토 결과

## 📋 개요

통합 문제 해결 후 발견된 추가 개선 사항들입니다.

**Last refreshed:** 2026-07-08 (자동 점검 사이클 — N1-N4, Issue #3/#4/#5 재검증 결과 모두 이미 코드에 반영됨을 확인. 문서만 stale했음.)

---

## ✅ 재검증 결과 (2026-07-08) — 이미 코드에 반영되어 문서만 stale했던 항목

`flake8 --select=F811` 로 재검사한 결과 아래 항목은 모두 중복 정의가 **없음**을 확인했다
(이전 세션에서 이미 고쳤으나 이 문서가 갱신되지 않았던 것):

| ID | 설명 | 확인 결과 |
|----|------|---------|
| N1 | `OpponentModeling.on_step` 중복 정의 | ✅ `opponent_modeling.py`에 `on_step` 정의 1개만 존재 |
| N2 | `EconomyManager._prevent_resource_banking` / `_reduce_gas_workers` 재정의 | ✅ 각각 1개 정의만 존재 |
| N3 | `combat_manager._find_harass_target` 재정의 | ✅ 1개 정의만 존재 |
| N4 | `production_resilience.build_terran_counters` 재정의 | ✅ 1개 정의만 존재 |
| Issue #3 | Transfusion 우선순위 시스템 | ✅ `queen_manager.py`의 `TRANSFUSE_PRIORITY` 딕셔너리로 구현됨 |
| Issue #4 | Resource Reservation Race Condition | ✅ `core/resource_manager.py`에 `asyncio.Lock` + `try_reserve()`로 구현됨 |
| Issue #5 | Position 계산 코드 중복 | ✅ `wicked_zerg_challenger/utils/position_utils.py`로 이미 분리됨 |

## 🆕 이번 사이클에서 새로 발견/수정한 항목 (2026-07-08)

| ID | 설명 | 우선순위 | 상태 |
|----|------|---------|------|
| N7 | `tests/test_combat_phase_fsm.py`가 `asyncio.get_event_loop().run_until_complete()`를 사용 — 같은 프로세스에서 `asyncio.run()`을 먼저 호출하는 다른 테스트(`test_matchup_strategies.py`) 뒤에 실행되면 전역 이벤트 루프 정책이 `None`으로 리셋되어 `RuntimeError: There is no current event loop` 발생 (테스트 격리 실패, full-suite에서만 재현) | 🔴 HIGH | ✅ Fixed — `asyncio.run()`으로 교체 |
| N8 | `RLAgent.save_model()` — tmp 경로를 `save_path.with_suffix(".tmp")`로 만들었는데 `np.savez()`가 `.npz`가 안 붙은 파일명에 자동으로 `.npz`를 붙여써서 실제 파일은 `*.tmp.npz`로 생성됨. 그 결과 `if tmp_path.exists():` 체크가 항상 False가 되어 **모델 저장이 조용히 아무것도 하지 않았음** (return True + 성공 로그를 남기지만 실제로는 파일이 갱신되지 않음) | 🔴 HIGH | ✅ Fixed — tmp 경로에 명시적으로 `.npz`를 붙이고 `os.replace()`로 원자적 교체 |
| N9 | `RLAgent.save_experience_data()` / `save_model()` — "atomic write"라고 주석에 적혀 있었지만 실제로는 `remove()` 후 `rename()` (또는 `unlink()` 후 `move()`, 실패 시 `copy+delete` 폴백) 이라 그 사이 프로세스가 죽으면 원본 파일이 사라지고 새 파일도 없는 데이터 손실 창이 있었음 | 🟡 MED | ✅ Fixed — `os.replace()`로 진짜 원자적 교체로 변경, 회귀 테스트 5건 추가 (`tests/test_rl_agent_atomic_save.py`) |
| N5 | bare `except Exception:` 다수 (현재 460건, `wicked_zerg_challenger/` 기준) | 🟢 LOW | open — 대량 리팩터라 점진적 처리 필요 |
| N6 | F841 unused local variables (`e` 47건 + 기타 74건) | 🟢 LOW | open |

검증 권장: PR 분리 불필요 — 이번 배치는 테스트/RL 저장 로직 한정, 봇의 실시간 의사결정 경로에는 영향 없음.

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

## 📝 이 문서에 대해

Issue #3~#6의 상세 코드 제안(수혈 우선순위, 자원 예약 락, position utils, 매직 넘버 상수화)은
모두 위 재검증에서 확인했듯 이미 코드베이스에 구현되어 있어 이 버전에서 제거했다.
(git history에서 이전 버전 참고 가능.)

## 🟢 남은 LOW 항목

- **N5** bare `except Exception:` 460건 — 대량 리팩터. 파일당 점진적으로 처리 권장.
- **N6** F841 미사용 지역변수 (`e` 47건 포함) — flake8 `--select=F841`로 추적.
- 매직 넘버 정리는 Queen Manager는 완료(`GameConfig`), 나머지 매니저는 미착수.

## 🔍 추가 검토 필요 항목 (진행 중 확인)

### Performance Optimization
- [ ] Pathfinding 캐싱 확인
- [ ] Unit filtering 최적화 검토
- [ ] Blackboard 업데이트 빈도 분석

### Strategic Improvements
- [ ] Counter-build 시스템 확인 (적 유닛 조합 대응)
- [ ] Scouting 타이밍 최적화
- [ ] Expansion timing 검증

### Code Quality
- [ ] Type hints 추가 (Python 3.10+) — `core/resource_manager.py`, `core/manager_factory.py` (PLAN-NIGHTLY.md P2.5)
- [ ] bare except 460건 점진적 축소 (N5)

---

## 📊 현재 상태 (2026-07-08)

- ✅ 전체 테스트: 507 passed / 14 skipped / 0 failed
- ✅ N1-N4 (F811 중복 정의), Issue #3/#4/#5: 재검증 결과 모두 이미 반영됨
- ✅ N7 (테스트 이벤트루프 오염), N8 (RL 모델 저장 무동작 버그), N9 (비원자적 저장) — 이번 사이클에서 수정
- 🟢 남은 것: N5(bare except), N6(F841), PLAN-NIGHTLY.md의 P2.2/P2.3/P2.5

**최종 갱신일**: 2026-07-08
