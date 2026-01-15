@echo off
chcp 65001 > nul
REM 최종 로직 검사 배치 파일

REM CRITICAL: Change to wicked_zerg_challenger directory
cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo 최종 로직 검사
echo ======================================================================
echo.
echo 깃허브 업로드 전 모든 파일의 로직을 검사합니다.
echo.

python tools\final_logic_check.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ======================================================================
    echo [SUCCESS] 모든 검사 통과!
    echo ======================================================================
    echo.
    echo 깃허브에 업로드할 준비가 되었습니다.
    echo.
    echo 다음 단계:
    echo   1. git add -A
    echo   2. git commit -m "Final optimization and logic check complete"
    echo   3. git push origin main
    echo.
) else (
    echo.
    echo ======================================================================
    echo [ERROR] 오류가 발견되었습니다!
    echo ======================================================================
    echo.
    echo FINAL_LOGIC_CHECK_REPORT.md 파일을 확인하여 오류를 수정하세요.
    echo.
)

pause
