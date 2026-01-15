@echo off
chcp 65001 > nul
REM 훈련 최적화 배치 파일

cd /d "%~dp0\.."
if not exist "tools" (
    echo [ERROR] tools directory not found. Current directory: %CD%
    exit /b 1
)
set PYTHONPATH=%CD%

echo ======================================================================
echo 훈련 최적화 도구
echo ======================================================================
echo.

REM 리포트만 생성
python tools\optimize_for_training.py --report-only

echo.
echo ======================================================================
echo 리포트 생성 완료!
echo ======================================================================
echo.
echo 실제 최적화를 실행하려면:
echo   python tools\optimize_for_training.py --execute
echo.

pause
