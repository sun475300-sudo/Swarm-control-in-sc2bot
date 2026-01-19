@echo off
chcp 65001 > nul
REM Complete Training Workflow - Automated
REM 1. Code optimization
REM 2. Start game training
REM 3. Wait for completion
REM 4. Replay comparison learning
REM 5. Replay learning data analysis
REM 6. Fix errors
REM 7. Cleanup and shutdown

echo ======================================================================
echo Complete_Training Workflow - Automated
echo ======================================================================
echo.

REM Change to project directory
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
echo [INFO] Starting complete training workflow...
echo.
echo This workflow will:
echo   1. Optimize and unify code style
echo   2. Start game training (background)
echo   3. Wait for training completion
echo   4. Run replay comparison learning
echo   5. Run replay learning data analysis
echo   6. Fix errors
echo   7. Cleanup and shutdown
echo   8. Shutdown computer
echo.

REM Run the workflow
if exist "tools\complete_training_workflow_auto.py" (
    python tools\complete_training_workflow_auto.py
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo [ERROR] Workflow completed with errors
        pause
        exit /b 1
    )
) else (
    echo [ERROR] tools\complete_training_workflow_auto.py not found
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo Workflow Completed
echo ======================================================================
echo.

pause
