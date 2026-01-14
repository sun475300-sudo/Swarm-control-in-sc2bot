# 배포 파이프라인에서 옛 키 제거 스크립트
# Remove Old Keys from Deployment Pipelines

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$KeysToRemove = @(
    "AIzaSyC_CiEZ6CtVz9e1kAK0Ymbt1br4tGGMIIo",
    "AIzaSyD-c6nmOLolncIrcZ8DIvKCkzib_-iUZrc"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "배포 파이프라인에서 옛 키 제거" -ForegroundColor Cyan
Write-Host "Remove Old Keys from Deployment Pipelines" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# GitHub Actions
# ============================================================================
Write-Host "[1/5] GitHub Actions 정리..." -ForegroundColor Green

$githubWorkflows = Get-ChildItem -Path $ProjectRoot -Recurse -Filter ".github\workflows\*.yml" -ErrorAction SilentlyContinue
if ($githubWorkflows) {
    foreach ($workflow in $githubWorkflows) {
        $content = Get-Content $workflow.FullName -Raw -ErrorAction SilentlyContinue
        if ($content) {
            $originalContent = $content
            foreach ($key in $KeysToRemove) {
                $content = $content -replace [regex]::Escape($key), "`${{ secrets.GEMINI_API_KEY }}"
            }
            
            if ($content -ne $originalContent) {
                Set-Content -Path $workflow.FullName -Value $content -NoNewline
                $relPath = $workflow.FullName.Replace($ProjectRoot, "").TrimStart("\")
                Write-Host "  ? $relPath 정리됨" -ForegroundColor Green
            }
        }
    }
} else {
    Write-Host "  ? GitHub Actions 파일이 없습니다" -ForegroundColor Green
}

Write-Host ""

# ============================================================================
# GitLab CI
# ============================================================================
Write-Host "[2/5] GitLab CI 정리..." -ForegroundColor Green

$gitlabCI = Join-Path $ProjectRoot ".gitlab-ci.yml"
if (Test-Path $gitlabCI) {
    $content = Get-Content $gitlabCI -Raw -ErrorAction SilentlyContinue
    if ($content) {
        $originalContent = $content
        foreach ($key in $KeysToRemove) {
            $content = $content -replace [regex]::Escape($key), "`$GEMINI_API_KEY"
        }
        
        if ($content -ne $originalContent) {
            Set-Content -Path $gitlabCI -Value $content -NoNewline
            Write-Host "  ? .gitlab-ci.yml 정리됨" -ForegroundColor Green
        }
    }
} else {
    Write-Host "  ? GitLab CI 파일이 없습니다" -ForegroundColor Green
}

Write-Host ""

# ============================================================================
# Azure DevOps
# ============================================================================
Write-Host "[3/5] Azure DevOps 정리..." -ForegroundColor Green

$azurePipelines = Get-ChildItem -Path $ProjectRoot -Recurse -Filter "azure-pipelines.yml" -ErrorAction SilentlyContinue
if ($azurePipelines) {
    foreach ($pipeline in $azurePipelines) {
        $content = Get-Content $pipeline.FullName -Raw -ErrorAction SilentlyContinue
        if ($content) {
            $originalContent = $content
            foreach ($key in $KeysToRemove) {
                $content = $content -replace [regex]::Escape($key), "`$(GEMINI_API_KEY)"
            }
            
            if ($content -ne $originalContent) {
                Set-Content -Path $pipeline.FullName -Value $content -NoNewline
                $relPath = $pipeline.FullName.Replace($ProjectRoot, "").TrimStart("\")
                Write-Host "  ? $relPath 정리됨" -ForegroundColor Green
            }
        }
    }
} else {
    Write-Host "  ? Azure DevOps 파일이 없습니다" -ForegroundColor Green
}

Write-Host ""

# ============================================================================
# Docker
# ============================================================================
Write-Host "[4/5] Dockerfile 정리..." -ForegroundColor Green

$dockerfiles = Get-ChildItem -Path $ProjectRoot -Recurse -Filter "Dockerfile*" -ErrorAction SilentlyContinue
if ($dockerfiles) {
    foreach ($dockerfile in $dockerfiles) {
        $content = Get-Content $dockerfile.FullName -Raw -ErrorAction SilentlyContinue
        if ($content) {
            $originalContent = $content
            foreach ($key in $KeysToRemove) {
                # ENV 변수로 변경
                $content = $content -replace [regex]::Escape($key), "`$GEMINI_API_KEY"
            }
            
            if ($content -ne $originalContent) {
                Set-Content -Path $dockerfile.FullName -Value $content -NoNewline
                $relPath = $dockerfile.FullName.Replace($ProjectRoot, "").TrimStart("\")
                Write-Host "  ? $relPath 정리됨" -ForegroundColor Green
            }
        }
    }
} else {
    Write-Host "  ? Dockerfile이 없습니다" -ForegroundColor Green
}

Write-Host ""

# ============================================================================
# Kubernetes
# ============================================================================
Write-Host "[5/5] Kubernetes 파일 정리..." -ForegroundColor Green

$k8sFiles = Get-ChildItem -Path $ProjectRoot -Recurse -Include "*.yaml", "*.yml" | 
    Where-Object { 
        $_.FullName -match "k8s|kubernetes|deployment|service" -and
        $_.FullName -notmatch "\.git" -and
        $_.FullName -notmatch "\.github"
    }

if ($k8sFiles) {
    foreach ($k8sFile in $k8sFiles) {
        $content = Get-Content $k8sFile.FullName -Raw -ErrorAction SilentlyContinue
        if ($content) {
            $originalContent = $content
            foreach ($key in $KeysToRemove) {
                # Secret 참조로 변경
                $content = $content -replace [regex]::Escape($key), "`$(GEMINI_API_KEY)"
            }
            
            if ($content -ne $originalContent) {
                Set-Content -Path $k8sFile.FullName -Value $content -NoNewline
                $relPath = $k8sFile.FullName.Replace($ProjectRoot, "").TrimStart("\")
                Write-Host "  ? $relPath 정리됨" -ForegroundColor Green
            }
        }
    }
} else {
    Write-Host "  ? Kubernetes 파일이 없습니다" -ForegroundColor Green
}

Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "완료!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "다음 단계:" -ForegroundColor Cyan
Write-Host "  1. GitHub Secrets에 새 키 설정" -ForegroundColor White
Write-Host "  2. GitLab CI/CD Variables에 새 키 설정" -ForegroundColor White
Write-Host "  3. Azure DevOps Variables에 새 키 설정" -ForegroundColor White
Write-Host "  4. Docker 환경 변수에 새 키 설정" -ForegroundColor White
Write-Host "  5. Kubernetes Secrets에 새 키 설정" -ForegroundColor White
Write-Host ""
