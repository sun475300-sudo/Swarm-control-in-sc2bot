@echo off
chcp 65001 > nul
REM 리플레이 학습 데이터 비교 분석 및 학습 실행 배치 스크립트

echo ======================================================================
echo Replay Learning Data Comparison and Learning
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
echo [INFO] Starting comparison and learning...
echo.

echo [STEP 1] Running comparison analysis...
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
echo [STEP 2] Starting replay learning with updated parameters...
if exist "local_training\scripts\replay_build_order_learner.py" (
    python local_training\scripts\replay_build_order_learner.py

    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Replay learning failed
        pause
        exit /b 1
    )
) else (
    echo [ERROR] local_training\scripts\replay_build_order_learner.py not found
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo Comparison and Learning Complete
echo ======================================================================
echo [INFO] Comparison reports saved to local_training/comparison_reports/
echo [INFO] Comparison data saved to local_training/scripts/build_order_comparison_history.json
echo [INFO] Learned parameters saved to local_training/scripts/learned_build_orders.json
echo [INFO] Ready for next training session with optimized parameters
echo.

pause
