# 완전한 환경 변수 캐시 및 키 제거 스크립트
# Complete Environment Variable Cache and Key Removal Script

param(
    [switch]$SkipIDE = $false,
    [switch]$SkipDeployment = $false
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "완전한 환경 변수 캐시 및 키 제거" -ForegroundColor Cyan
Write-Host "Complete Environment Cleanup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$KeysToRemove = @(
    "AIzaSyC_CiEZ6CtVz9e1kAK0Ymbt1br4tGGMIIo",
    "AIzaSyD-c6nmOLolncIrcZ8DIvKCkzib_-iUZrc"
)

# ============================================================================
# 1. IDE 환경 변수 캐시 삭제
# ============================================================================
if (-not $SkipIDE) {
    Write-Host "[1/6] IDE 환경 변수 캐시 삭제..." -ForegroundColor Green
    
    # Visual Studio Code
    $vscodeCachePaths = @(
        "$env:APPDATA\Code\User\workspaceStorage",
        "$env:APPDATA\Code\CachedData",
        "$env:APPDATA\Code\Cache"
    )
    
    foreach ($path in $vscodeCachePaths) {
        if (Test-Path $path) {
            try {
                Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "  ? VS Code 캐시 삭제: $path" -ForegroundColor Green
            } catch {
                Write-Host "  ? VS Code 캐시 삭제 실패: $path" -ForegroundColor Yellow
            }
        }
    }
    
    # Android Studio
    $androidStudioPaths = @(
        "$env:USERPROFILE\.AndroidStudio*\config\caches",
        "$env:USERPROFILE\.AndroidStudio*\system\caches",
        "$env:USERPROFILE\.gradle\caches"
    )
    
    foreach ($pattern in $androidStudioPaths) {
        $paths = Get-ChildItem -Path (Split-Path $pattern -Parent) -Filter (Split-Path $pattern -Leaf) -ErrorAction SilentlyContinue
        foreach ($path in $paths) {
            try {
                Remove-Item -Path $path.FullName -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "  ? Android Studio 캐시 삭제: $($path.FullName)" -ForegroundColor Green
            } catch {
                Write-Host "  ? Android Studio 캐시 삭제 실패: $($path.FullName)" -ForegroundColor Yellow
            }
        }
    }
    
    # IntelliJ IDEA
    $ideaPaths = @(
        "$env:USERPROFILE\.IntelliJIdea*\config\caches",
        "$env:USERPROFILE\.IntelliJIdea*\system\caches"
    )
    
    foreach ($pattern in $ideaPaths) {
        $paths = Get-ChildItem -Path (Split-Path $pattern -Parent) -Filter (Split-Path $pattern -Leaf) -ErrorAction SilentlyContinue
        foreach ($path in $paths) {
            try {
                Remove-Item -Path $path.FullName -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "  ? IntelliJ IDEA 캐시 삭제: $($path.FullName)" -ForegroundColor Green
            } catch {
                Write-Host "  ? IntelliJ IDEA 캐시 삭제 실패: $($path.FullName)" -ForegroundColor Yellow
            }
        }
    }
    
    # PyCharm
    $pycharmPaths = @(
        "$env:USERPROFILE\.PyCharm*\config\caches",
        "$env:USERPROFILE\.PyCharm*\system\caches"
    )
    
    foreach ($pattern in $pycharmPaths) {
        $paths = Get-ChildItem -Path (Split-Path $pattern -Parent) -Filter (Split-Path $pattern -Leaf) -ErrorAction SilentlyContinue
        foreach ($path in $paths) {
            try {
                Remove-Item -Path $path.FullName -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "  ? PyCharm 캐시 삭제: $($path.FullName)" -ForegroundColor Green
            } catch {
                Write-Host "  ? PyCharm 캐시 삭제 실패: $($path.FullName)" -ForegroundColor Yellow
            }
        }
    }
    
    Write-Host ""
}

# ============================================================================
# 2. 터미널/배치 파일에서 이전 키 제거
# ============================================================================
Write-Host "[2/6] 터미널/배치 파일에서 이전 키 제거..." -ForegroundColor Green

$batchFiles = Get-ChildItem -Path $ProjectRoot -Recurse -Include "*.bat", "*.cmd", "*.ps1", "*.sh" | 
    Where-Object { 
        $_.FullName -notmatch "\.git" -and
        $_.FullName -notmatch "node_modules" -and
        $_.FullName -notmatch "venv"
    }

