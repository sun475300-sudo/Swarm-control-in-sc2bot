# API 키 교체 스크립트
# 기존 키를 제거하고 새 키를 적용합니다

param(
    [Parameter(Mandatory=$false)]
    [string]$NewApiKey = ""
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "API 키 교체 스크립트" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 현재 키 확인
Write-Host "1. 현재 키 확인" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Yellow

$currentKey = $env:GEMINI_API_KEY
if ($currentKey) {
    Write-Host "현재 환경 변수 키: $($currentKey.Substring(0, [Math]::Min(20, $currentKey.Length)))..." -ForegroundColor Red
    Write-Host "?? 이 키는 삭제되어야 합니다!" -ForegroundColor Red
} else {
    Write-Host "환경 변수에 키 없음" -ForegroundColor Green
}

# 파일 확인
$secretsFile = "secrets\gemini_api.txt"
$apiKeysFile = "api_keys\GEMINI_API_KEY.txt"

if (Test-Path $secretsFile) {
    $fileKey = Get-Content $secretsFile -Raw
    Write-Host "secrets/gemini_api.txt 파일 존재" -ForegroundColor Yellow
} else {
    Write-Host "secrets/gemini_api.txt 파일 없음" -ForegroundColor Green
}

Write-Host ""

# 기존 키 제거
Write-Host "2. 기존 키 제거" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Yellow

$remove = Read-Host "환경 변수에서 기존 키를 제거하시겠습니까? (Y/N)"
if ($remove -eq "Y" -or $remove -eq "y") {
    Remove-Item Env:\GEMINI_API_KEY -ErrorAction SilentlyContinue
    Remove-Item Env:\GOOGLE_API_KEY -ErrorAction SilentlyContinue
    Write-Host "? 환경 변수에서 키 제거 완료" -ForegroundColor Green
} else {
    Write-Host "환경 변수 키 제거 건너뜀" -ForegroundColor Yellow
}

Write-Host ""

# 새 키 입력
Write-Host "3. 새 키 입력" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Yellow

if (-not $NewApiKey) {
    Write-Host "?? 중요: Google AI Studio에서 새 키를 발급받으세요:" -ForegroundColor Red
    Write-Host "   https://makersuite.google.com/app/apikey" -ForegroundColor Cyan
    Write-Host ""
    $NewApiKey = Read-Host "새 API 키를 입력하세요 (또는 Enter로 건너뛰기)"
}

if ($NewApiKey) {
    # 키 형식 검증
    if (-not $NewApiKey.StartsWith("AIzaSy")) {
        Write-Host "?? 경고: 키가 'AIzaSy'로 시작하지 않습니다." -ForegroundColor Yellow
        $continue = Read-Host "계속하시겠습니까? (Y/N)"
        if ($continue -ne "Y" -and $continue -ne "y") {
            Write-Host "취소되었습니다." -ForegroundColor Yellow
            exit
        }
    }
    
    # secrets/ 폴더에 저장
    if (-not (Test-Path "secrets")) {
        New-Item -ItemType Directory -Path "secrets" | Out-Null
        Write-Host "? secrets/ 폴더 생성" -ForegroundColor Green
    }
    
    $NewApiKey | Out-File -FilePath $secretsFile -Encoding UTF8 -NoNewline
    Write-Host "? 새 키를 secrets/gemini_api.txt에 저장했습니다" -ForegroundColor Green
    Write-Host "  키: $($NewApiKey.Substring(0, [Math]::Min(20, $NewApiKey.Length)))..." -ForegroundColor Cyan
    
    # 환경 변수에도 설정할지 물어보기
    $setEnv = Read-Host "환경 변수에도 설정하시겠습니까? (Y/N)"
    if ($setEnv -eq "Y" -or $setEnv -eq "y") {
        [System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", $NewApiKey, "User")
        $env:GEMINI_API_KEY = $NewApiKey
        Write-Host "? 환경 변수에 설정 완료" -ForegroundColor Green
    }
} else {
    Write-Host "키 입력이 취소되었습니다." -ForegroundColor Yellow
    Write-Host "나중에 secrets/gemini_api.txt 파일에 직접 입력하세요." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "다음 단계:" -ForegroundColor Cyan
Write-Host "1. Google AI Studio에서 기존 키 삭제" -ForegroundColor Yellow
Write-Host "2. 새 키로 테스트: python tools/check_api_key.py" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
