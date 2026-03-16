# Ű ���� Ȯ�� ��ũ��Ʈ
# Verify Key Removal Script

$ProjectRoot = Split-Path -Parent $PSScriptRoot

$KeysToCheck = @(
    $env:OLD_GOOGLE_KEY_1,
    $env:OLD_GOOGLE_KEY_2
) | Where-Object { $_ -ne $null }

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Ű ���� Ȯ��" -ForegroundColor Cyan
Write-Host "Key Removal Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$allClean = $true

# 1. ȯ�� ���� Ȯ��
Write-Host "[1/4] ȯ�� ���� Ȯ��..." -ForegroundColor Green
$envKeys = @("GEMINI_API_KEY", "GOOGLE_API_KEY")
foreach ($envKey in $envKeys) {
    $value = [System.Environment]::GetEnvironmentVariable($envKey, "User")
    if ($value) {
        foreach ($oldKey in $KeysToCheck) {
            if ($value -eq $oldKey) {
                Write-Host "  ? �߰ߵ�: $envKey = $($oldKey.Substring(0, 10))..." -ForegroundColor Yellow
                $allClean = $false
            }
        }
    }
}
if ($allClean) {
    Write-Host "  ? ȯ�� ������ ������ Ű�� �����ϴ�" -ForegroundColor Green
}
Write-Host ""

# 2. .env ���� Ȯ��
Write-Host "[2/4] .env ���� Ȯ��..." -ForegroundColor Green
$envFile = Join-Path $ProjectRoot ".env"
if (Test-Path $envFile) {
    $content = Get-Content $envFile -ErrorAction SilentlyContinue
    foreach ($line in $content) {
        foreach ($oldKey in $KeysToCheck) {
            if ($line -match [regex]::Escape($oldKey)) {
                Write-Host "  ? �߰ߵ�: .env ���Ͽ� ������ Ű" -ForegroundColor Yellow
                $allClean = $false
            }
        }
    }
    if ($allClean) {
        Write-Host "  ? .env ���Ͽ� ������ Ű�� �����ϴ�" -ForegroundColor Green
    }
} else {
    Write-Host "  ? .env ������ �����ϴ�" -ForegroundColor Green
}
Write-Host ""

# 3. ������Ʈ ���� �˻�
Write-Host "[3/4] ������Ʈ ���� �˻�..." -ForegroundColor Green
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
        Write-Host "  ? �߰ߵ�: $($oldKey.Substring(0, 10))..." -ForegroundColor Yellow
        foreach ($result in $results | Select-Object -First 3) {
            $relPath = $result.Path.Replace($ProjectRoot, "").TrimStart("\")
            Write-Host "    - $relPath : $($result.LineNumber)" -ForegroundColor Yellow
        }
        $allClean = $false
    }
}

if ($foundInFiles.Count -eq 0) {
    Write-Host "  ? ������Ʈ ���Ͽ� ������ Ű�� �����ϴ�" -ForegroundColor Green
}
Write-Host ""

# 4. Git History �˻�
Write-Host "[4/4] Git History �˻�..." -ForegroundColor Green
Push-Location $ProjectRoot
try {
    foreach ($oldKey in $KeysToCheck) {
        $gitResults = git log -p --all -S $oldKey --source --all 2>$null | Select-String -Pattern ([regex]::Escape($oldKey))
        if ($gitResults) {
            Write-Host "  ? �߰ߵ�: Git history�� $($oldKey.Substring(0, 10))..." -ForegroundColor Yellow
            Write-Host "    �� git-filter-repo �Ǵ� BFG�� ���� �ʿ�" -ForegroundColor Yellow
            $allClean = $false
        }
    }
    
    if ($allClean) {
        Write-Host "  ? Git history�� ������ Ű�� �����ϴ�" -ForegroundColor Green
    }
} catch {
    Write-Host "  ? Git history �˻� ����: $_" -ForegroundColor Yellow
} finally {
    Pop-Location
}

Write-Host ""

# ���� ���
Write-Host "========================================" -ForegroundColor Cyan
if ($allClean) {
    Write-Host "? �Ϸ�! ��� ������ Ű�� ���ŵǾ����ϴ�." -ForegroundColor Green
    Write-Host "? '���� Ű�� ����' �����Դϴ�." -ForegroundColor Green
} else {
    Write-Host "? �Ϻ� ������ Ű�� �����ֽ��ϴ�." -ForegroundColor Yellow
    Write-Host "  �� tools/complete_key_removal.ps1 ���� ����" -ForegroundColor Yellow
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
