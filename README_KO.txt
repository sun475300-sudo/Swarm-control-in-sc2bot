sc2bot 레포 배치 파일 안내 (Cowork Claude 자동 생성, 2026-05-03)

[현재 상태]
- main 이 origin/main 보다 10 commits 앞섬 (push 필요).
- 워킹 트리에 modified 11개 + 새 테스트 4개 + 신규 module 1개.
- pytest 결과: 388 passed / 20 skipped (integration 제외).

[발견 / 검증된 변경]
- harassment_coordinator.py
  * HP 후퇴 임계 0.2 -> 0.35 (자글링이 너무 늦게 후퇴하던 버그)
  * per-raid 일꾼 처치 카운터 추가
  * 적이 일꾼 재건 시 스냅샷 동기화 (이중 카운팅 방지)
- comm_learning/__init__.py: API 클래스 이름 변경 후 backward-compat
  alias 추가 (CommAgent / CommNet / TarMAC).
- 새 테스트 3개 (combat phase FSM, expansion timing, phase scout cadence) 59건 모두 통과.

[배치 파일]
1. PUSH_FIX_TO_MAIN.bat
   - .git/index.lock 자동 제거
   - git add -A 로 modified + 새 파일 모두 스테이징
   - pytest tests/ --ignore=tests/integration 통과 시에만 commit + push
   - 실패 시 중단

2. MERGE_ALL_BRANCHES_TO_MAIN.bat
   - origin fetch
   - 이미 main 에 merge 된 5개 로컬 브랜치 자동 삭제:
     * claude/ecstatic-hellman-628710
     * claude/happy-wiles-991755
     * claude/objective-moser-953a1c
     * claude/review-readme-planning-TJk2f
     * claude/upbeat-murdock-99da7d
   - merge 안 된 4개는 이름만 출력 (PR 권장)

[실행 방법]
cmd 창에서:
  cd /d E:\GitHub\Swarm-control-in-sc2bot
  PUSH_FIX_TO_MAIN.bat

또는 통합 실행:
  E:\PUSH_ALL_REPOS_TO_MAIN.bat

[제약]
- pytest 가 PATH 에 없으면 python -m pytest 폴백 자동 사용.
- main force push 금지.
