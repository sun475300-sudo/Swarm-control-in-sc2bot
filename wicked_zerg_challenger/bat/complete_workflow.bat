@echo off
chcp 65001 > nul
REM Complete Workflow: Code Style, Replay Learning, Game Training, Comparison, and Logic Check

echo ======================================================================
echo COMPLETE WORKFLOW
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
echo.

echo [INFO] This workflow will execute:
echo   1. Code style unification
echo   2. Replay learning and logic check
echo   3. Replay comparison learning
echo   4. Apply differences and learn
echo   5. Full logic check
echo.
echo [INFO] Game training will be started separately after this workflow
echo.

if exist "tools\complete_workflow.py" (
    python tools\complete_workflow.py
    
    if %ERRORLEVEL% NEQ 0 (
        echo [WARNING] Some steps failed, but workflow completed
    )
) else (
    echo [ERROR] tools\complete_workflow.py not found
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo WORKFLOW COMPLETE
echo ======================================================================
echo.
echo [INFO] Next step: Start game training
echo [INFO] Run: bat\start_local_training.bat
echo.
pause
