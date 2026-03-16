# ������ ȯ�� ���� ĳ�� �� Ű ���� ��ũ��Ʈ
# Complete Environment Variable Cache and Key Removal Script

param(
    [switch]$SkipIDE = $false,
    [switch]$SkipDeployment = $false
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "������ ȯ�� ���� ĳ�� �� Ű ����" -ForegroundColor Cyan
Write-Host "Complete Environment Cleanup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$KeysToRemove = @(
    $env:OLD_GOOGLE_KEY_1,
    $env:OLD_GOOGLE_KEY_2
) | Where-Object { $_ -ne $null }

# ============================================================================
# 1. IDE ȯ�� ���� ĳ�� ����
# ============================================================================
if (-not $SkipIDE) {
    Write-Host "[1/6] IDE ȯ�� ���� ĳ�� ����..." -ForegroundColor Green
    
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
                Write-Host "  ? VS Code ĳ�� ����: $path" -ForegroundColor Green
            } catch {
                Write-Host "  ? VS Code ĳ�� ���� ����: $path" -ForegroundColor Yellow
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
                Write-Host "  ? Android Studio ĳ�� ����: $($path.FullName)" -ForegroundColor Green
            } catch {
                Write-Host "  ? Android Studio ĳ�� ���� ����: $($path.FullName)" -ForegroundColor Yellow
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
                Write-Host "  ? IntelliJ IDEA ĳ�� ����: $($path.FullName)" -ForegroundColor Green
            } catch {
                Write-Host "  ? IntelliJ IDEA ĳ�� ���� ����: $($path.FullName)" -ForegroundColor Yellow
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
                Write-Host "  ? PyCharm ĳ�� ����: $($path.FullName)" -ForegroundColor Green
            } catch {
                Write-Host "  ? PyCharm ĳ�� ���� ����: $($path.FullName)" -ForegroundColor Yellow
            }
        }
    }
    
    Write-Host ""
}

# ============================================================================
# 2. �͹̳�/��ġ ���Ͽ��� ���� Ű ����
# ============================================================================
Write-Host "[2/6] �͹̳�/��ġ ���Ͽ��� ���� Ű ����..." -ForegroundColor Green

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
            # ȯ�� ���� ���� ���� ���� �Ǵ� �ּ� ó��
            $patterns = @(
                "set\s+.*$([regex]::Escape($key))",
                "\$env:.*$([regex]::Escape($key))",
                "export\s+.*$([regex]::Escape($key))",
                [regex]::Escape($key)
            )
            
            foreach ($pattern in $patterns) {
                # �ּ� ó��
                $content = $content -replace "($pattern)", "# REMOVED: `$1"
            }
        }
        
        if ($content -ne $originalContent) {
            Set-Content -Path $file.FullName -Value $content -NoNewline
            $cleanedBatchCount++
            $relPath = $file.FullName.Replace($ProjectRoot, "").TrimStart("\")
            Write-Host "  ? $relPath ������" -ForegroundColor Green
        }
    }
}

if ($cleanedBatchCount -eq 0) {
    Write-Host "  ? ������ ��ġ ������ �����ϴ�" -ForegroundColor Green
} else {
    Write-Host "  ? $cleanedBatchCount �� ��ġ ���� ���� �Ϸ�" -ForegroundColor Green
}

Write-Host ""

# ============================================================================
# 3. ȯ�� ���� ���� ����
# ============================================================================
Write-Host "[3/6] ȯ�� ���� ���� ����..." -ForegroundColor Green

# ���� ����
Remove-Item Env:\GEMINI_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:\GOOGLE_API_KEY -ErrorAction SilentlyContinue
Write-Host "  ? ���� ���� ȯ�� ���� ���ŵ�" -ForegroundColor Green

# ����� ȯ�� ����
try {
    [System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", $null, "User")
    [System.Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", $null, "User")
    Write-Host "  ? ����� ȯ�� ���� ���ŵ�" -ForegroundColor Green
} catch {
    Write-Host "  ? ����� ȯ�� ���� ���� ����: $_" -ForegroundColor Yellow
}

# �ý��� ȯ�� ���� (������ ���� �ʿ�)
try {
    [System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", $null, "Machine")
    [System.Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", $null, "Machine")
    Write-Host "  ? �ý��� ȯ�� ���� ���ŵ�" -ForegroundColor Green
} catch {
    Write-Host "  ? �ý��� ȯ�� ���� ���� ���� (������ ���� �ʿ�): $_" -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# 4. ���� ���������ο��� �� Ű ����
# ============================================================================
if (-not $SkipDeployment) {
    Write-Host "[4/6] ���� ���������ο��� �� Ű ����..." -ForegroundColor Green
    
    # GitHub Actions
    $githubWorkflows = Get-ChildItem -Path $ProjectRoot -Recurse -Filter ".github\workflows\*.yml" -ErrorAction SilentlyContinue
    foreach ($workflow in $githubWorkflows) {
        $content = Get-Content $workflow.FullName -Raw -ErrorAction SilentlyContinue
        if ($content) {
            $originalContent = $content
            foreach ($key in $KeysToRemove) {
                # Secrets���� Ű ���� �Ǵ� ����ŷ
                $content = $content -replace [regex]::Escape($key), "REDACTED"
            }
            
            if ($content -ne $originalContent) {
                Set-Content -Path $workflow.FullName -Value $content -NoNewline
                $relPath = $workflow.FullName.Replace($ProjectRoot, "").TrimStart("\")
                Write-Host "  ? GitHub Actions ����: $relPath" -ForegroundColor Green
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
                Write-Host "  ? GitLab CI ������" -ForegroundColor Green
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
                Write-Host "  ? Azure DevOps ����: $relPath" -ForegroundColor Green
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
                Write-Host "  ? Dockerfile ����: $relPath" -ForegroundColor Green
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
                Write-Host "  ? Kubernetes ���� ����: $relPath" -ForegroundColor Green
            }
        }
    }
    
    Write-Host ""
}

# ============================================================================
# 5. .env ���� ����
# ============================================================================
Write-Host "[5/6] .env ���� ����..." -ForegroundColor Green

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
            Write-Host "  ? $relPath ������" -ForegroundColor Green
        }
    }
}

Write-Host ""

# ============================================================================
# 6. ���μ��� ����� �ȳ�
# ============================================================================
Write-Host "[6/6] ���μ��� ����� �ȳ�..." -ForegroundColor Green
Write-Host "  ? ���� ���μ����� ������ϼ���:" -ForegroundColor Yellow
Write-Host "    1. IDE (VS Code, Android Studio, IntelliJ ��)" -ForegroundColor White
Write-Host "    2. �͹̳� ���� (�� �͹̳� ����)" -ForegroundColor White
Write-Host "    3. ���� ���������� (GitHub Actions, GitLab CI ��)" -ForegroundColor White
Write-Host ""

# ============================================================================
# ���� Ȯ��
# ============================================================================
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "�Ϸ�!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "���� �ܰ�:" -ForegroundColor Cyan
Write-Host "  1. IDE �����" -ForegroundColor White
Write-Host "  2. �� �͹̳� ����" -ForegroundColor White
Write-Host "  3. �� Ű ���� Ȯ��: secrets/gemini_api.txt" -ForegroundColor White
Write-Host "  4. ���� ���������ο��� �� Ű ����" -ForegroundColor White
Write-Host ""
