# Swarm-control-in-sc2bot branch merge plan (2026-05-03)

## main 기준 ahead/behind
- local main vs origin/main: 10/0 (main이 origin/main 보다 10 commits 앞섬)
- 다음 push 가 origin/main을 정렬

## 분류

### 1) Merged into local main (정리 가능, 자동 삭제 후보)
- claude/ecstatic-hellman-628710
- claude/happy-wiles-991755
- claude/objective-moser-953a1c
- claude/review-readme-planning-TJk2f
- claude/upbeat-murdock-99da7d

### 2) NOT merged into local main (검토 필요, 수동 처리)
- claude/black-format-main-2026-04-27   (이미 merge 됐지만 history 가 다름 → 살짝 조사 필요)
- claude/master-todo-sc2                  (별개 PR)
- claude/stoic-shannon-1YXPl              (claude PR)
- claude/stoic-shannon-Dc7yg              (claude PR)

위 4개는 fast-forward 가 안 되거나 충돌 가능성 있어 GitHub 에서 PR 로 머지 권장.

## 자동 머지 대상
없음 (merged 그룹은 이미 main 에 포함된 상태이므로 단순 삭제만).

## 정리 액션 (자동 .bat)
- merged 그룹 5개 로컬 브랜치 삭제 (`git branch -d <name>`)
- no-merged 그룹은 이름만 출력
