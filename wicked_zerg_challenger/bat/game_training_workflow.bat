@echo off
chcp 65001 > nul
REM 게임 학습 워크플로우 - 정밀검사 후 게임 학습 시작 및 완료 후 로직 검사

echo ======================================================================
echo Game Training Workflow - 게임 학습 워크플로우
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
echo [INFO] Starting game training workflow...
echo.
echo This workflow will:
echo   1. Run precision code style check
echo   2. Start game training
echo   3. Run post-training logic check and error fixing
echo   4. Run full file logic check
echo.

REM Run the workflow
if exist "tools\game_training_workflow.py" (
    python tools\game_training_workflow.py
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo [ERROR] Workflow completed with errors
        pause
        exit /b 1
    )
) else (
    echo [ERROR] tools\game_training_workflow.py not found
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo Workflow Completed Successfully
echo ======================================================================
echo.

pause
