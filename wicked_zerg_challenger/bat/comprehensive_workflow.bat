@echo off
chcp 65001 > nul
REM Comprehensive Workflow: Code Style, Replay Learning, Game Training, and Logic Check

echo ======================================================================
echo COMPREHENSIVE WORKFLOW
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

if exist "tools\comprehensive_workflow.py" (
    python tools\comprehensive_workflow.py
    
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Workflow failed
        pause
        exit /b 1
    )
) else (
    echo [ERROR] tools\comprehensive_workflow.py not found
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo WORKFLOW COMPLETE
echo ======================================================================
echo.
pause
