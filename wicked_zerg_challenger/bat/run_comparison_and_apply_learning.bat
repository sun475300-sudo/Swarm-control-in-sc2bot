@echo off
chcp 65001 > nul
REM 비교 분석 실행 및 차이점을 반영한 학습 실행 배치 스크립트

echo ======================================================================
echo Comparison Analysis and Learning
echo ======================================================================
echo.
echo This workflow will:
echo   1. Run comparison analysis (training vs pro replays)
echo   2. Apply differences to learned parameters
echo   3. Learn from pro gamer replays
echo   4. Save learned parameters
echo.

REM CRITICAL: Change to project directory
cd /d "%~dp0\.."
if not exist "tools" (
    echo [ERROR] tools directory not found. Current directory: %CD%
    exit /b 1
)
set PYTHONPATH=%CD%

REM Verify Python is available
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found in PATH
    exit /b 1
)

echo [INFO] Current directory: %CD%
echo [INFO] Starting comparison analysis and learning...
echo.

if exist "tools\run_comparison_and_apply_learning.py" (
    python tools\run_comparison_and_apply_learning.py
    
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Process failed
        pause
        exit /b 1
    )
) else (
    echo [ERROR] tools\run_comparison_and_apply_learning.py not found
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo Comparison and Learning Complete
echo ======================================================================
echo.
echo [INFO] Learned parameters saved to local_training/scripts/learned_build_orders.json
echo [INFO] Ready for next training session
echo.

pause
