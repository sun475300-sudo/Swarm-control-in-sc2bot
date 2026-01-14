# Android SHA-1 인증서 지문 가져오기
# Get Android SHA-1 Certificate Fingerprint

param(
    [string]$KeystorePath = "$env:USERPROFILE\.android\debug.keystore",
    [string]$Alias = "androiddebugkey",
    [string]$StorePass = "android",
    [string]$KeyPass = "android"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Android SHA-1 인증서 지문 가져오기" -ForegroundColor Cyan
Write-Host "Get Android SHA-1 Certificate Fingerprint" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 키스토어 파일 확인
if (-not (Test-Path $KeystorePath)) {
    Write-Host "? 키스토어 파일을 찾을 수 없습니다: $KeystorePath" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "다른 키스토어 경로를 지정하세요:" -ForegroundColor White
    Write-Host "  .\tools\get_android_sha1.ps1 -KeystorePath 'C:\path\to\your\keystore.jks'" -ForegroundColor Cyan
    exit 1
}

Write-Host "키스토어: $KeystorePath" -ForegroundColor Green
Write-Host "별칭: $Alias" -ForegroundColor Green
Write-Host ""

# keytool 명령 실행
$keytoolPath = "keytool"
if (-not (Get-Command $keytoolPath -ErrorAction SilentlyContinue)) {
    Write-Host "? keytool을 찾을 수 없습니다." -ForegroundColor Yellow
    Write-Host "  Java JDK가 설치되어 있고 PATH에 추가되어 있는지 확인하세요." -ForegroundColor White
    exit 1
}

Write-Host "SHA-1 인증서 지문 가져오는 중..." -ForegroundColor Green
Write-Host ""

try {
    $output = & $keytoolPath -list -v -keystore $KeystorePath -alias $Alias -storepass $StorePass -keypass $KeyPass 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "? keytool 실행 실패" -ForegroundColor Yellow
        Write-Host $output
        exit 1
    }
    
    # SHA-1 지문 추출
    $sha1Line = $output | Select-String -Pattern "SHA1:"
    $sha256Line = $output | Select-String -Pattern "SHA256:"
    
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "인증서 지문" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    if ($sha1Line) {
        $sha1 = ($sha1Line -split "SHA1:")[1].Trim()
        Write-Host "SHA-1:" -ForegroundColor Green
        Write-Host "  $sha1" -ForegroundColor White
        Write-Host ""
        Write-Host "Google Cloud Console에 추가할 SHA-1:" -ForegroundColor Yellow
        Write-Host "  $sha1" -ForegroundColor Cyan
        Write-Host ""
    }
    
    if ($sha256Line) {
        $sha256 = ($sha256Line -split "SHA256:")[1].Trim()
        Write-Host "SHA-256:" -ForegroundColor Green
        Write-Host "  $sha256" -ForegroundColor White
        Write-Host ""
    }
    
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Google Cloud Console 설정 방법" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. https://console.cloud.google.com/apis/credentials 접속" -ForegroundColor White
    Write-Host "2. API 키 선택" -ForegroundColor White
    Write-Host "3. '애플리케이션 제한' → 'Android 앱' 선택" -ForegroundColor White
    Write-Host "4. 패키지명 추가: com.wickedzerg.mobilegcs" -ForegroundColor White
    Write-Host "5. SHA-1 인증서 지문 추가: $sha1" -ForegroundColor White
    Write-Host ""
    
} catch {
    Write-Host "? 오류 발생: $_" -ForegroundColor Red
    exit 1
}
