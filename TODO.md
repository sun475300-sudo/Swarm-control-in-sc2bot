# 작업 목록 (2026-07-12 재검증)

> 이전 버전(2026-01-25/26 작성)은 Sprint 1의 초기 항목들을 다뤘으나, 그 항목들은 모두 코드에 구현되어 있음이 2026-07-12 감사로 확인됐다. `ROADMAP.md`의 "구현 현황 요약"이 Sprint 1-8 전체의 최신 상태를 담고 있으니 그쪽을 우선 참고할 것. 이 파일은 로드맵에 없는, 지금 시점에 실제로 남아있는 작업만 추린 목록이다.

## 우선순위 높음

### 1. Sprint 8.1: 현재 코드베이스 기준 승률 재검증
**문제:** 마지막 실게임 결과(`data/reports/`)는 6월 초 스태빌라이즈 커밋(F821 버그 수정, 죽은 메서드 제거) 이전 데이터라 지금 코드 상태를 반영하지 못한다. "45~50% 추정 승률"은 근거가 없는 숫자다.
**막힌 이유:** 이 저장소를 다루는 원격/샌드박스 세션에는 StarCraft II 게임 클라이언트가 설치되어 있지 않아 `run_single_game.py`/`run_mass_test.py`를 실행할 수 없다. **SC2 클라이언트가 있는 로컬/CI 환경에서 수행해야 하는 작업.**
**할 일:** SC2 클라이언트가 있는 환경에서 Easy/Medium 각 종족 10판씩 실행 → 승/패 로그를 `data/reports/`에 축적 → `improvement_log.txt`/`logs/improvement_log.json`을 실제 결과로 갱신(현재 두 파일 모두 사실상 방치되어 git 이력과 완전히 어긋나 있음).

### 2. Sprint 7.3 마무리: 매직넘버 → GameConstants 치환 스윕
**현재 상태:** `utils/game_constants.py`의 `GameFrequencies`는 존재하고 일부 파일에 쓰이지만, `strategy_manager.py`/`economy_manager.py`에 `iteration % 22`, `% 50`, `% 100` 등 하드코딩된 리터럴이 20개 이상 남아있다(2026-07-12 grep 확인).
**파일:** `wicked_zerg_challenger/strategy_manager.py`, `wicked_zerg_challenger/economy_manager.py`
**할 일:** 각 리터럴을 대응하는 `GameFrequencies`/`EconomyConstants` 상수로 교체. 기계적 작업이라 리스크는 낮지만 342개 관련 테스트(현재 661개 전체 테스트) 통과 재확인 필수.

### 3. GitHub 저장소의 열린 draft PR 정리
**문제:** 2026-07-12 기준 `main`을 대상으로 한 열린 draft PR이 30개 있고, 대다수가 "asyncio event-loop crash"/"CI 파이프라인 복구" 계열의 거의 동일한 제목이다(PR #395~#424). 실제로는 병합된 것이 하나도 없어 보이고, CI가 빨간 상태가 계속 재발생하는 원인도 결국 `black`/`isort` 포맷팅 드리프트였다(2026-07-12에 확인 및 수정, PR 참고).
**할 일:** 사용자가 30개 draft PR을 검토해 유효한 것만 병합하고 중복은 닫는 정리 작업 필요. 이후 자동화 세션이 매번 새 브랜치/PR을 만드는 대신, 열려 있는 자신의 PR을 계속 이어서 커밋하도록 운영 방식을 조정하는 것을 권장.

## 완료 확인됨 (참고용, ROADMAP.md와 중복)

- 정찰 시스템(오버로드/저글링/오버시어), 견제 시스템, 1분 확장 타이밍, 전투 프레임 스킵, StrategyManager 역할 분담, 인코딩 정리 — 모두 코드 검증 완료(DONE), 자세한 근거는 `ROADMAP.md` 참고.

## 참고사항

### 테스트 명령어
```bash
cd wicked_zerg_challenger
python -m pytest tests/ -q          # 661개 단위 테스트 (SC2 클라이언트 불필요)
```
```bash
# 실게임 검증 (SC2 클라이언트 있는 환경에서만 가능)
python run_single_game.py
python run_mass_test.py --opponent Terran --difficulty Medium --games 10
```

### 정적 분석 (CI와 동일)
```bash
black --check .
isort --check-only .
flake8 --select=F821,F811,F822,E999 .
```

**작성일:** 2026-07-12
