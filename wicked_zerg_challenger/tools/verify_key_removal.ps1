# 키 제거 확인 스크립트
# Verify Key Removal Script

$ProjectRoot = Split-Path -Parent $PSScriptRoot

$KeysToCheck = @(
    "AIzaSyC_CiEZ6CtVz9e1kAK0Ymbt1br4tGGMIIo",
    "AIzaSyD-c6nmOLolncIrcZ8DIvKCkzib_-iUZrc"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "키 제거 확인" -ForegroundColor Cyan
Write-Host "Key Removal Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$allClean = $true

# 1. 환경 변수 확인
Write-Host "[1/4] 환경 변수 확인..." -ForegroundColor Green
$envKeys = @("GEMINI_API_KEY", "GOOGLE_API_KEY")
foreach ($envKey in $envKeys) {
    $value = [System.Environment]::GetEnvironmentVariable($envKey, "User")
    if ($value) {
        foreach ($oldKey in $KeysToCheck) {
            if ($value -eq $oldKey) {
                Write-Host "  ? 발견됨: $envKey = $($oldKey.Substring(0, 10))..." -ForegroundColor Yellow
                $allClean = $false
            }
        }
    }
}
if ($allClean) {
    Write-Host "  ? 환경 변수에 오래된 키가 없습니다" -ForegroundColor Green
}
Write-Host ""

# 2. .env 파일 확인
Write-Host "[2/4] .env 파일 확인..." -ForegroundColor Green
$envFile = Join-Path $ProjectRoot ".env"
if (Test-Path $envFile) {
    $content = Get-Content $envFile -ErrorAction SilentlyContinue
    foreach ($line in $content) {
        foreach ($oldKey in $KeysToCheck) {
            if ($line -match [regex]::Escape($oldKey)) {
                Write-Host "  ? 발견됨: .env 파일에 오래된 키" -ForegroundColor Yellow
                $allClean = $false
            }
        }
    }
    if ($allClean) {
        Write-Host "  ? .env 파일에 오래된 키가 없습니다" -ForegroundColor Green
    }
} else {
    Write-Host "  ? .env 파일이 없습니다" -ForegroundColor Green
}
Write-Host ""

# 3. 프로젝트 파일 검색
Write-Host "[3/4] 프로젝트 파일 검색..." -ForegroundColor Green
$foundInFiles = @()
foreach ($oldKey in $KeysToCheck) {
    $results = Select-String -Path "$ProjectRoot\*" -Pattern ([regex]::Escape($oldKey)) -Recurse -ErrorAction SilentlyContinue | 
        Where-Object { 
            $_.Path -notmatch "\.git" -and
            $_.Path -notmatch "node_modules" -and
            $_.Path -notmatch "venv" -and
            $_.Path -notmatch "__pycache__" -and
            $_.Path -notmatch "secrets" -and
            $_.Path -notmatch "api_keys" -and
            $_.Path -notmatch "\.pyc"
        }
    
    if ($results) {
        $foundInFiles += $oldKey
        Write-Host "  ? 발견됨: $($oldKey.Substring(0, 10))..." -ForegroundColor Yellow
        foreach ($result in $results | Select-Object -First 3) {
            $relPath = $result.Path.Replace($ProjectRoot, "").TrimStart("\")
            Write-Host "    - $relPath : $($result.LineNumber)" -ForegroundColor Yellow
        }
        $allClean = $false
    }
}

if ($foundInFiles.Count -eq 0) {
    Write-Host "  ? 프로젝트 파일에 오래된 키가 없습니다" -ForegroundColor Green
}
Write-Host ""

# 4. Git History 검색
Write-Host "[4/4] Git History 검색..." -ForegroundColor Green
Push-Location $ProjectRoot
try {
    foreach ($oldKey in $KeysToCheck) {
        $gitResults = git log -p --all -S $oldKey --source --all 2>$null | Select-String -Pattern ([regex]::Escape($oldKey))
        if ($gitResults) {
            Write-Host "  ? 발견됨: Git history에 $($oldKey.Substring(0, 10))..." -ForegroundColor Yellow
            Write-Host "    → git-filter-repo 또는 BFG로 제거 필요" -ForegroundColor Yellow
            $allClean = $false
        }
    }
    
    if ($allClean) {
        Write-Host "  ? Git history에 오래된 키가 없습니다" -ForegroundColor Green
    }
} catch {
    Write-Host "  ? Git history 검색 실패: $_" -ForegroundColor Yellow
} finally {
    Pop-Location
}

Write-Host ""

# 최종 결과
Write-Host "========================================" -ForegroundColor Cyan
if ($allClean) {
    Write-Host "? 완료! 모든 오래된 키가 제거되었습니다." -ForegroundColor Green
    Write-Host "? '과거 키가 없음' 상태입니다." -ForegroundColor Green
} else {
    Write-Host "? 일부 오래된 키가 남아있습니다." -ForegroundColor Yellow
    Write-Host "  → tools/complete_key_removal.ps1 실행 권장" -ForegroundColor Yellow
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
