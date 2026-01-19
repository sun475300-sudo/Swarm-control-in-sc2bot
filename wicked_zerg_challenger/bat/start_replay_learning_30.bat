@echo off
chcp 65001 > nul
REM Replay Learning - Extract from 30 replays

echo ======================================================================
echo Replay Learning - 30 Replays
echo ======================================================================
echo.

cd /d "%~dp0\.."
set PYTHONPATH=%CD%

python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

echo [INFO] Starting replay learning from 30 replays...
echo [INFO] Replay directory: D:\replays\replays
echo.

set MAX_REPLAYS_FOR_LEARNING=30
python local_training\scripts\replay_build_order_learner.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Replay learning failed
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo Replay Learning Complete
echo ======================================================================
echo [INFO] Learned parameters saved to: local_training\scripts\learned_build_orders.json
echo.
pause
