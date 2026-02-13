# ═══════════════════════════════════════════════════════════
# JARVIS Pre-Commit Security Check
# - API 키/시크릿 유출 방지
# - 스테이징된 파일만 검사
# ═══════════════════════════════════════════════════════════

Write-Host "🔒 Pre-commit 보안 스캔 시작..." -ForegroundColor Cyan

$ErrorFound = $false

# 스테이징된 파일 목록 (새로 추가 / 수정된 파일만)
$StagedFiles = git diff --cached --name-only --diff-filter=ACM 2>$null
if (-not $StagedFiles) {
    Write-Host "✅ 스테이징된 파일 없음 - 스캔 스킵" -ForegroundColor Green
    exit 0
}

# 검사할 확장자
$CheckExtensions = @('.py', '.js', '.ts', '.json', '.yaml', '.yml', '.toml',
                     '.cfg', '.ini', '.bat', '.cmd', '.sh', '.ps1', '.md', '.txt', '.env')

# 제외할 파일 패턴
$ExcludePatterns = @('*.example', '.gitignore', 'pre_commit_security_check*', 'security.py')

# ── .env에서 키 prefix 동적 로드 ──
$DangerPatterns = @(
    # 일반적인 API 키 할당 패턴 (하드코딩)
    @{ Pattern = '(?i)(UPBIT_ACCESS_KEY|UPBIT_SECRET_KEY)\s*=\s*"[A-Za-z0-9]{20,}"'; Description = 'Upbit 키 하드코딩' }
    @{ Pattern = '(?i)(access_key|secret_key|api_key)\s*=\s*"[A-Za-z0-9]{25,}"'; Description = 'API 키 하드코딩' }
    @{ Pattern = '(?i)Upbit\(\s*"[A-Za-z0-9]{20,}"'; Description = 'Upbit() 생성자에 키 직접 전달' }

    # 바이낸스 등 다른 거래소
    @{ Pattern = '(?i)(binance|coinbase|bithumb).*key\s*=\s*"[A-Za-z0-9]{20,}"'; Description = '거래소 API 키 하드코딩' }

    # 일반 시크릿
    @{ Pattern = '(?i)password\s*=\s*"[^"]{8,}"'; Description = '비밀번호 하드코딩' }
    @{ Pattern = '(?i)token\s*=\s*"[A-Za-z0-9_\-\.]{20,}"'; Description = '토큰 하드코딩' }
)

# .env에서 실제 키의 prefix를 읽어 동적 패턴 추가 (하드코딩 방지)
$EnvPaths = @("wicked_zerg_challenger\.env", ".env")
foreach ($envPath in $EnvPaths) {
    if (Test-Path $envPath) {
        $envContent = Get-Content $envPath -ErrorAction SilentlyContinue
        foreach ($line in $envContent) {
            if ($line -match '^(UPBIT_ACCESS_KEY|UPBIT_SECRET_KEY)\s*=\s*(.{10})') {
                $prefix = $Matches[2]
                $DangerPatterns += @{ Pattern = [regex]::Escape($prefix); Description = "Upbit API 키 값 감지 ($($Matches[1]))" }
            }
        }
        break
    }
}

$FilesChecked = 0
$IssuesFound = @()

foreach ($file in $StagedFiles) {
    # 확장자 체크
    $ext = [System.IO.Path]::GetExtension($file).ToLower()
    if ($ext -notin $CheckExtensions) { continue }

    # 제외 파일 체크
    $skip = $false
    foreach ($excl in $ExcludePatterns) {
        if ($file -like $excl) { $skip = $true; break }
    }
    if ($skip) { continue }

    # .env 파일은 이미 .gitignore에 있어야 하지만 혹시 모르니 경고
    if ($file -match '\.env$' -or $file -match '\.env\.') {
        $IssuesFound += "⚠️  .env 파일이 커밋에 포함됨: $file"
        $ErrorFound = $true
        continue
    }

    $FilesChecked++

    # 파일 내용에서 위험 패턴 검색 (스테이징된 내용)
    $content = git show ":$file" 2>$null
    if (-not $content) { continue }

    $lineNum = 0
    foreach ($line in $content -split "`n") {
        $lineNum++
        foreach ($dp in $DangerPatterns) {
            if ($line -match $dp.Pattern) {
                $IssuesFound += "❌ $($dp.Description): ${file}:${lineNum}"
                $ErrorFound = $true
            }
        }
    }
}

# ── 결과 출력 ──
Write-Host "  검사한 파일: $FilesChecked 개" -ForegroundColor Gray

if ($IssuesFound.Count -gt 0) {
    Write-Host ""
    Write-Host "⛔ 보안 이슈 발견! 커밋을 차단합니다." -ForegroundColor Red
    Write-Host ""
    foreach ($issue in $IssuesFound) {
        Write-Host "  $issue" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "해결 방법:" -ForegroundColor White
    Write-Host "  1. API 키를 .env 파일로 이동하세요 (이미 .gitignore에 포함)" -ForegroundColor White
    Write-Host "  2. os.getenv() 또는 config.py를 통해 키를 로드하세요" -ForegroundColor White
    Write-Host "  3. 강제 커밋: git commit --no-verify (비추천)" -ForegroundColor DarkGray
    exit 1
}

Write-Host "✅ 보안 스캔 통과 - 민감 정보 미검출" -ForegroundColor Green
exit 0
