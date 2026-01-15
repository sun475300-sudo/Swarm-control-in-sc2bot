@echo off
chcp 65001 > nul
REM 마크다운 경고 자동 수정 배치 파일

REM CRITICAL: Change to wicked_zerg_challenger directory
cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo 마크다운 경고 자동 수정
echo ======================================================================
echo.

python tools\fix_markdown_warnings.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] 마크다운 경고 수정 완료!
) else (
    echo.
    echo [ERROR] 수정 중 오류가 발생했습니다!
)

echo.
pause
