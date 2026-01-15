@echo off
chcp 65001 > nul
REM 배치 파일 인코딩 수정 도구

echo ======================================================================
echo 배치 파일 인코딩 수정
echo ======================================================================
echo.
echo 이 스크립트는 bat 폴더의 모든 배치 파일을 UTF-8로 변환합니다.
echo.

cd /d "%~dp0"

echo [INFO] 현재 디렉토리: %CD%
echo.

REM PowerShell을 사용하여 모든 .bat 파일을 UTF-8로 변환
for %%f in (*.bat) do (
    echo [INFO] 변환 중: %%f
    powershell -Command "Get-Content '%%f' -Raw | Out-File -Encoding UTF8 '%%f.tmp' -NoNewline"
    if exist "%%f.tmp" (
        move /y "%%f.tmp" "%%f" > nul
        echo [OK] %%f 변환 완료
    ) else (
        echo [WARNING] %%f 변환 실패
    )
)

echo.
echo ======================================================================
echo 인코딩 수정 완료!
echo ======================================================================
echo.
echo 모든 배치 파일이 UTF-8로 변환되었습니다.
echo.
pause
