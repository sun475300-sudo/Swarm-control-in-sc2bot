@echo off
chcp 65001 > nul
REM 리플레이 학습 시작 배치 스크립트

echo ======================================================================
echo Replay Learning - 리플레이 학습 시작
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
echo [INFO] Starting replay learning...
echo.
echo [NOTE] This will process replays from D:\replays\replays
echo [NOTE] Each replay will be analyzed 5 times for comprehensive learning
echo [NOTE] Progress will be shown in real-time
echo [NOTE] Learned parameters will be saved to local_training/scripts/learned_build_orders.json
echo.

REM Check if replay learning script exists
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
echo Replay Learning Complete
echo ======================================================================
echo [INFO] Learned parameters saved to local_training/scripts/learned_build_orders.json
echo [INFO] Build orders saved to D:\replays\archive\training_YYYYMMDD_HHMMSS\
echo.

pause
