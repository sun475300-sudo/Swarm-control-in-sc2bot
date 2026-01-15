# Swarm Control in SC2Bot - Windows Setup Script
# 자동 설치 스크립트

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Swarm Control in SC2Bot - Windows Setup" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Python 버전 확인
Write-Host "1. Python 버전 확인 중..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "   $pythonVersion" -ForegroundColor Green
    
    # Python 3.10 이상 확인
    $versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)"
    if ($versionMatch) {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
            Write-Host "   ??  Python 3.10 이상이 필요합니다. 현재: $pythonVersion" -ForegroundColor Red
            exit 1
        }
    }
} catch {
    Write-Host "   ? Python이 설치되어 있지 않습니다." -ForegroundColor Red
    Write-Host "   https://www.python.org/downloads/ 에서 Python 3.10+를 설치하세요." -ForegroundColor Yellow
    exit 1
}

# 가상 환경 생성
Write-Host ""
Write-Host "2. 가상 환경 생성 중..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "   가상 환경이 이미 존재합니다. 스킵합니다." -ForegroundColor Gray
} else {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   ? 가상 환경 생성 실패" -ForegroundColor Red
        exit 1
    }
    Write-Host "   ? 가상 환경 생성 완료" -ForegroundColor Green
}

# 가상 환경 활성화
Write-Host ""
Write-Host "3. 가상 환경 활성화 중..." -ForegroundColor Yellow
& ".venv\Scripts\Activate.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ??  PowerShell 실행 정책 문제. 다음 명령을 실행하세요:" -ForegroundColor Yellow
    Write-Host "   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor White
    Write-Host ""
    Write-Host "   수동으로 가상 환경을 활성화하세요: .venv\Scripts\activate" -ForegroundColor Yellow
}

# pip 업그레이드
Write-Host ""
Write-Host "4. pip 업그레이드 중..." -ForegroundColor Yellow
python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ??  pip 업그레이드 실패 (계속 진행)" -ForegroundColor Yellow
}

# 의존성 설치
Write-Host ""
Write-Host "5. 의존성 설치 중..." -ForegroundColor Yellow
Write-Host "   (이 작업은 몇 분이 걸릴 수 있습니다)" -ForegroundColor Gray

if (Test-Path "wicked_zerg_challenger\requirements.txt") {
    Set-Location "wicked_zerg_challenger"
    pip install -r requirements.txt
    Set-Location ..
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   ??  일부 의존성 설치 실패 (수동 설치 필요)" -ForegroundColor Yellow
    } else {
        Write-Host "   ? 의존성 설치 완료" -ForegroundColor Green
    }
} else {
    Write-Host "   ? requirements.txt 파일을 찾을 수 없습니다." -ForegroundColor Red
    exit 1
}

# 환경 변수 파일 설정
Write-Host ""
Write-Host "6. 환경 변수 파일 설정 중..." -ForegroundColor Yellow
if (Test-Path "wicked_zerg_challenger\api_keys\.env.example") {
    if (-not (Test-Path "wicked_zerg_challenger\.env")) {
        Copy-Item "wicked_zerg_challenger\api_keys\.env.example" "wicked_zerg_challenger\.env"
        Write-Host "   ? .env 파일 생성 완료" -ForegroundColor Green
        Write-Host "   ??  wicked_zerg_challenger\.env 파일을 편집하여 API 키를 설정하세요." -ForegroundColor Yellow
    } else {
        Write-Host "   .env 파일이 이미 존재합니다." -ForegroundColor Gray
    }
} else {
    Write-Host "   ??  .env.example 파일을 찾을 수 없습니다. (선택사항)" -ForegroundColor Yellow
}

# 설치 확인
Write-Host ""
Write-Host "7. 설치 확인 중..." -ForegroundColor Yellow
$errors = @()

try {
    python -c "import sc2; print('SC2 library OK')" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        $errors += "sc2 library"
    } else {
        Write-Host "   ? SC2 library" -ForegroundColor Green
    }
} catch {
    $errors += "sc2 library"
}

try {
    python -c "import torch; print('PyTorch OK')" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        $errors += "PyTorch"
    } else {
        Write-Host "   ? PyTorch" -ForegroundColor Green
    }
} catch {
    $errors += "PyTorch"
}

# 최종 메시지
Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
if ($errors.Count -eq 0) {
    Write-Host "? 설치 완료!" -ForegroundColor Green
    Write-Host ""
    Write-Host "다음 단계:" -ForegroundColor Yellow
    Write-Host "  1. .env 파일 설정: wicked_zerg_challenger\.env" -ForegroundColor White
    Write-Host "  2. 게임 실행: python run.py" -ForegroundColor White
    Write-Host ""
    Write-Host "자세한 내용은 SETUP.md를 참조하세요." -ForegroundColor Gray
} else {
    Write-Host "??  설치 완료 (일부 오류 발생)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "설치되지 않은 패키지:" -ForegroundColor Yellow
    foreach ($error in $errors) {
        Write-Host "  - $error" -ForegroundColor White
    }
    Write-Host ""
    Write-Host "수동으로 설치하세요:" -ForegroundColor Yellow
    Write-Host "  pip install $($errors -join ' ')" -ForegroundColor White
}
Write-Host "======================================================================" -ForegroundColor Cyan
