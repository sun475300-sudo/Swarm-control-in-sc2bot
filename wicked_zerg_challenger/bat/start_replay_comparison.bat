@echo off
chcp 65001 > nul
REM 리플레이 데이터 비교분석 시작 배치 스크립트

echo ======================================================================
echo Replay Data Comparison Analysis - 리플레이 데이터 비교분석 시작
echo ======================================================================
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
echo [INFO] Starting replay comparison analysis...
echo.
echo [NOTE] This will compare:
echo    - Pro gamer replays (D:\replays\replays)
echo    - Training replays (local training data)
echo    - Generate detailed comparison reports
echo.

REM Check if comparison script exists
if exist "tools\compare_pro_vs_training_replays.py" (
    python tools\compare_pro_vs_training_replays.py
    
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Comparison analysis failed
        pause
        exit /b 1
    )
) else (
    echo [ERROR] tools\compare_pro_vs_training_replays.py not found
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo Replay Comparison Analysis Complete
echo ======================================================================
echo [INFO] Comparison reports saved to local_training/comparison_reports/
echo [INFO] Comparison data saved to local_training/scripts/build_order_comparison_history.json
echo.

pause
