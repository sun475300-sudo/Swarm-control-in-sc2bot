@echo off
chcp 65001 > nul
REM 게임 학습 워크플로우 - 개선된 버전
REM Improved Game Training Workflow - 통합 확인, 모니터링 서버, 리플레이 학습 지원

echo ======================================================================
echo Game Training Workflow - 게임 학습 워크플로우 (개선 버전)
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
echo [INFO] Starting improved game training workflow...
echo.
echo This workflow will:
echo   0. Check hierarchical RL and reward system integration status
echo   0.5. (Optional) Start monitoring server (set START_MONITOR=true)
echo   1. Run precision code style check
echo   2. Start game training
echo   3. Run post-training logic check and error fixing
echo   4. Run full file logic check
echo   5. (Optional) Run replay learning (set RUN_REPLAY_LEARNING=true)
echo.
echo [INFO] Optional features can be enabled by setting environment variables:
echo   - START_MONITOR=true : Start monitoring server
echo   - RUN_REPLAY_LEARNING=true : Run replay learning after training
echo.

REM Check for optional flags (can be set before running this script)
if "%START_MONITOR%"=="" set START_MONITOR=false
if "%RUN_REPLAY_LEARNING%"=="" set RUN_REPLAY_LEARNING=false

if "%START_MONITOR%"=="true" (
    echo [INFO] Monitoring server will be started
)
if "%RUN_REPLAY_LEARNING%"=="true" (
    echo [INFO] Replay learning will run after training
)

echo.

REM Run the workflow
if exist "tools\game_training_workflow.py" (
    set START_MONITOR=%START_MONITOR%
    set RUN_REPLAY_LEARNING=%RUN_REPLAY_LEARNING%
    python tools\game_training_workflow.py
    set EXIT_CODE=%ERRORLEVEL%
    if %EXIT_CODE% NEQ 0 (
        echo.
        echo [ERROR] Workflow completed with errors (Exit code: %EXIT_CODE%)
        pause
        exit /b %EXIT_CODE%
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
echo [INFO] Next steps:
echo   - Check 구현_상태_및_통합_가이드.md for hierarchical RL integration
echo   - Monitor training progress at http://localhost:8000/docs (if started)
echo   - Review replay learning results in local_training/extracted_data/
echo.

pause
