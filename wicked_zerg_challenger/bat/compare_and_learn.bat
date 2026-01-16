@echo off
chcp 65001 > nul
REM 리플레이 학습 데이터 비교 분석 및 학습 실행 배치 스크립트

echo ======================================================================
echo Replay Learning Data Comparison and Learning
echo ======================================================================
echo.

REM CRITICAL: Change to project directory
cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo [INFO] Current directory: %CD%
echo [INFO] Starting comparison and learning...
echo.

echo [STEP 1] Running comparison analysis...
python tools\compare_pro_vs_training_replays.py

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Comparison analysis failed
    pause
    exit /b 1
)

echo.
echo [STEP 2] Starting replay learning with updated parameters...
python local_training\scripts\replay_build_order_learner.py

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Replay learning failed
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo Comparison and Learning Complete
echo ======================================================================
echo [INFO] Comparison reports saved to local_training/comparison_reports/
echo [INFO] Learned parameters saved to local_training/scripts/learned_build_orders.json
echo.

pause
