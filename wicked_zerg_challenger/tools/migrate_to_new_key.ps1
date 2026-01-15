# 프로젝트 전체를 새 키로 교체 스크립트
# Migrate Entire Project to New API Key

param(
    [Parameter(Mandatory=$true)]
    [string]$NewApiKey = "",
    
    [string[]]$OldKeys = @(
        "AIzaSyC_CiEZ6CtVz9e1kAK0Ymbt1br4tGGMIIo",
        "AIzaSyD-c6nmOLolncIrcZ8DIvKCkzib_-iUZrc"
        # 주의: 이전에 사용된 키는 여기에 추가할 수 있지만, 실제 키 값은 보안상 제외됩니다.
        # 마이그레이션 시 구체적인 키 값은 명령줄 인수로 전달하세요.
    )
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "프로젝트 전체를 새 키로 교체" -ForegroundColor Cyan
Write-Host "Migrate Entire Project to New API Key" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = Split-Path -Parent $PSScriptRoot

# 새 키 필수 확인
if ([string]::IsNullOrWhiteSpace($NewApiKey)) {
    Write-Host "? 오류: 새 API 키가 제공되지 않았습니다." -ForegroundColor Red
    Write-Host ""
    Write-Host "사용법:" -ForegroundColor Yellow
    Write-Host "  .\migrate_to_new_key.ps1 -NewApiKey 'YOUR_NEW_API_KEY'" -ForegroundColor White
    Write-Host ""
    Write-Host "또는 이전 키를 제거하면서:" -ForegroundColor Yellow
    Write-Host "  .\migrate_to_new_key.ps1 -NewApiKey 'YOUR_NEW_API_KEY' -OldKeys @('OLD_KEY_1', 'OLD_KEY_2')" -ForegroundColor White
    Write-Host ""
    exit 1
}

# 새 키 검증
if (-not $NewApiKey.StartsWith("AIzaSy")) {
    Write-Host "? 경고: 새 키가 올바른 형식이 아닐 수 있습니다." -ForegroundColor Yellow
    Write-Host "  Google API 키는 'AIzaSy'로 시작해야 합니다." -ForegroundColor Yellow
    Write-Host ""
    $confirm = Read-Host "계속하시겠습니까? (yes/no)"
    if ($confirm -ne "yes") {
        exit 1
    }
}

Write-Host "새 키: $($NewApiKey.Substring(0, 10))..." -ForegroundColor Green
Write-Host ""

# ============================================================================
# 1. 새 키 파일 생성
# ============================================================================
Write-Host "[1/7] 새 키 파일 생성..." -ForegroundColor Green

# secrets 폴더에 새 키 저장 (권장)
$secretsDir = Join-Path $ProjectRoot "secrets"
if (-not (Test-Path $secretsDir)) {
    New-Item -ItemType Directory -Path $secretsDir -Force | Out-Null
}

$secretsFile = Join-Path $secretsDir "gemini_api.txt"
$NewApiKey | Set-Content $secretsFile -NoNewline
Write-Host "  ? $secretsFile 생성됨" -ForegroundColor Green

# api_keys 폴더에도 저장 (하위 호환성)
$apiKeysDir = Join-Path $ProjectRoot "api_keys"
if (-not (Test-Path $apiKeysDir)) {
    New-Item -ItemType Directory -Path $apiKeysDir -Force | Out-Null
}

$geminiKeyFile = Join-Path $apiKeysDir "GEMINI_API_KEY.txt"
$googleKeyFile = Join-Path $apiKeysDir "GOOGLE_API_KEY.txt"

$NewApiKey | Set-Content $geminiKeyFile -NoNewline
$NewApiKey | Set-Content $googleKeyFile -NoNewline
Write-Host "  ? $geminiKeyFile 생성됨" -ForegroundColor Green
Write-Host "  ? $googleKeyFile 생성됨" -ForegroundColor Green

Write-Host ""

# ============================================================================
# 2. 환경 변수에서 옛 키 제거 및 새 키 설정
# ============================================================================
Write-Host "[2/7] 환경 변수 업데이트..." -ForegroundColor Green

# 현재 세션에서 옛 키 제거
foreach ($oldKey in $OldKeys) {
    if ($env:GEMINI_API_KEY -eq $oldKey) {
        Remove-Item Env:\GEMINI_API_KEY -ErrorAction SilentlyContinue
    }
    if ($env:GOOGLE_API_KEY -eq $oldKey) {
        Remove-Item Env:\GOOGLE_API_KEY -ErrorAction SilentlyContinue
    }
}

# 새 키를 현재 세션에 설정
$env:GEMINI_API_KEY = $NewApiKey
$env:GOOGLE_API_KEY = $NewApiKey
Write-Host "  ? 현재 세션 환경 변수 설정됨" -ForegroundColor Green

# 사용자 환경 변수 업데이트
try {
    [System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", $NewApiKey, "User")
    [System.Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", $NewApiKey, "User")
    Write-Host "  ? 사용자 환경 변수 업데이트됨" -ForegroundColor Green
} catch {
    Write-Host "  ? 사용자 환경 변수 업데이트 실패: $_" -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# 3. .env 파일 업데이트
# ============================================================================
Write-Host "[3/7] .env 파일 업데이트..." -ForegroundColor Green

$envFile = Join-Path $ProjectRoot ".env"
$envExampleFile = Join-Path $ProjectRoot ".env.example"

# .env 파일 업데이트
if (Test-Path $envFile) {
    $content = Get-Content $envFile -ErrorAction SilentlyContinue
    $newContent = @()
    $keyFound = $false
    
    foreach ($line in $content) {
        if ($line -match "^GEMINI_API_KEY=" -or $line -match "^GOOGLE_API_KEY=") {
            if (-not $keyFound) {
                $newContent += "GEMINI_API_KEY=$NewApiKey"
                $newContent += "GOOGLE_API_KEY=$NewApiKey"
                $keyFound = $true
            }
            # 옛 키 라인은 제거
        } else {
            $newContent += $line
        }
    }
    
    if (-not $keyFound) {
        $newContent += "GEMINI_API_KEY=$NewApiKey"
        $newContent += "GOOGLE_API_KEY=$NewApiKey"
    }
    
    $newContent | Set-Content $envFile
    Write-Host "  ? .env 파일 업데이트됨" -ForegroundColor Green
} else {
    # .env 파일 생성
    @(
        "# API Keys",
        "GEMINI_API_KEY=$NewApiKey",
        "GOOGLE_API_KEY=$NewApiKey"
    ) | Set-Content $envFile
    Write-Host "  ? .env 파일 생성됨" -ForegroundColor Green
}

# .env.example 업데이트
if (Test-Path $envExampleFile) {
    $content = Get-Content $envExampleFile -ErrorAction SilentlyContinue
    $newContent = @()
    
    foreach ($line in $content) {
        if ($line -match "^GEMINI_API_KEY=" -or $line -match "^GOOGLE_API_KEY=") {
            $newContent += "GEMINI_API_KEY=YOUR_API_KEY_HERE"
            $newContent += "GOOGLE_API_KEY=YOUR_API_KEY_HERE"
        } else {
            $newContent += $line
        }
    }
    
    $newContent | Set-Content $envExampleFile
    Write-Host "  ? .env.example 업데이트됨" -ForegroundColor Green
}

Write-Host ""

# ============================================================================
# 4. 배포 설정에서 Secrets 참조로 변경
# ============================================================================
Write-Host "[4/7] 배포 설정 업데이트..." -ForegroundColor Green

# GitHub Actions
$githubWorkflows = Get-ChildItem -Path $ProjectRoot -Recurse -Filter ".github\workflows\*.yml" -ErrorAction SilentlyContinue
if ($githubWorkflows) {
    foreach ($workflow in $githubWorkflows) {
        $content = Get-Content $workflow.FullName -Raw -ErrorAction SilentlyContinue
        if ($content) {
            $originalContent = $content
            foreach ($oldKey in $OldKeys) {
                # 하드코딩된 키를 Secrets 참조로 변경
                $content = $content -replace [regex]::Escape($oldKey), "`${{ secrets.GEMINI_API_KEY }}"
            }
            
            if ($content -ne $originalContent) {
                Set-Content -Path $workflow.FullName -Value $content -NoNewline
                $relPath = $workflow.FullName.Replace($ProjectRoot, "").TrimStart("\")
                Write-Host "  ? GitHub Actions 업데이트: $relPath" -ForegroundColor Green
            }
        }
    }
}

# GitLab CI
$gitlabCI = Join-Path $ProjectRoot ".gitlab-ci.yml"
if (Test-Path $gitlabCI) {
    $content = Get-Content $gitlabCI -Raw -ErrorAction SilentlyContinue
    if ($content) {
        $originalContent = $content
        foreach ($oldKey in $OldKeys) {
            $content = $content -replace [regex]::Escape($oldKey), "`$GEMINI_API_KEY"
        }
        
        if ($content -ne $originalContent) {
            Set-Content -Path $gitlabCI -Value $content -NoNewline
            Write-Host "  ? GitLab CI 업데이트됨" -ForegroundColor Green
        }
    }
}

# Docker
$dockerfiles = Get-ChildItem -Path $ProjectRoot -Recurse -Filter "Dockerfile*" -ErrorAction SilentlyContinue
if ($dockerfiles) {
    foreach ($dockerfile in $dockerfiles) {
        $content = Get-Content $dockerfile.FullName -Raw -ErrorAction SilentlyContinue
        if ($content) {
            $originalContent = $content
            foreach ($oldKey in $OldKeys) {
                $content = $content -replace [regex]::Escape($oldKey), "`$GEMINI_API_KEY"
            }
            
            if ($content -ne $originalContent) {
                Set-Content -Path $dockerfile.FullName -Value $content -NoNewline
                $relPath = $dockerfile.FullName.Replace($ProjectRoot, "").TrimStart("\")
                Write-Host "  ? Dockerfile 업데이트: $relPath" -ForegroundColor Green
            }
        }
    }
}

Write-Host ""

# ============================================================================
# 5. Android local.properties 업데이트
# ============================================================================
Write-Host "[5/7] Android local.properties 업데이트..." -ForegroundColor Green

$androidProps = Join-Path $ProjectRoot "monitoring\mobile_app_android\local.properties"
if (Test-Path $androidProps) {
    $content = Get-Content $androidProps -ErrorAction SilentlyContinue
    $newContent = @()
    $keyFound = $false
    
    foreach ($line in $content) {
        if ($line -match "^GEMINI_API_KEY=") {
            $newContent += "GEMINI_API_KEY=$NewApiKey"
            $keyFound = $true
        } else {
            $newContent += $line
        }
    }
    
    if (-not $keyFound) {
        $newContent += "GEMINI_API_KEY=$NewApiKey"
    }
    
    $newContent | Set-Content $androidProps
    Write-Host "  ? Android local.properties 업데이트됨" -ForegroundColor Green
} else {
    Write-Host "  ? Android local.properties 파일이 없습니다" -ForegroundColor Green
}

Write-Host ""

# ============================================================================
# 6. 키 검증
# ============================================================================
Write-Host "[6/7] 새 키 검증..." -ForegroundColor Green

# Python 스크립트로 키 로드 확인
$pythonScript = @"
import sys
sys.path.insert(0, r'$ProjectRoot')
from tools.load_api_key import get_gemini_api_key, get_google_api_key

gemini_key = get_gemini_api_key()
google_key = get_google_api_key()

if gemini_key == '$NewApiKey':
    print('? GEMINI_API_KEY: 올바르게 로드됨')
else:
    print('? GEMINI_API_KEY: 로드 실패 또는 다른 키')

if google_key == '$NewApiKey':
    print('? GOOGLE_API_KEY: 올바르게 로드됨')
else:
    print('? GOOGLE_API_KEY: 로드 실패 또는 다른 키')
"@

$tempScript = Join-Path $env:TEMP "verify_key_$(Get-Random).py"
$pythonScript | Set-Content $tempScript

try {
    $result = python $tempScript 2>&1
    Write-Host $result
} catch {
    Write-Host "  ? 키 검증 실패: $_" -ForegroundColor Yellow
} finally {
    Remove-Item $tempScript -ErrorAction SilentlyContinue
}

Write-Host ""

# ============================================================================
# 7. 요약 및 다음 단계
# ============================================================================
Write-Host "[7/7] 요약..." -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "완료!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "다음 단계:" -ForegroundColor Cyan
Write-Host "  1. IDE 재시작 (새 환경 변수 적용)" -ForegroundColor White
Write-Host "  2. 새 터미널 열기" -ForegroundColor White
Write-Host "  3. 배포 파이프라인 Secrets 설정:" -ForegroundColor White
Write-Host "     - GitHub: Settings → Secrets → GEMINI_API_KEY" -ForegroundColor White
Write-Host "     - GitLab: Settings → CI/CD → Variables → GEMINI_API_KEY" -ForegroundColor White
Write-Host "     - Azure DevOps: Pipelines → Library → Variables" -ForegroundColor White
Write-Host "  4. 키 보안 강화 (docs/API_KEY_SECURITY_HARDENING.md 참고)" -ForegroundColor White
Write-Host ""
