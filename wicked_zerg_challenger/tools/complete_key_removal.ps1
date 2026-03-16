# ������ API Ű ���� ��ũ��Ʈ
# Complete API Key Removal Script

param(
    [switch]$SkipGitHistory = $false
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "������ API Ű ����" -ForegroundColor Cyan
Write-Host "Complete API Key Removal" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ������ Ű ���
$KeysToRemove = @(
    $env:OLD_GOOGLE_KEY_1,
    $env:OLD_GOOGLE_KEY_2
) | Where-Object { $_ -ne $null }

# ������Ʈ ��Ʈ
$ProjectRoot = Split-Path -Parent $PSScriptRoot

# ============================================================================
# 1. ȯ�� �������� Ű ����
# ============================================================================
Write-Host "[1/5] ȯ�� �������� Ű ����..." -ForegroundColor Green

# ���� ���ǿ��� ����
Remove-Item Env:\GEMINI_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:\GOOGLE_API_KEY -ErrorAction SilentlyContinue
Write-Host "  ? ���� ���� ȯ�� ���� ���ŵ�" -ForegroundColor Green

# ����� ȯ�� �������� ����
try {
    [System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", $null, "User")
    [System.Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", $null, "User")
    Write-Host "  ? ����� ȯ�� ���� ���ŵ�" -ForegroundColor Green
} catch {
    Write-Host "  ? ����� ȯ�� ���� ���� ����: $_" -ForegroundColor Yellow
}

# �ý��� ȯ�� �������� ���� (������ ���� �ʿ�)
try {
    [System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", $null, "Machine")
    [System.Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", $null, "Machine")
    Write-Host "  ? �ý��� ȯ�� ���� ���ŵ�" -ForegroundColor Green
} catch {
    Write-Host "  ? �ý��� ȯ�� ���� ���� ���� (������ ���� �ʿ�): $_" -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# 2. .env ���Ͽ��� Ű ����
# ============================================================================
Write-Host "[2/5] .env ���Ͽ��� Ű ����..." -ForegroundColor Green

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
        Write-Host "  ? .env ���Ͽ��� Ű ���ŵ�" -ForegroundColor Green
    } else {
        Write-Host "  ? .env ���Ͽ� Ű�� �����ϴ�" -ForegroundColor Green
    }
} else {
    Write-Host "  ? .env ������ �����ϴ�" -ForegroundColor Green
}

Write-Host ""

# ============================================================================
# 3. ���� ���Ͽ��� ���� Ű ����ŷ
# ============================================================================
Write-Host "[3/5] ���� ���Ͽ��� ���� Ű ����ŷ..." -ForegroundColor Green

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
            Write-Host "  ? $relPath ����ŷ��" -ForegroundColor Green
        }
    }
}

if ($maskedCount -eq 0) {
    Write-Host "  ? ����ŷ�� ������ �����ϴ�" -ForegroundColor Green
} else {
    Write-Host "  ? $maskedCount �� ���� ����ŷ �Ϸ�" -ForegroundColor Green
}

Write-Host ""

# ============================================================================
# 4. �ڵ� ���Ͽ��� �ϵ��ڵ��� Ű ����
# ============================================================================
Write-Host "[4/5] �ڵ� ���Ͽ��� �ϵ��ڵ��� Ű ����..." -ForegroundColor Green

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
            # �ϵ��ڵ��� Ű�� "YOUR_API_KEY_HERE" �Ǵ� ȯ�� ���� ������ ����
            $pattern = '["\''`]?' + [regex]::Escape($key) + '["\''`]?'
            $content = $content -replace $pattern, '"YOUR_API_KEY_HERE"'
        }
        
        if ($content -ne $originalContent) {
            Set-Content -Path $file.FullName -Value $content -NoNewline
            $removedCount++
            $relPath = $file.FullName.Replace($ProjectRoot, "").TrimStart("\")
            Write-Host "  ? $relPath ������" -ForegroundColor Green
        }
    }
}

if ($removedCount -eq 0) {
    Write-Host "  ? ������ Ű�� �����ϴ�" -ForegroundColor Green
} else {
    Write-Host "  ? $removedCount �� ���� ���� �Ϸ�" -ForegroundColor Green
}

Write-Host ""

