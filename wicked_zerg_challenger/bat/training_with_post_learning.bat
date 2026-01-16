@echo off
chcp 65001 > nul
REM 게임 훈련 실행 및 훈련 후 자동 리플레이 비교 및 학습 통합 스크립트

echo ======================================================================
echo Training with Post Learning Workflow
echo ======================================================================
echo.
echo This workflow will:
echo   1. Start game training with optimized parameters
echo   2. After training: Run comparison analysis
echo   3. Learn from pro gamer replays
echo   4. Apply learned parameters for next training
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

REM Step 1: Start game training
echo ======================================================================
echo [STEP 1] Starting game training with optimized parameters...
echo ======================================================================
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

REM Verify optimized parameters
if exist "local_training\scripts\learned_build_orders.json" (
    echo [INFO] Optimized parameters ready:
    python -c "import json; from pathlib import Path; learned = json.load(open('local_training/scripts/learned_build_orders.json', 'r', encoding='utf-8')); [print(f'  {k}: {v}') for k, v in sorted(learned.items())]"
    echo.
)

echo [INFO] Starting training session...
echo [INFO] Training will run until manually stopped or MAX_GAMES reached
echo.

REM Start training
if exist "run_with_training.py" (
    python run_with_training.py
    set TRAINING_EXIT_CODE=%ERRORLEVEL%
) else (
    echo [ERROR] run_with_training.py not found
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo Training Session Ended (Exit Code: %TRAINING_EXIT_CODE%)
echo ======================================================================
echo.

REM Step 2: Post training learning workflow
echo ======================================================================
echo [STEP 2] Starting post training learning workflow...
echo ======================================================================
echo.

if exist "tools\post_training_learning_workflow.py" (
    python tools\post_training_learning_workflow.py
    
    if %ERRORLEVEL% NEQ 0 (
        echo [WARNING] Post training learning workflow had errors
    ) else (
        echo [SUCCESS] Post training learning workflow complete
    )
) else (
    echo [WARNING] post_training_learning_workflow.py not found, skipping...
)

echo.
echo ======================================================================
echo Complete Workflow Finished
echo ======================================================================
echo.
echo [INFO] Training session completed
echo [INFO] Post training learning completed
echo [INFO] Learned parameters updated and ready for next training session
echo.

pause