$cleanedBatchCount = 0
foreach ($file in $batchFiles) {
    $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
    if ($content) {
        $originalContent = $content
        foreach ($key in $KeysToRemove) {
            # 환경 변수 설정 라인 제거 또는 주석 처리
            $patterns = @(
                "set\s+.*$([regex]::Escape($key))",
                "\$env:.*$([regex]::Escape($key))",
                "export\s+.*$([regex]::Escape($key))",
                [regex]::Escape($key)
            )
            
            foreach ($pattern in $patterns) {
                # 주석 처리
                $content = $content -replace "($pattern)", "# REMOVED: `$1"
            }
        }
        
        if ($content -ne $originalContent) {
            Set-Content -Path $file.FullName -Value $content -NoNewline
            $cleanedBatchCount++
            $relPath = $file.FullName.Replace($ProjectRoot, "").TrimStart("\")
            Write-Host "  ? $relPath 정리됨" -ForegroundColor Green
        }
    }
}

if ($cleanedBatchCount -eq 0) {
    Write-Host "  ? 정리할 배치 파일이 없습니다" -ForegroundColor Green
} else {
    Write-Host "  ? $cleanedBatchCount 개 배치 파일 정리 완료" -ForegroundColor Green
}

Write-Host ""

# ============================================================================
# 3. 환경 변수 완전 제거
# ============================================================================
Write-Host "[3/6] 환경 변수 완전 제거..." -ForegroundColor Green

# 현재 세션
Remove-Item Env:\GEMINI_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:\GOOGLE_API_KEY -ErrorAction SilentlyContinue
Write-Host "  ? 현재 세션 환경 변수 제거됨" -ForegroundColor Green

# 사용자 환경 변수
try {
    [System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", $null, "User")
    [System.Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", $null, "User")
    Write-Host "  ? 사용자 환경 변수 제거됨" -ForegroundColor Green
} catch {
    Write-Host "  ? 사용자 환경 변수 제거 실패: $_" -ForegroundColor Yellow
}

# 시스템 환경 변수 (관리자 권한 필요)
try {
    [System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", $null, "Machine")
    [System.Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", $null, "Machine")
    Write-Host "  ? 시스템 환경 변수 제거됨" -ForegroundColor Green
} catch {
    Write-Host "  ? 시스템 환경 변수 제거 실패 (관리자 권한 필요): $_" -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# 4. 배포 파이프라인에서 옛 키 제거
# ============================================================================
if (-not $SkipDeployment) {
    Write-Host "[4/6] 배포 파이프라인에서 옛 키 제거..." -ForegroundColor Green
    
    # GitHub Actions
    $githubWorkflows = Get-ChildItem -Path $ProjectRoot -Recurse -Filter ".github\workflows\*.yml" -ErrorAction SilentlyContinue
    foreach ($workflow in $githubWorkflows) {
        $content = Get-Content $workflow.FullName -Raw -ErrorAction SilentlyContinue
        if ($content) {
            $originalContent = $content
            foreach ($key in $KeysToRemove) {
                # Secrets에서 키 제거 또는 마스킹
                $content = $content -replace [regex]::Escape($key), "REDACTED"
            }
            
            if ($content -ne $originalContent) {
                Set-Content -Path $workflow.FullName -Value $content -NoNewline
                $relPath = $workflow.FullName.Replace($ProjectRoot, "").TrimStart("\")
                Write-Host "  ? GitHub Actions 정리: $relPath" -ForegroundColor Green
            }
        }
    }
    
    # GitLab CI
    $gitlabCI = Join-Path $ProjectRoot ".gitlab-ci.yml"
    if (Test-Path $gitlabCI) {
        $content = Get-Content $gitlabCI -Raw -ErrorAction SilentlyContinue
        if ($content) {
            $originalContent = $content
            foreach ($key in $KeysToRemove) {
                $content = $content -replace [regex]::Escape($key), "REDACTED"
            }
            
            if ($content -ne $originalContent) {
                Set-Content -Path $gitlabCI -Value $content -NoNewline
                Write-Host "  ? GitLab CI 정리됨" -ForegroundColor Green
            }
        }
    }
    
    # Azure DevOps
    $azurePipelines = Get-ChildItem -Path $ProjectRoot -Recurse -Filter "azure-pipelines.yml" -ErrorAction SilentlyContinue
    foreach ($pipeline in $azurePipelines) {
        $content = Get-Content $pipeline.FullName -Raw -ErrorAction SilentlyContinue
        if ($content) {
            $originalContent = $content
            foreach ($key in $KeysToRemove) {
                $content = $content -replace [regex]::Escape($key), "REDACTED"
            }
            
            if ($content -ne $originalContent) {
                Set-Content -Path $pipeline.FullName -Value $content -NoNewline
                $relPath = $pipeline.FullName.Replace($ProjectRoot, "").TrimStart("\")
                Write-Host "  ? Azure DevOps 정리: $relPath" -ForegroundColor Green
            }
        }
    }
    
    # Docker
    $dockerfiles = Get-ChildItem -Path $ProjectRoot -Recurse -Filter "Dockerfile*" -ErrorAction SilentlyContinue
    foreach ($dockerfile in $dockerfiles) {
        $content = Get-Content $dockerfile.FullName -Raw -ErrorAction SilentlyContinue
        if ($content) {
            $originalContent = $content
            foreach ($key in $KeysToRemove) {
                $content = $content -replace [regex]::Escape($key), "REDACTED"
            }
            
            if ($content -ne $originalContent) {
                Set-Content -Path $dockerfile.FullName -Value $content -NoNewline
                $relPath = $dockerfile.FullName.Replace($ProjectRoot, "").TrimStart("\")
                Write-Host "  ? Dockerfile 정리: $relPath" -ForegroundColor Green
            }
        }
    }
    
    # Kubernetes
    $k8sFiles = Get-ChildItem -Path $ProjectRoot -Recurse -Include "*.yaml", "*.yml" | 
        Where-Object { 
            $_.FullName -match "k8s|kubernetes|deployment|service" -and
            $_.FullName -notmatch "\.git"
        }
    
    foreach ($k8sFile in $k8sFiles) {
        $content = Get-Content $k8sFile.FullName -Raw -ErrorAction SilentlyContinue
        if ($content) {
            $originalContent = $content
            foreach ($key in $KeysToRemove) {
                $content = $content -replace [regex]::Escape($key), "REDACTED"
            }
            
            if ($content -ne $originalContent) {
                Set-Content -Path $k8sFile.FullName -Value $content -NoNewline
                $relPath = $k8sFile.FullName.Replace($ProjectRoot, "").TrimStart("\")
                Write-Host "  ? Kubernetes 파일 정리: $relPath" -ForegroundColor Green
            }
        }
    }
    
    Write-Host ""
}

# ============================================================================
# 5. .env 파일 정리
# ============================================================================
Write-Host "[5/6] .env 파일 정리..." -ForegroundColor Green

$envFiles = Get-ChildItem -Path $ProjectRoot -Recurse -Filter ".env*" -ErrorAction SilentlyContinue | 
    Where-Object { $_.FullName -notmatch "\.git" }

foreach ($envFile in $envFiles) {
    $content = Get-Content $envFile.FullName -ErrorAction SilentlyContinue
    if ($content) {
        $newContent = $content | Where-Object { 
            $_ -notmatch "GEMINI_API_KEY" -and 
            $_ -notmatch "GOOGLE_API_KEY" -and
            $_ -notmatch "AIzaSy"
        }
        
        if ($newContent.Count -lt $content.Count) {
            $newContent | Set-Content $envFile.FullName
            $relPath = $envFile.FullName.Replace($ProjectRoot, "").TrimStart("\")
            Write-Host "  ? $relPath 정리됨" -ForegroundColor Green
        }
    }
}

Write-Host ""

# ============================================================================
# 6. 프로세스 재시작 안내
# ============================================================================
Write-Host "[6/6] 프로세스 재시작 안내..." -ForegroundColor Green
Write-Host "  ? 다음 프로세스를 재시작하세요:" -ForegroundColor Yellow
Write-Host "    1. IDE (VS Code, Android Studio, IntelliJ 등)" -ForegroundColor White
Write-Host "    2. 터미널 세션 (새 터미널 열기)" -ForegroundColor White
Write-Host "    3. 배포 파이프라인 (GitHub Actions, GitLab CI 등)" -ForegroundColor White
Write-Host ""

# ============================================================================
# 최종 확인
# ============================================================================
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "완료!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "다음 단계:" -ForegroundColor Cyan
Write-Host "  1. IDE 재시작" -ForegroundColor White
Write-Host "  2. 새 터미널 열기" -ForegroundColor White
Write-Host "  3. 새 키 설정 확인: secrets/gemini_api.txt" -ForegroundColor White
Write-Host "  4. 배포 파이프라인에서 새 키 설정" -ForegroundColor White
Write-Host ""
