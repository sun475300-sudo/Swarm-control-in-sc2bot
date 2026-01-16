@echo off
chcp 65001 > nul
REM 프로게이머 리플레이 학습 30회 및 학습 리플레이 데이터 비교 분석 및 학습 30회 실행

echo ======================================================================
echo 30 ITERATIONS OF LEARNING
echo ======================================================================
echo.
echo This will execute:
echo   1. Pro gamer replay learning: 30 iterations
echo   2. Comparison analysis and learning: 30 iterations
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
echo [INFO] Starting 30 iterations of learning...
echo.

if exist "tools\run_30_iterations_learning.py" (
    python tools\run_30_iterations_learning.py
    
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Process failed
        pause
        exit /b 1
    )
) else (
    echo [ERROR] tools\run_30_iterations_learning.py not found
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo 30 ITERATIONS COMPLETE
echo ======================================================================
echo.

pause
