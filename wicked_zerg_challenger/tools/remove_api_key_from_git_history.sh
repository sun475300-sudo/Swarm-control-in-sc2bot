#!/bin/bash
# Git 히스토리에서 API 키 제거 스크립트
# 사용법: ./remove_api_key_from_git_history.sh "[YOUR_API_KEY]"

set -e

API_KEY="${1:-[YOUR_API_KEY_HERE]}"

echo "============================================================"
echo "Git 히스토리에서 API 키 제거"
echo "============================================================"
echo ""
echo "제거할 API 키: $API_KEY"
echo ""

# 현재 브랜치 확인
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "현재 브랜치: $CURRENT_BRANCH"
echo ""

# 경고 메시지
echo "⚠️  경고: 이 작업은 Git 히스토리를 다시 작성합니다!"
echo "⚠️  이미 푸시된 커밋을 수정하면 force push가 필요합니다!"
echo "⚠️  다른 사람과 공유하는 저장소라면 문제가 될 수 있습니다!"
echo ""

read -p "계속하시겠습니까? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "작업이 취소되었습니다."
    exit 0
fi

echo ""
echo "API 키가 포함된 커밋 검색 중..."

# API 키가 포함된 커밋 찾기
COMMITS=$(git log --all --source --full-history -S "$API_KEY" --oneline)
if [ -n "$COMMITS" ]; then
    echo "다음 커밋에서 API 키가 발견되었습니다:"
    echo "$COMMITS"
else
    echo "API 키가 포함된 커밋을 찾을 수 없습니다."
    exit 0
fi

echo ""
echo "백업 브랜치 생성 중..."

# 백업 브랜치 생성
BACKUP_BRANCH="backup-before-api-key-removal-$(date +%Y%m%d-%H%M%S)"
git branch "$BACKUP_BRANCH"
echo "백업 브랜치 생성: $BACKUP_BRANCH"

echo ""
echo "Git 히스토리에서 API 키 제거 중..."
echo "이 작업은 시간이 걸릴 수 있습니다..."

# git filter-branch를 사용하여 API 키 제거
git filter-branch --force --index-filter \
    "git ls-files -z | xargs -0 sed -i 's/$API_KEY/[API_KEY_REMOVED]/g'" \
    --prune-empty --tag-name-filter cat -- --all

echo ""
echo "Git 히스토리 정리 중..."

# 정리
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo ""
echo "============================================================"
echo "작업 완료"
echo "============================================================"
echo ""
echo "백업 브랜치: $BACKUP_BRANCH"
echo ""
echo "다음 단계:"
echo "  1. 히스토리 확인: git log --all --oneline | head -20"
echo "  2. API 키가 제거되었는지 확인: git log --all -S \"$API_KEY\""
echo "  3. 문제가 없으면 푸시:"
echo "     git push --force --all"
echo "     git push --force --tags"
echo ""
echo "문제가 발생하면 다음 명령어로 복구:"
echo "  git reset --hard $BACKUP_BRANCH"
echo ""
