# ���� ���������ο��� �� Ű ���� ��ũ��Ʈ
# Remove Old Keys from Deployment Pipelines

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$KeysToRemove = @(
    $env:OLD_GOOGLE_KEY_1,
    $env:OLD_GOOGLE_KEY_2
) | Where-Object { $_ -ne $null }

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "���� ���������ο��� �� Ű ����" -ForegroundColor Cyan
Write-Host "Remove Old Keys from Deployment Pipelines" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# GitHub Actions
# ============================================================================
Write-Host "[1/5] GitHub Actions ����..." -ForegroundColor Green

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
                Write-Host "  ? $relPath ������" -ForegroundColor Green
            }
        }
    }
} else {
    Write-Host "  ? GitHub Actions ������ �����ϴ�" -ForegroundColor Green
}

Write-Host ""

# ============================================================================
# GitLab CI
# ============================================================================
Write-Host "[2/5] GitLab CI ����..." -ForegroundColor Green

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
            Write-Host "  ? .gitlab-ci.yml ������" -ForegroundColor Green
        }
    }
} else {
    Write-Host "  ? GitLab CI ������ �����ϴ�" -ForegroundColor Green
}

Write-Host ""

# ============================================================================
# Azure DevOps
# ============================================================================
Write-Host "[3/5] Azure DevOps ����..." -ForegroundColor Green

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
                Write-Host "  ? $relPath ������" -ForegroundColor Green
            }
        }
    }
} else {
    Write-Host "  ? Azure DevOps ������ �����ϴ�" -ForegroundColor Green
}

Write-Host ""

# ============================================================================
# Docker
# ============================================================================
Write-Host "[4/5] Dockerfile ����..." -ForegroundColor Green

$dockerfiles = Get-ChildItem -Path $ProjectRoot -Recurse -Filter "Dockerfile*" -ErrorAction SilentlyContinue
if ($dockerfiles) {
    foreach ($dockerfile in $dockerfiles) {
        $content = Get-Content $dockerfile.FullName -Raw -ErrorAction SilentlyContinue
        if ($content) {
            $originalContent = $content
            foreach ($key in $KeysToRemove) {
                # ENV ������ ����
                $content = $content -replace [regex]::Escape($key), "`$GEMINI_API_KEY"
            }
            
            if ($content -ne $originalContent) {
                Set-Content -Path $dockerfile.FullName -Value $content -NoNewline
                $relPath = $dockerfile.FullName.Replace($ProjectRoot, "").TrimStart("\")
                Write-Host "  ? $relPath ������" -ForegroundColor Green
            }
        }
    }
} else {
    Write-Host "  ? Dockerfile�� �����ϴ�" -ForegroundColor Green
}

Write-Host ""

# ============================================================================
# Kubernetes
# ============================================================================
Write-Host "[5/5] Kubernetes ���� ����..." -ForegroundColor Green

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
                # Secret ������ ����
                $content = $content -replace [regex]::Escape($key), "`$(GEMINI_API_KEY)"
            }
            
            if ($content -ne $originalContent) {
                Set-Content -Path $k8sFile.FullName -Value $content -NoNewline
                $relPath = $k8sFile.FullName.Replace($ProjectRoot, "").TrimStart("\")
                Write-Host "  ? $relPath ������" -ForegroundColor Green
            }
        }
    }
} else {
    Write-Host "  ? Kubernetes ������ �����ϴ�" -ForegroundColor Green
}

Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "�Ϸ�!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "���� �ܰ�:" -ForegroundColor Cyan
Write-Host "  1. GitHub Secrets�� �� Ű ����" -ForegroundColor White
Write-Host "  2. GitLab CI/CD Variables�� �� Ű ����" -ForegroundColor White
Write-Host "  3. Azure DevOps Variables�� �� Ű ����" -ForegroundColor White
Write-Host "  4. Docker ȯ�� ������ �� Ű ����" -ForegroundColor White
Write-Host "  5. Kubernetes Secrets�� �� Ű ����" -ForegroundColor White
Write-Host ""
