@echo off
chcp 65001 > nul
REM 학습 데이터 최적화 배치 스크립트

echo ======================================================================
echo Learning Data Optimization
echo ======================================================================
echo.
echo This will:
echo   1. Load all learning data sources
echo   2. Extract timing data
echo   3. Remove outliers
echo   4. Calculate optimal parameters
echo   5. Save optimized data
echo   6. Update config
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
echo [INFO] Starting learning data optimization...
echo.

if exist "tools\optimize_learning_data.py" (
    python tools\optimize_learning_data.py

    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Optimization failed
        pause
        exit /b 1
    )
) else (
    echo [ERROR] tools\optimize_learning_data.py not found
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo Optimization Complete
echo ======================================================================
echo [INFO] Optimized parameters saved to local_training/scripts/learned_build_orders.json
echo [INFO] Statistics saved to local_training/optimization_stats/
echo.

pause
