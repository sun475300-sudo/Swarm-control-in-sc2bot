# Git History���� API Ű ������ ����
# Remove API keys from Git history completely

param(
    [string[]]$KeysToRemove = @(
        $env:OLD_GOOGLE_KEY_1,
        $env:OLD_GOOGLE_KEY_2
    ) | Where-Object { $_ -ne $null }
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Git History���� API Ű ����" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# git-filter-repo ��ġ Ȯ��
$filterRepoInstalled = Get-Command git-filter-repo -ErrorAction SilentlyContinue

if (-not $filterRepoInstalled) {
    Write-Host "? git-filter-repo�� ��ġ�Ǿ� ���� �ʽ��ϴ�." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "��ġ ���:" -ForegroundColor Yellow
    Write-Host "  1. pip install git-filter-repo" -ForegroundColor White
    Write-Host "  2. �Ǵ� https://github.com/newren/git-filter-repo ���� �ٿ�ε�" -ForegroundColor White
    Write-Host ""
    Write-Host "���: BFG Repo-Cleaner ���" -ForegroundColor Yellow
    Write-Host "  https://rtyley.github.io/bfg-repo-cleaner/" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host "[1/4] ��� ���� ��..." -ForegroundColor Green
$backupBranch = "backup-before-key-removal-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
git branch $backupBranch
Write-Host "  ? ��� �귣ġ ����: $backupBranch" -ForegroundColor Green
Write-Host ""

Write-Host "[2/4] �� Ű ���� ��..." -ForegroundColor Green
foreach ($key in $KeysToRemove) {
    Write-Host "  Ű ���� ��: $($key.Substring(0, 10))..." -ForegroundColor Yellow
    
    # git-filter-repo�� Ű ����
    git filter-repo --invert-paths --path-glob "**/*" --replace-text <(echo "$key==>REDACTED")
    
    Write-Host "    ? �Ϸ�" -ForegroundColor Green
}
Write-Host ""

Write-Host "[3/4] ���� ����ҿ� ���� Ǫ�� (����!)" -ForegroundColor Red
Write-Host "  ? �� �۾��� Git history�� ���������� �����մϴ�!" -ForegroundColor Red
Write-Host "  ? ��� �������� �˷��� �մϴ�!" -ForegroundColor Red
Write-Host ""
$confirm = Read-Host "����Ͻðڽ��ϱ�? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "��ҵǾ����ϴ�." -ForegroundColor Yellow
    Write-Host "��� �귣ġ�� ����: git checkout $backupBranch" -ForegroundColor White
    exit 0
}

Write-Host "[4/4] ���� ����� ���� Ǫ��..." -ForegroundColor Green
git push origin --force --all
git push origin --force --tags
Write-Host "  ? �Ϸ�" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "�Ϸ�!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "���� �ܰ�:" -ForegroundColor Yellow
Write-Host "  1. ��� �������� �˸�" -ForegroundColor White
Write-Host "  2. �������� ����Ҹ� �ٽ� Ŭ���ؾ� �մϴ�" -ForegroundColor White
Write-Host "  3. �� API Ű�� �����ϼ���" -ForegroundColor White
Write-Host ""
