# 완전한 API 키 제거 스크립트
# Complete API Key Removal Script

param(
    [switch]$SkipGitHistory = $false
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "완전한 API 키 제거" -ForegroundColor Cyan
Write-Host "Complete API Key Removal" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 제거할 키 목록
$KeysToRemove = @(
    "AIzaSyC_CiEZ6CtVz9e1kAK0Ymbt1br4tGGMIIo",
    "AIzaSyD-c6nmOLolncIrcZ8DIvKCkzib_-iUZrc"
)

# 프로젝트 루트
$ProjectRoot = Split-Path -Parent $PSScriptRoot

# ============================================================================
# 1. 환경 변수에서 키 제거
# ============================================================================
Write-Host "[1/5] 환경 변수에서 키 제거..." -ForegroundColor Green

# 현재 세션에서 제거
Remove-Item Env:\GEMINI_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:\GOOGLE_API_KEY -ErrorAction SilentlyContinue
Write-Host "  ? 현재 세션 환경 변수 제거됨" -ForegroundColor Green

# 사용자 환경 변수에서 제거
try {
    [System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", $null, "User")
    [System.Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", $null, "User")
    Write-Host "  ? 사용자 환경 변수 제거됨" -ForegroundColor Green
} catch {
    Write-Host "  ? 사용자 환경 변수 제거 실패: $_" -ForegroundColor Yellow
}

# 시스템 환경 변수에서 제거 (관리자 권한 필요)
try {
    [System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", $null, "Machine")
    [System.Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", $null, "Machine")
    Write-Host "  ? 시스템 환경 변수 제거됨" -ForegroundColor Green
} catch {
    Write-Host "  ? 시스템 환경 변수 제거 실패 (관리자 권한 필요): $_" -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# 2. .env 파일에서 키 제거
# ============================================================================
Write-Host "[2/5] .env 파일에서 키 제거..." -ForegroundColor Green

$envFile = Join-Path $ProjectRoot ".env"
if (Test-Path $envFile) {
    $content = Get-Content $envFile
    $newContent = $content | Where-Object { 
        $_ -notmatch "GEMINI_API_KEY" -and 
        $_ -notmatch "GOOGLE_API_KEY" -and
        $_ -notmatch "AIzaSy"
    }
    
    if ($newContent.Count -lt $content.Count) {
        $newContent | Set-Content $envFile
        Write-Host "  ? .env 파일에서 키 제거됨" -ForegroundColor Green
    } else {
        Write-Host "  ? .env 파일에 키가 없습니다" -ForegroundColor Green
    }
} else {
    Write-Host "  ? .env 파일이 없습니다" -ForegroundColor Green
}

Write-Host ""

# ============================================================================
# 3. 문서 파일에서 예제 키 마스킹
# ============================================================================
Write-Host "[3/5] 문서 파일에서 예제 키 마스킹..." -ForegroundColor Green

$docFiles = Get-ChildItem -Path $ProjectRoot -Recurse -Include "*.md", "*.txt" | 
    Where-Object { 
        $_.FullName -notmatch "\.git" -and
        $_.FullName -notmatch "node_modules" -and
        $_.FullName -notmatch "venv" -and
        $_.FullName -notmatch "__pycache__"
    }

$maskedCount = 0
foreach ($file in $docFiles) {
    $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
    if ($content) {
        $originalContent = $content
        foreach ($key in $KeysToRemove) {
            if ($content -match [regex]::Escape($key)) {
                $masked = $key.Substring(0, 10) + "..." + $key.Substring($key.Length - 4)
                $content = $content -replace [regex]::Escape($key), $masked
            }
        }
        
        if ($content -ne $originalContent) {
            Set-Content -Path $file.FullName -Value $content -NoNewline
            $maskedCount++
            $relPath = $file.FullName.Replace($ProjectRoot, "").TrimStart("\")
            Write-Host "  ? $relPath 마스킹됨" -ForegroundColor Green
        }
    }
}

if ($maskedCount -eq 0) {
    Write-Host "  ? 마스킹할 파일이 없습니다" -ForegroundColor Green
} else {
    Write-Host "  ? $maskedCount 개 파일 마스킹 완료" -ForegroundColor Green
}

Write-Host ""

# ============================================================================
# 4. 코드 파일에서 하드코딩된 키 제거
# ============================================================================
Write-Host "[4/5] 코드 파일에서 하드코딩된 키 제거..." -ForegroundColor Green

$codeFiles = Get-ChildItem -Path $ProjectRoot -Recurse -Include "*.py", "*.kt", "*.java", "*.js", "*.ts" | 
    Where-Object { 
        $_.FullName -notmatch "\.git" -and
        $_.FullName -notmatch "node_modules" -and
        $_.FullName -notmatch "venv" -and
        $_.FullName -notmatch "__pycache__" -and
        $_.FullName -notmatch "build" -and
        $_.FullName -notmatch "dist"
    }

$removedCount = 0
foreach ($file in $codeFiles) {
    $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
    if ($content) {
        $originalContent = $content
        foreach ($key in $KeysToRemove) {
            # 하드코딩된 키를 "YOUR_API_KEY_HERE" 또는 환경 변수 참조로 변경
            $pattern = '["\''`]?' + [regex]::Escape($key) + '["\''`]?'
            $content = $content -replace $pattern, '"YOUR_API_KEY_HERE"'
        }
        
        if ($content -ne $originalContent) {
            Set-Content -Path $file.FullName -Value $content -NoNewline
            $removedCount++
            $relPath = $file.FullName.Replace($ProjectRoot, "").TrimStart("\")
            Write-Host "  ? $relPath 수정됨" -ForegroundColor Green
        }
    }
}

if ($removedCount -eq 0) {
    Write-Host "  ? 제거할 키가 없습니다" -ForegroundColor Green
} else {
    Write-Host "  ? $removedCount 개 파일 수정 완료" -ForegroundColor Green
}

Write-Host ""

# ============================================================================
# 5. Git History에서 키 제거
# ============================================================================
if (-not $SkipGitHistory) {
    Write-Host "[5/5] Git History에서 키 제거..." -ForegroundColor Green
    
    # git-filter-repo 확인
    $filterRepoInstalled = Get-Command git-filter-repo -ErrorAction SilentlyContinue
    
    if (-not $filterRepoInstalled) {
        Write-Host "  ? git-filter-repo가 설치되어 있지 않습니다." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  설치 방법:" -ForegroundColor Yellow
        Write-Host "    pip install git-filter-repo" -ForegroundColor White
        Write-Host ""
        Write-Host "  또는 BFG Repo-Cleaner 사용:" -ForegroundColor Yellow
        Write-Host "    https://rtyley.github.io/bfg-repo-cleaner/" -ForegroundColor White
        Write-Host ""
        
        $useBFG = Read-Host "BFG를 사용하시겠습니까? (yes/no)"
        if ($useBFG -eq "yes") {
            Write-Host "  BFG 사용 방법:" -ForegroundColor Yellow
            Write-Host "    1. keys.txt 파일 생성 (각 키를 한 줄씩)" -ForegroundColor White
            Write-Host "    2. java -jar bfg.jar --replace-text keys.txt" -ForegroundColor White
            Write-Host "    3. git reflog expire --expire=now --all" -ForegroundColor White
            Write-Host "    4. git gc --prune=now --aggressive" -ForegroundColor White
        }
    } else {
        Write-Host "  ? 이 작업은 Git history를 영구적으로 변경합니다!" -ForegroundColor Red
        Write-Host "  ? 모든 팀원에게 알려야 합니다!" -ForegroundColor Red
        Write-Host "  ? 백업을 먼저 생성하세요!" -ForegroundColor Red
        Write-Host ""
        
        $confirm = Read-Host "계속하시겠습니까? (yes/no)"
        if ($confirm -eq "yes") {
            # 백업 브랜치 생성
            $backupBranch = "backup-before-key-removal-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
            git branch $backupBranch
            Write-Host "  ? 백업 브랜치 생성: $backupBranch" -ForegroundColor Green
            
            # 각 키 제거
            foreach ($key in $KeysToRemove) {
                Write-Host "  키 제거 중: $($key.Substring(0, 10))..." -ForegroundColor Yellow
                
                # replace-text 파일 생성
                $replaceFile = Join-Path $env:TEMP "replace-text-$(Get-Random).txt"
                "$key==>REDACTED" | Set-Content $replaceFile
                
                # git-filter-repo 실행
                Push-Location $ProjectRoot
                try {
                    git filter-repo --replace-text $replaceFile --force
                    Write-Host "    ? 완료" -ForegroundColor Green
                } catch {
                    Write-Host "    ? 실패: $_" -ForegroundColor Red
                } finally {
                    Remove-Item $replaceFile -ErrorAction SilentlyContinue
                    Pop-Location
                }
            }
            
            Write-Host ""
            Write-Host "  ? 원격 저장소에 강제 푸시가 필요합니다:" -ForegroundColor Red
            Write-Host "    git push origin --force --all" -ForegroundColor White
            Write-Host "    git push origin --force --tags" -ForegroundColor White
        } else {
            Write-Host "  취소되었습니다." -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "[5/5] Git History 제거 건너뜀 (--SkipGitHistory 옵션)" -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# 최종 확인
# ============================================================================
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "최종 확인" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "프로젝트 파일에서 키 검색..." -ForegroundColor Green
$foundKeys = @()
foreach ($key in $KeysToRemove) {
    $results = Select-String -Path "$ProjectRoot\*" -Pattern ([regex]::Escape($key)) -Recurse -ErrorAction SilentlyContinue | 
        Where-Object { 
            $_.Path -notmatch "\.git" -and
            $_.Path -notmatch "node_modules" -and
            $_.Path -notmatch "venv" -and
            $_.Path -notmatch "__pycache__" -and
            $_.Path -notmatch "secrets" -and
            $_.Path -notmatch "api_keys"
        }
    
    if ($results) {
        $foundKeys += $key
        Write-Host "  ? 발견됨: $($key.Substring(0, 10))..." -ForegroundColor Yellow
        foreach ($result in $results | Select-Object -First 5) {
            $relPath = $result.Path.Replace($ProjectRoot, "").TrimStart("\")
            Write-Host "    - $relPath : $($result.LineNumber)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ? 없음: $($key.Substring(0, 10))..." -ForegroundColor Green
    }
}

Write-Host ""

if ($foundKeys.Count -eq 0) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "? 완료! 모든 키가 제거되었습니다." -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "? 일부 키가 남아있습니다. 수동으로 확인하세요." -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "다음 단계:" -ForegroundColor Cyan
Write-Host "  1. 새 키 설정 확인: secrets/gemini_api.txt" -ForegroundColor White
Write-Host "  2. Git history 정리 (필요한 경우)" -ForegroundColor White
Write-Host "  3. 팀원에게 알림 (Git history 변경 시)" -ForegroundColor White
Write-Host ""
