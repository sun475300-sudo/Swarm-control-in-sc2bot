@echo off
chcp 65001 > nul
REM 게임 훈련 끝난 후 리플레이 비교 및 프로게이머 리플레이 다시 학습 배치 스크립트

echo ======================================================================
echo Post Training Learning Workflow
echo ======================================================================
echo.
echo This workflow will run after game training:
echo   1. Run comparison analysis (training vs pro replays)
echo   2. Learn from pro gamer replays
echo   3. Apply learned parameters to training
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
echo [INFO] Starting post training learning workflow...
echo.

if exist "tools\post_training_learning_workflow.py" (
    python tools\post_training_learning_workflow.py

    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Post training learning workflow failed
        pause
        exit /b 1
    )
) else (
    echo [ERROR] tools\post_training_learning_workflow.py not found
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo Post Training Learning Workflow Complete
echo ======================================================================
echo.
echo [INFO] Learned parameters saved to local_training/scripts/learned_build_orders.json
echo [INFO] Ready for next training session
echo.

pause
