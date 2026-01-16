@echo off
chcp 65001 > nul
REM 학습 진행 모니터링 및 학습 완료 후 자동 비교 분석 및 재학습 배치 스크립트

echo ======================================================================
echo TRAINING WITH MONITORING AND AUTO LEARNING
echo ======================================================================
echo.
echo This workflow will:
echo   1. Start game training with monitoring
echo   2. Open monitoring dashboard for real-time statistics
echo   3. After training: Run comparison analysis
echo   4. Learn from pro gamer replays
echo   5. Apply learned parameters
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
echo.

REM Set environment variables for training
set INSTANCE_ID=0
set NUM_INSTANCES=1
set SINGLE_GAME_MODE=true
set SHOW_WINDOW=true
set HEADLESS_MODE=false
set DISABLE_DASHBOARD=false
set TORCH_NUM_THREADS=12

if "%MAX_GAMES%"=="" set MAX_GAMES=0

echo [INFO] Environment variables set:
echo    - INSTANCE_ID=%INSTANCE_ID%
echo    - NUM_INSTANCES=%NUM_INSTANCES%
echo    - SINGLE_GAME_MODE=%SINGLE_GAME_MODE%
echo    - SHOW_WINDOW=%SHOW_WINDOW%
echo    - MAX_GAMES=%MAX_GAMES%
echo.

REM Check if SC2PATH is set
if "%SC2PATH%"=="" (
    echo [WARNING] SC2PATH not set. Will attempt to auto-detect...
) else (
    echo [INFO] SC2PATH: %SC2PATH%
)

echo.
echo ======================================================================
echo [STEP 1] STARTING TRAINING WITH MONITORING
echo ======================================================================
echo.
echo [INFO] Training will start now...
echo [INFO] Monitor progress:
echo    - Game window: Real-time game visualization
echo    - Dashboard: http://localhost:8000
echo.
echo [INFO] Press Ctrl+C to stop training and proceed to post-learning
echo.

if exist "tools\training_with_monitoring_and_auto_learning.py" (
    python tools\training_with_monitoring_and_auto_learning.py
    
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Process failed
        pause
        exit /b 1
    )
) else (
    echo [ERROR] tools\training_with_monitoring_and_auto_learning.py not found
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo WORKFLOW COMPLETE
echo ======================================================================
echo.

pause
