# 단일 브랜치 운영과 보관 기록

2026-10-30에 원격 브랜치 541개를 조사하고 `main` 하나로 정리했습니다.
`main`에 없는 고유 커밋 2,545개를 포함해 모든 이전 브랜치의 끝점은
`archive/2026-10-30/<이전 브랜치 이름>` 태그로 원격에 보존했습니다.
540개 태그의 SHA를 원본 브랜치 SHA와 전수 대조한 뒤 브랜치를 삭제했고,
최종 원격 브랜치가 `main` 하나인지 다시 확인했습니다.
보관된 코드를 자동 병합한 것은 아닙니다.

## 운영 원칙

- 검증한 변경을 `main`에 반영하며 강제 덮어쓰기를 하지 않습니다.
- 예약 자동화는 테스트를 통과한 소스의 README 상태와 JSON만 커밋합니다.
- 과거 브랜치는 [GitHub 태그 목록](https://github.com/sun475300-sudo/Swarm-control-in-sc2bot/tags)에서 확인할 수 있습니다.
- 보관 태그를 삭제하거나 같은 이름을 다른 커밋으로 덮어쓰지 않습니다.
- 후속 기여자가 새 브랜치를 만들 수 있으므로 단일 브랜치는 현재 정리 결과입니다. 새 브랜치를 무조건 삭제하는 예약 작업은 두지 않습니다.

이전 작업을 살펴보려면 태그의 정확한 이름을 사용합니다.

```bash
git fetch origin refs/tags/archive/2026-10-30/claude/cool-edison-RCIW1
git log --oneline main..FETCH_HEAD
git diff main...FETCH_HEAD
```

필요한 커밋을 검토하고 테스트한 뒤 선별 반영합니다. 2,545개 과거 커밋을
검증 없이 한꺼번에 병합하지 않습니다.

## 재사용 정리 도구

`scripts/consolidate_branches.py`는 기본 실행에서 원격을 읽기만 하고 계획을
출력합니다. `--apply --manifest <새 파일>`을 명시해야 보관·삭제가 실행됩니다.
기존 manifest와 보관 태그를 덮어쓰지 않으며, 끝점 변경이나 보호 규칙 거절 시
원자적 삭제가 중단됩니다. 삭제 전에 모든 보관 태그가 정확한 SHA인지 검증합니다.

현재 클라우드 작업 공간의 추가 복구 자료:

- `/workspace/sc2bot-environment/all-branches-before-cleanup.bundle`: 정리 전 541개 끝점 전체, 자체 완결성 검사 통과
- `/workspace/sc2bot-environment/branch-consolidation-manifest-2026-10-30.json`: 원본 끝점과 보관 태그 매핑
- `/workspace/sc2bot-environment/branch-consolidation-verified.json`: 정리 후 원격 검증 결과

위 로컬 파일의 미래 환경 복원은 환경 게시·스냅샷에 달려 있습니다.
원격 태그는 이 로컬 백업과 별개로 GitHub에 보존되어 있습니다.
