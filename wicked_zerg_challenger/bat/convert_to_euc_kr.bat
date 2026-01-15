@echo off
chcp 65001 > nul
REM 전체 파일을 EUC-KR 인코딩으로 변환하는 배치 파일

REM CRITICAL: Change to wicked_zerg_challenger directory
cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo 전체 파일을 EUC-KR 인코딩으로 변환
echo ======================================================================
echo.
echo ??  주의사항:
echo 1. Python 소스 코드는 일반적으로 UTF-8을 사용합니다
echo 2. EUC-KR로 변환하면 일부 특수문자나 영어가 깨질 수 있습니다
echo 3. 변환 전에 백업을 권장합니다
echo 4. 이미 UTF-8로 잘 작동하는 파일은 변환하지 않는 것이 좋습니다
echo.

python tools\convert_to_euc_kr.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] 변환 중 오류가 발생했습니다!
    pause
    exit /b 1
)

echo.
echo [SUCCESS] 변환 완료!
pause
