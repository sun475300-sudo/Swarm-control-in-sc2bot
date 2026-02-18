# ═══════════════════════════════════════════════════════════
# JARVIS Pre-Commit Security Check v2.0
# - Prevents API key/secret/token leaks
# - Covers: Anthropic, Discord, Google, AWS, Upbit, OpenAI, GitHub
# - Only scans staged files
# ═══════════════════════════════════════════════════════════

# Force UTF-8 output to prevent Korean text garbling
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "[Security] Pre-commit scan starting (v2.0)..." -ForegroundColor Cyan

$ErrorFound = $false

# 스테이징된 파일 목록 (새로 추가 / 수정된 파일만)
$StagedFiles = git diff --cached --name-only --diff-filter=ACM 2>$null
if (-not $StagedFiles) {
    Write-Host "✅ 스테이징된 파일 없음 - 스캔 스킵" -ForegroundColor Green
    exit 0
}

# ── 검사할 확장자 ──
$CheckExtensions = @(
    '.py', '.js', '.ts', '.jsx', '.tsx',
    '.json', '.yaml', '.yml', '.toml',
    '.cfg', '.ini', '.bat', '.cmd', '.sh', '.ps1',
    '.md', '.txt', '.env', '.conf', '.config'
)

# ── 제외할 파일 패턴 (보안 도구 자체, 예시 파일) ──
$ExcludePatterns = @(
    'pre_commit_security_check*',
    'check_api_key*',
    'check_all_api_keys*',
    'remove_api_key*',
    'rotate_api_key*',
    'api_key_security_hardening*',
    '*.example',
    '*.sample',
    '.gitignore',
    'REMOVE_API_KEY_FROM_GIT_HISTORY.md',
    'TOMORROW_TODO.md',
    'CRITICAL_ISSUES_SUMMARY.md'
)

# ── 위험 패턴 정의 ──
$DangerPatterns = @(

    # ════ Anthropic / Claude ════
    @{ Pattern = 'sk-ant-[a-zA-Z0-9\-_]{20,}'; Description = 'Anthropic API 키 감지' }
    @{ Pattern = '(?i)ANTHROPIC_API_KEY\s*=\s*[''"][a-zA-Z0-9\-_]{20,}[''"]'; Description = 'Anthropic API 키 하드코딩' }

    # ════ OpenAI ════
    @{ Pattern = 'sk-[a-zA-Z0-9]{48}'; Description = 'OpenAI API 키 감지' }
    @{ Pattern = '(?i)OPENAI_API_KEY\s*=\s*[''"][a-zA-Z0-9\-_]{20,}[''"]'; Description = 'OpenAI API 키 하드코딩' }

    # ════ Google / GCP ════
    @{ Pattern = 'AIza[0-9A-Za-z\-_]{35}'; Description = 'Google API 키 감지' }
    @{ Pattern = '(?i)"type"\s*:\s*"service_account"'; Description = 'Google 서비스 계정 JSON 감지' }
    @{ Pattern = '(?i)GOOGLE_API_KEY\s*=\s*[''"][a-zA-Z0-9\-_]{20,}[''"]'; Description = 'Google API 키 하드코딩' }

    # ════ AWS ════
    @{ Pattern = 'AKIA[0-9A-Z]{16}'; Description = 'AWS Access Key ID 감지' }
    @{ Pattern = '(?i)aws_secret_access_key\s*=\s*[''"][a-zA-Z0-9/+]{40}[''"]'; Description = 'AWS Secret Key 하드코딩' }

    # ════ Discord ════
    @{ Pattern = '(?i)discord.*token\s*=\s*[''"][A-Za-z0-9\.\-_]{50,}[''"]'; Description = 'Discord 봇 토큰 하드코딩' }
    @{ Pattern = 'MTI[0-9A-Za-z\-_]{50,}'; Description = 'Discord 토큰 패턴 감지' }
    @{ Pattern = '(?i)DISCORD_TOKEN\s*=\s*[''"][A-Za-z0-9\.\-_]{50,}[''"]'; Description = 'Discord 토큰 하드코딩' }

    # ════ Upbit / 거래소 ════
    @{ Pattern = '(?i)(UPBIT_ACCESS_KEY|UPBIT_SECRET_KEY)\s*=\s*[''"][A-Za-z0-9]{20,}[''"]'; Description = 'Upbit 키 하드코딩' }
    @{ Pattern = '(?i)Upbit\(\s*[''"][A-Za-z0-9]{20,}[''"]'; Description = 'Upbit() 생성자에 키 직접 전달' }
    @{ Pattern = '(?i)(access_key|secret_key)\s*=\s*[''"][A-Za-z0-9]{25,}[''"]'; Description = '거래소 API 키 하드코딩' }
    @{ Pattern = '(?i)(binance|coinbase|bithumb|bybit).*key\s*=\s*[''"][A-Za-z0-9]{20,}[''"]'; Description = '거래소 API 키 하드코딩' }

    # ════ GitHub ════
    @{ Pattern = 'ghp_[a-zA-Z0-9]{36}'; Description = 'GitHub Personal Access Token 감지' }
    @{ Pattern = 'ghs_[a-zA-Z0-9]{36}'; Description = 'GitHub Server Token 감지' }
    @{ Pattern = 'github_pat_[a-zA-Z0-9_]{82}'; Description = 'GitHub Fine-grained Token 감지' }

    # ════ Slack ════
    @{ Pattern = 'xox[baprs]-[0-9]{12}-[0-9]{12}-[a-zA-Z0-9]{24}'; Description = 'Slack 토큰 감지' }

    # ════ 일반 패턴 ════
    @{ Pattern = '(?i)password\s*=\s*[''"][^''"]{8,}[''"]'; Description = '비밀번호 하드코딩' }
    @{ Pattern = '(?i)secret\s*=\s*[''"][a-zA-Z0-9\-_\.]{16,}[''"]'; Description = '시크릿 하드코딩' }
    @{ Pattern = '(?i)private_key\s*=\s*[''"][a-zA-Z0-9\-_\.]{20,}[''"]'; Description = '프라이빗 키 하드코딩' }
    @{ Pattern = '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----'; Description = 'Private Key 파일 내용 감지' }
    @{ Pattern = '(?i)bearer\s+[a-zA-Z0-9\-_\.]{30,}'; Description = 'Bearer 토큰 하드코딩' }
)

