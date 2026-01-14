# Git History에서 API 키 완전히 제거
# Remove API keys from Git history completely

param(
    [string[]]$KeysToRemove = @(
        "AIzaSyC_CiEZ6CtVz9e1kAK0Ymbt1br4tGGMIIo",
        "AIzaSyD-c6nmOLolncIrcZ8DIvKCkzib_-iUZrc"
    )
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Git History에서 API 키 제거" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# git-filter-repo 설치 확인
$filterRepoInstalled = Get-Command git-filter-repo -ErrorAction SilentlyContinue

if (-not $filterRepoInstalled) {
    Write-Host "? git-filter-repo가 설치되어 있지 않습니다." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "설치 방법:" -ForegroundColor Yellow
    Write-Host "  1. pip install git-filter-repo" -ForegroundColor White
    Write-Host "  2. 또는 https://github.com/newren/git-filter-repo 에서 다운로드" -ForegroundColor White
    Write-Host ""
    Write-Host "대안: BFG Repo-Cleaner 사용" -ForegroundColor Yellow
    Write-Host "  https://rtyley.github.io/bfg-repo-cleaner/" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host "[1/4] 백업 생성 중..." -ForegroundColor Green
$backupBranch = "backup-before-key-removal-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
git branch $backupBranch
Write-Host "  ? 백업 브랜치 생성: $backupBranch" -ForegroundColor Green
Write-Host ""

Write-Host "[2/4] 각 키 제거 중..." -ForegroundColor Green
foreach ($key in $KeysToRemove) {
    Write-Host "  키 제거 중: $($key.Substring(0, 10))..." -ForegroundColor Yellow
    
    # git-filter-repo로 키 제거
    git filter-repo --invert-paths --path-glob "**/*" --replace-text <(echo "$key==>REDACTED")
    
    Write-Host "    ? 완료" -ForegroundColor Green
}
Write-Host ""

Write-Host "[3/4] 원격 저장소에 강제 푸시 (주의!)" -ForegroundColor Red
Write-Host "  ? 이 작업은 Git history를 영구적으로 변경합니다!" -ForegroundColor Red
Write-Host "  ? 모든 팀원에게 알려야 합니다!" -ForegroundColor Red
Write-Host ""
$confirm = Read-Host "계속하시겠습니까? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "취소되었습니다." -ForegroundColor Yellow
    Write-Host "백업 브랜치로 복원: git checkout $backupBranch" -ForegroundColor White
    exit 0
}

Write-Host "[4/4] 원격 저장소 강제 푸시..." -ForegroundColor Green
git push origin --force --all
git push origin --force --tags
Write-Host "  ? 완료" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "완료!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "다음 단계:" -ForegroundColor Yellow
Write-Host "  1. 모든 팀원에게 알림" -ForegroundColor White
Write-Host "  2. 팀원들은 저장소를 다시 클론해야 합니다" -ForegroundColor White
Write-Host "  3. 새 API 키를 설정하세요" -ForegroundColor White
Write-Host ""
