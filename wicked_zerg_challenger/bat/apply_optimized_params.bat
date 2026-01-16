@echo off
chcp 65001 > nul
REM 최적화된 학습 데이터를 다음 게임 훈련에 적용하는 배치 스크립트

echo ======================================================================
echo Apply Optimized Parameters to Training
echo ======================================================================
echo.
echo This will:
echo   1. Load optimized parameters from learned_build_orders.json
echo   2. Verify config integration
echo   3. Apply to training system
echo   4. Prepare for next game training
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
echo [INFO] Applying optimized parameters to training...
echo.

if exist "tools\apply_optimized_params_to_training.py" (
    python tools\apply_optimized_params_to_training.py

    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to apply optimized parameters
        pause
        exit /b 1
    )
) else (
    echo [ERROR] tools\apply_optimized_params_to_training.py not found
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo Application Complete
echo ======================================================================
echo [INFO] Optimized parameters are ready for next game training
echo [INFO] Start training with: bat\start_local_training.bat
echo.

pause