# ── Load actual key prefixes from .env files dynamically ──
$EnvPaths = @(".env", ".env.jarvis", "wicked_zerg_challenger\.env", "crypto_trading\.env")
foreach ($envPath in $EnvPaths) {
    if (Test-Path $envPath) {
        $envContent = Get-Content $envPath -Encoding UTF8 -ErrorAction SilentlyContinue
        foreach ($line in $envContent) {
            # KEY=VALUE format: only add prefix pattern if value is 20+ chars AND not a URL/path
            if ($line -match '^([A-Z_]+)\s*=\s*(.{20,})$') {
                $keyName = $Matches[1]
                $keyValue = $Matches[2].Trim('"').Trim("'")
                # Skip URLs, file paths, and non-secret values
                if ($keyValue -match '^(https?://|http://|/|C:\\|\\\\)') { continue }
                if ($keyValue -match '^(true|false|yes|no|\d+)$') { continue }
                if ($keyName -match '(URL|PATH|DIR|HOST|PORT|MODE|NAME|TIMEOUT)$') { continue }
                if ($keyValue.Length -ge 20) {
                    $prefix = $keyValue.Substring(0, [Math]::Min(12, $keyValue.Length))
                    $escapedPrefix = [regex]::Escape($prefix)
                    $DangerPatterns += @{
                        Pattern = $escapedPrefix
                        Description = "[Key Leak] Actual key value detected ($keyName prefix)"
                    }
                }
            }
        }
    }
}

$FilesChecked = 0
$IssuesFound = @()

# Force UTF-8 when reading staged file content
$env:PYTHONIOENCODING = 'utf-8'

foreach ($file in $StagedFiles) {
    # 확장자 체크
    $ext = [System.IO.Path]::GetExtension($file).ToLower()
    if ($ext -notin $CheckExtensions) { continue }

    # 제외 파일 체크
    $skip = $false
    $fileName = [System.IO.Path]::GetFileName($file)
    foreach ($excl in $ExcludePatterns) {
        if ($fileName -like $excl -or $file -like "*$excl*") {
            $skip = $true; break
        }
    }
    if ($skip) { continue }

    # .env 파일 자체가 커밋에 포함되면 즉시 차단
    if ($file -match '(^|/)\.env(\.|$)' -or $file -match '\.env\.jarvis') {
        $IssuesFound += "⛔ .env 파일이 커밋에 포함됨: $file"
        $ErrorFound = $true
        continue
    }

    # credentials JSON 파일 차단
    if ($file -match '(service.account|credentials|client.secret).*\.json$') {
        $IssuesFound += "⛔ 인증 JSON 파일이 커밋에 포함됨: $file"
        $ErrorFound = $true
        continue
    }

    $FilesChecked++

    # 스테이징된 파일 내용 가져오기
    $content = git show ":$file" 2>$null
    if (-not $content) { continue }

    $lineNum = 0
    foreach ($line in $content -split "`n") {
        $lineNum++

        # 주석 줄 스킵 (# 또는 // 로 시작하는 줄)
        $trimmed = $line.Trim()
        if ($trimmed -match '^(#|//)') { continue }

        foreach ($dp in $DangerPatterns) {
            if ($line -match $dp.Pattern) {
                $IssuesFound += "❌ $($dp.Description): ${file}:${lineNum}"
                $ErrorFound = $true
            }
        }
    }
}

# ── Results ──
Write-Host "  Files scanned: $FilesChecked" -ForegroundColor Gray

if ($IssuesFound.Count -gt 0) {
    Write-Host ""
    Write-Host "[BLOCKED] Security issue detected! Commit aborted." -ForegroundColor Red
    Write-Host ""
    foreach ($issue in $IssuesFound) {
        Write-Host "  $issue" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "======================================" -ForegroundColor DarkGray
    Write-Host "How to fix:" -ForegroundColor White
    Write-Host "  1. Move API keys to .env or .env.jarvis file" -ForegroundColor White
    Write-Host "  2. Load via os.getenv() / process.env in code" -ForegroundColor White
    Write-Host "  3. If already committed: revoke & rotate the key immediately" -ForegroundColor White
    Write-Host "  4. Force commit (not recommended): git commit --no-verify" -ForegroundColor DarkGray
    Write-Host "======================================" -ForegroundColor DarkGray
    exit 1
}

Write-Host "[OK] Security scan passed ($FilesChecked files checked) - No secrets detected" -ForegroundColor Green
exit 0
