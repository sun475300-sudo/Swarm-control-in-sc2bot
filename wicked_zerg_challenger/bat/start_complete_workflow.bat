@echo off
chcp 65001 > nul
REM Complete Training Workflow - Start
REM 1. Code optimization
REM 2. Start game training
REM 3. Wait for completion
REM 4. Replay comparison learning
REM 5. Replay learning data analysis
REM 6. Fix errors

echo ======================================================================
echo Complete Training Workflow
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

echo [INFO] Starting complete training workflow...
echo [INFO] This will:
echo   1. Optimize and unify code style
echo   2. Start game training (background)
echo   3. Wait for training completion
echo   4. Run replay comparison learning
echo   5. Run replay learning data analysis
echo   6. Fix errors
echo.

python tools\complete_training_workflow_auto.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Workflow failed
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo Workflow Completed Successfully
echo ======================================================================
pause
