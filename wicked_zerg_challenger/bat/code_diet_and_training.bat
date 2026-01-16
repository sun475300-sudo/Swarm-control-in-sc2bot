@echo off
chcp 65001 > nul
REM 코드 다이어트 및 게임 학습 시작 배치 스크립트

echo ======================================================================
echo CODE DIET AND GAME TRAINING
echo ======================================================================
echo.
echo This will:
echo   1. Run code diet (remove unnecessary code)
echo   2. Start game training
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

REM Step 1: Run code diet
echo ======================================================================
echo [STEP 1] CODE DIET - 코드 다이어트 시작
echo ======================================================================
echo.

if exist "tools\run_code_diet.py" (
    python tools\run_code_diet.py
    
    if %ERRORLEVEL% NEQ 0 (
        echo [WARNING] Code diet had some issues, but continuing...
    )
) else (
    echo [WARNING] tools\run_code_diet.py not found, skipping code diet
)

echo.
echo ======================================================================
echo [STEP 2] GAME TRAINING - 게임 학습 시작
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

REM Check if SC2PATH is set
if "%SC2PATH%"=="" (
    echo [WARNING] SC2PATH not set. Will attempt to auto-detect...
) else (
    echo [INFO] SC2PATH: %SC2PATH%
)

echo.
echo [INFO] Starting game training...
echo.

REM Start training
if exist "run_with_training.py" (
    python run_with_training.py
) else (
    echo [ERROR] run_with_training.py not found
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo Training Session Ended
echo ======================================================================
echo.

pause
