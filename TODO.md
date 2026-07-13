# 작업 목록 (Live TODO)

**최근 갱신:** 2026-07-13 (자동 점검 루프 — 테스트 실행 + 코드 검증 기반 재작성)

> 이 문서는 2026-01-25에 작성된 이후 갱신되지 않아 완전히 stale한 상태였다
> (`strategy_manager.py` 단일 파일 시절 기준 — 현재는 `strategy_manager_v2.py`로 대체됨,
> `scouting_system.py`는 `scouting/advanced_scout_system_v2.py` 등으로 확장됨).
> 오늘 세션에서 테스트 스위트 실행 + 코드 grep 검증을 거쳐 전면 재작성했다.

## 📊 현재 상태 요약 (2026-07-13 검증)

- **테스트**: `wicked_zerg_challenger/tests/` 680개 전부 통과 (pytest, 0 실패/에러)
- **정적 분석**: `ruff --select F811,F821,E722` 0건 (중복 정의·미정의 이름·bare except 없음).
  `F841`(미사용 지역변수) 130건 중 47건 이번 세션에서 자동 정리, 잔여 83건은 unsafe-fix 대상.
- **MASSIVE_FIX_PLAN.md P0 (8개, 승률 직접 영향)**: 코드에 전부 반영 확인 (`FIX P0-1`~`FIX P0-8` 주석).
  문서만 갱신되지 않았던 것으로, 실제 게임 승률 재측정(20게임 벤치마크)은 아직 미수행.
- **REMAINING_ISSUES.md N1-N4, Issue #3, #4**: 전부 코드에 반영 확인, 문서만 갱신 (오늘 수정 완료).

## 🔴 우선순위 높음 — 실제로 열려있는 항목

### 1. 실측 승률 벤치마크 미수행
`MASSIVE_FIX_PLAN.md`의 P0/P1 수정이 실제로 승률을 19.3% → 50%+로 끌어올렸는지 **한 번도 재측정되지 않았다**.
- 매치업별(ZvP/ZvT/ZvZ) 최소 5게임씩 Easy/Medium AI 대전
- 가스 부유량, 서플라이 피크, 3기지 타이밍을 로그에서 재추출해 P0 항목 효과 검증
- 이 저장소에는 SC2 클라이언트가 없어 이 세션에서는 실행 불가 — SC2 실행 가능한 환경에서 수행 필요

### 2. `position_utils` 미채택 호출부 정리 (REMAINING_ISSUES.md Issue #5)
`utils/position_utils.py`에 `get_center_position`/`get_weighted_center` 등이 이미 구현되어 있고
이번 세션에 테스트(`tests/test_position_utils.py`, 19케이스)도 추가했지만, 아래 11곳은 여전히
동일 계산을 인라인 중복하고 있다. 호출부마다 빈 컬렉션 처리(`None` vs `Point2((0,0))`)가 달라 개별 검증 필요:
- `combat_manager.py:1622`, `combat_manager.py:3657`
- `combat/combat_execution.py:262`, `combat/infestor_tactics.py:189`, `combat/micro_combat.py:442,1345`
- `combat_phase_controller.py:591`, `micro_controller.py:525`
- `battle_preparation_system.py:166`, `idle_unit_manager.py:179`

### 3. 잔여 F841 (미사용 변수) 83건 수동 검토
`ruff check --select F841 --fix`로 47건은 자동 정리했으나, 나머지는 `--unsafe-fixes`가 필요한
(우변에 부작용 가능성 있는) 케이스라 자동화하지 않았다. 파일별 상위: `combat_manager.py`,
`bot_step_integration.py`, `local_training/production_resilience.py`, `visuals/*.py`.

## 🟡 우선순위 중간

### 4. `MASSIVE_FIX_PLAN.md` P1 항목 상세 검증
오늘 spot-check로 P1-1(HP가중 전투력), P1-2(무한루프 없음), P1-3(매치업별 빌드), P1-4(공격 타이밍),
P1-5(방어 소집 반경 제한), P1-6(인젝트 쿨다운)은 구현 확인. P1-7(`tech_coordinator.py`)과
P1-8(`racial_counter_manager.py`)은 전용 모듈 존재만 확인했고 세부 로직(레어 4:30-5:00 타이밍,
공중/메카닉 감지 후 유닛 전환 임계값 등 문서 스펙과 일치하는지)은 미검증.

### 5. requirements.txt 의존성 해석 문제 (`MASTER_TODO_SC2.md`에 이미 기록됨)
루트 `requirements.txt`가 SC2 봇 + 암호화폐 트레이딩 + Discord 봇 + AWS 등 무관한 서비스 의존성을
한 파일에 뒤섞어 두어 pip resolver가 매우 느리다 (이번 세션에서 6분+ 소요 후 강제 종료).
추가로 `mpyq`(burnysc2의 전이 의존성)가 Debian 패치 distutils(`install_layout`)와 충돌해
시스템 Python에서 빌드 실패 — venv(fresh setuptools)에서는 정상 설치됨.
- 서비스별 requirements 파일 분리 (`requirements-sc2.txt`, `requirements-crypto.txt`는 이미 있음 — 루트 통합 파일 정리 필요)
- 또는 최소 lockfile(`pip-compile` 등) 도입

## 🟢 우선순위 낮음

### 6. 매직 넘버 정리 (Queen 외)
`REMAINING_ISSUES.md` Issue #6 — Queen Manager 상수는 이미 `GameConfig`로 이동 완료.
나머지 파일(`combat_manager.py`의 체력/거리 임계값 등)은 여전히 하드코딩.

### 7. 47개 이상의 stale 루트 `*.md` 리포트 정리
`STATUS.md`가 "candidate for docs/history/"로 표시한 문서들(Phase 완료 보고서, 한국어 리포트 등)이
아직 이동되지 않음 (`PLAN-NIGHTLY.md` P1.5 항목).

---

## ✅ 이번 세션(2026-07-13)에서 완료

1. 테스트 스위트 680개 전부 통과 확인 (베이스라인 그린)
2. `MASSIVE_FIX_PLAN.md` P0 8개 항목 전부 구현 확인 → 문서에 검증 배너 추가
3. `REMAINING_ISSUES.md` N1-N4, Issue #3, #4 해결 확인 → 문서 갱신
4. `ruff --fix`로 미사용 예외 변수(F841) 47건 자동 정리 (동작 변화 없음, 테스트로 검증)
5. `tests/test_position_utils.py` 신설 (19케이스) — 기존에 테스트 커버리지 0이었던 공용 유틸리티에 회귀 안전망 추가
6. 이 문서(`TODO.md`) 및 `MASSIVE_FIX_PLAN.md`를 stale 상태에서 현재 코드 상태와 일치하도록 재작성

---

**작성일:** 2026-07-13
**다음 업데이트:** 다음 자동 점검 루프 실행 시
