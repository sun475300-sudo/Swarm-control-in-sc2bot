@echo off
chcp 65001 > nul
REM 완전한 훈련 워크플로우 배치 스크립트

echo ======================================================================
echo Complete Training Workflow - 완전한 훈련 워크플로우
echo ======================================================================
echo.
echo This workflow will execute:
echo   1. Start game training (python run_with_training.py)
echo   2. Post-training logic check and error fixing
echo   3. Full file logic check
echo   4. Replay comparison learning and data application
echo   5. Replay learning data comparison analysis and learning
echo   6. Cleanup and data organization
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
echo [INFO] Starting complete training workflow...
echo.
echo [NOTE] You can interrupt training with Ctrl+C to proceed to next steps
echo.

REM Run complete workflow
if exist "tools\complete_training_workflow.py" (
    python tools\complete_training_workflow.py
    
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Workflow failed
        pause
        exit /b 1
    )
) else (
    echo [ERROR] complete_training_workflow.py not found
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo WORKFLOW COMPLETE
echo ======================================================================
echo.

pause
