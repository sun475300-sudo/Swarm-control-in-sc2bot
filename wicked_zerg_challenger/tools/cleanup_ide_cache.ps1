# IDE 환경 변수 캐시 삭제 스크립트
# Remove IDE Environment Variable Cache

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "IDE 환경 변수 캐시 삭제" -ForegroundColor Cyan
Write-Host "Remove IDE Environment Variable Cache" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$cleanedCount = 0

# ============================================================================
# Visual Studio Code
# ============================================================================
Write-Host "[1/6] Visual Studio Code 캐시 삭제..." -ForegroundColor Green

$vscodePaths = @(
    "$env:APPDATA\Code\User\workspaceStorage",
    "$env:APPDATA\Code\CachedData",
    "$env:APPDATA\Code\Cache",
    "$env:APPDATA\Code\logs",
    "$env:USERPROFILE\.vscode\extensions"
)

foreach ($path in $vscodePaths) {
    if (Test-Path $path) {
        try {
            Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "  ? 삭제됨: $path" -ForegroundColor Green
            $cleanedCount++
        } catch {
            Write-Host "  ? 삭제 실패: $path - $_" -ForegroundColor Yellow
        }
    }
}

Write-Host ""

# ============================================================================
# Android Studio
# ============================================================================
Write-Host "[2/6] Android Studio 캐시 삭제..." -ForegroundColor Green

$androidStudioBase = "$env:USERPROFILE\.AndroidStudio*"
$androidStudioPaths = @(
    "config\caches",
    "system\caches",
    "system\log",
    "system\index"
)

$androidStudioDirs = Get-ChildItem -Path $env:USERPROFILE -Filter ".AndroidStudio*" -Directory -ErrorAction SilentlyContinue
foreach ($dir in $androidStudioDirs) {
    foreach ($subPath in $androidStudioPaths) {
        $fullPath = Join-Path $dir.FullName $subPath
        if (Test-Path $fullPath) {
            try {
                Remove-Item -Path $fullPath -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "  ? 삭제됨: $fullPath" -ForegroundColor Green
                $cleanedCount++
            } catch {
                Write-Host "  ? 삭제 실패: $fullPath - $_" -ForegroundColor Yellow
            }
        }
    }
}

# Gradle 캐시
$gradleCache = "$env:USERPROFILE\.gradle\caches"
if (Test-Path $gradleCache) {
    try {
        Remove-Item -Path $gradleCache -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  ? Gradle 캐시 삭제됨" -ForegroundColor Green
        $cleanedCount++
    } catch {
        Write-Host "  ? Gradle 캐시 삭제 실패: $_" -ForegroundColor Yellow
    }
}

Write-Host ""

# ============================================================================
# IntelliJ IDEA
# ============================================================================
Write-Host "[3/6] IntelliJ IDEA 캐시 삭제..." -ForegroundColor Green

$ideaDirs = Get-ChildItem -Path $env:USERPROFILE -Filter ".IntelliJIdea*" -Directory -ErrorAction SilentlyContinue
foreach ($dir in $ideaDirs) {
    $ideaPaths = @(
        "config\caches",
        "system\caches",
        "system\log"
    )
    
    foreach ($subPath in $ideaPaths) {
        $fullPath = Join-Path $dir.FullName $subPath
        if (Test-Path $fullPath) {
            try {
                Remove-Item -Path $fullPath -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "  ? 삭제됨: $fullPath" -ForegroundColor Green
                $cleanedCount++
            } catch {
                Write-Host "  ? 삭제 실패: $fullPath - $_" -ForegroundColor Yellow
            }
        }
    }
}

Write-Host ""

# ============================================================================
# PyCharm
# ============================================================================
Write-Host "[4/6] PyCharm 캐시 삭제..." -ForegroundColor Green

$pycharmDirs = Get-ChildItem -Path $env:USERPROFILE -Filter ".PyCharm*" -Directory -ErrorAction SilentlyContinue
foreach ($dir in $pycharmDirs) {
    $pycharmPaths = @(
        "config\caches",
        "system\caches",
        "system\log"
    )
    
    foreach ($subPath in $pycharmPaths) {
        $fullPath = Join-Path $dir.FullName $subPath
        if (Test-Path $fullPath) {
            try {
                Remove-Item -Path $fullPath -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "  ? 삭제됨: $fullPath" -ForegroundColor Green
                $cleanedCount++
            } catch {
                Write-Host "  ? 삭제 실패: $fullPath - $_" -ForegroundColor Yellow
            }
        }
    }
}

Write-Host ""

# ============================================================================
# Cursor IDE
# ============================================================================
Write-Host "[5/6] Cursor IDE 캐시 삭제..." -ForegroundColor Green

$cursorPaths = @(
    "$env:APPDATA\Cursor\User\workspaceStorage",
    "$env:APPDATA\Cursor\CachedData",
    "$env:APPDATA\Cursor\Cache"
)

foreach ($path in $cursorPaths) {
    if (Test-Path $path) {
        try {
            Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "  ? 삭제됨: $path" -ForegroundColor Green
            $cleanedCount++
        } catch {
            Write-Host "  ? 삭제 실패: $path - $_" -ForegroundColor Yellow
        }
    }
}

Write-Host ""

# ============================================================================
# Python 캐시
# ============================================================================
Write-Host "[6/6] Python 캐시 삭제..." -ForegroundColor Green

$pythonCachePaths = @(
    "$env:USERPROFILE\.cache\pip",
    "$env:LOCALAPPDATA\pip\Cache"
)

foreach ($path in $pythonCachePaths) {
    if (Test-Path $path) {
        try {
            Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "  ? 삭제됨: $path" -ForegroundColor Green
            $cleanedCount++
        } catch {
            Write-Host "  ? 삭제 실패: $path - $_" -ForegroundColor Yellow
        }
    }
}

# __pycache__ 디렉토리
$pycacheDirs = Get-ChildItem -Path (Split-Path $PSScriptRoot -Parent) -Recurse -Filter "__pycache__" -Directory -ErrorAction SilentlyContinue | 
    Where-Object { $_.FullName -notmatch "\.git|venv|node_modules" }

foreach ($dir in $pycacheDirs) {
    try {
        Remove-Item -Path $dir.FullName -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  ? 삭제됨: $($dir.FullName)" -ForegroundColor Green
        $cleanedCount++
    } catch {
        Write-Host "  ? 삭제 실패: $($dir.FullName) - $_" -ForegroundColor Yellow
    }
}

Write-Host ""

# ============================================================================
# 최종 결과
# ============================================================================
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "완료!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "총 $cleanedCount 개 캐시 디렉토리 삭제됨" -ForegroundColor Green
Write-Host ""
Write-Host "다음 단계:" -ForegroundColor Cyan
Write-Host "  1. IDE 재시작 (VS Code, Android Studio 등)" -ForegroundColor White
Write-Host "  2. 새 터미널 열기" -ForegroundColor White
Write-Host "  3. 새 키 설정 확인" -ForegroundColor White
Write-Host ""