# ============================================================================
# 5. Git History���� Ű ����
# ============================================================================
if (-not $SkipGitHistory) {
    Write-Host "[5/5] Git History���� Ű ����..." -ForegroundColor Green
    
    # git-filter-repo Ȯ��
    $filterRepoInstalled = Get-Command git-filter-repo -ErrorAction SilentlyContinue
    
    if (-not $filterRepoInstalled) {
        Write-Host "  ? git-filter-repo�� ��ġ�Ǿ� ���� �ʽ��ϴ�." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  ��ġ ���:" -ForegroundColor Yellow
        Write-Host "    pip install git-filter-repo" -ForegroundColor White
        Write-Host ""
        Write-Host "  �Ǵ� BFG Repo-Cleaner ���:" -ForegroundColor Yellow
        Write-Host "    https://rtyley.github.io/bfg-repo-cleaner/" -ForegroundColor White
        Write-Host ""
        
        $useBFG = Read-Host "BFG�� ����Ͻðڽ��ϱ�? (yes/no)"
        if ($useBFG -eq "yes") {
            Write-Host "  BFG ��� ���:" -ForegroundColor Yellow
            Write-Host "    1. keys.txt ���� ���� (�� Ű�� �� �پ�)" -ForegroundColor White
            Write-Host "    2. java -jar bfg.jar --replace-text keys.txt" -ForegroundColor White
            Write-Host "    3. git reflog expire --expire=now --all" -ForegroundColor White
            Write-Host "    4. git gc --prune=now --aggressive" -ForegroundColor White
        }
    } else {
        Write-Host "  ? �� �۾��� Git history�� ���������� �����մϴ�!" -ForegroundColor Red
        Write-Host "  ? ��� �������� �˷��� �մϴ�!" -ForegroundColor Red
        Write-Host "  ? ����� ���� �����ϼ���!" -ForegroundColor Red
        Write-Host ""
        
        $confirm = Read-Host "����Ͻðڽ��ϱ�? (yes/no)"
        if ($confirm -eq "yes") {
            # ��� �귣ġ ����
            $backupBranch = "backup-before-key-removal-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
            git branch $backupBranch
            Write-Host "  ? ��� �귣ġ ����: $backupBranch" -ForegroundColor Green
            
            # �� Ű ����
            foreach ($key in $KeysToRemove) {
                Write-Host "  Ű ���� ��: $($key.Substring(0, 10))..." -ForegroundColor Yellow
                
                # replace-text ���� ����
                $replaceFile = Join-Path $env:TEMP "replace-text-$(Get-Random).txt"
                "$key==>REDACTED" | Set-Content $replaceFile
                
                # git-filter-repo ����
                Push-Location $ProjectRoot
                try {
                    git filter-repo --replace-text $replaceFile --force
                    Write-Host "    ? �Ϸ�" -ForegroundColor Green
                } catch {
                    Write-Host "    ? ����: $_" -ForegroundColor Red
                } finally {
                    Remove-Item $replaceFile -ErrorAction SilentlyContinue
                    Pop-Location
                }
            }
            
            Write-Host ""
            Write-Host "  ? ���� ����ҿ� ���� Ǫ�ð� �ʿ��մϴ�:" -ForegroundColor Red
            Write-Host "    git push origin --force --all" -ForegroundColor White
            Write-Host "    git push origin --force --tags" -ForegroundColor White
        } else {
            Write-Host "  ��ҵǾ����ϴ�." -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "[5/5] Git History ���� �ǳʶ� (--SkipGitHistory �ɼ�)" -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# ���� Ȯ��
# ============================================================================
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "���� Ȯ��" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "������Ʈ ���Ͽ��� Ű �˻�..." -ForegroundColor Green
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
        Write-Host "  ? �߰ߵ�: $($key.Substring(0, 10))..." -ForegroundColor Yellow
        foreach ($result in $results | Select-Object -First 5) {
            $relPath = $result.Path.Replace($ProjectRoot, "").TrimStart("\")
            Write-Host "    - $relPath : $($result.LineNumber)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ? ����: $($key.Substring(0, 10))..." -ForegroundColor Green
    }
}

Write-Host ""

if ($foundKeys.Count -eq 0) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "? �Ϸ�! ��� Ű�� ���ŵǾ����ϴ�." -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "? �Ϻ� Ű�� �����ֽ��ϴ�. �������� Ȯ���ϼ���." -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "���� �ܰ�:" -ForegroundColor Cyan
Write-Host "  1. �� Ű ���� Ȯ��: secrets/gemini_api.txt" -ForegroundColor White
Write-Host "  2. Git history ���� (�ʿ��� ���)" -ForegroundColor White
Write-Host "  3. �������� �˸� (Git history ���� ��)" -ForegroundColor White
Write-Host ""
