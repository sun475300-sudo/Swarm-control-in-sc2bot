@echo off
chcp 65001 > nul
REM Integrated Replay Learning Workflow
REM 프로게이머 리플레이 학습 → 빌드오더 학습 → 게임 훈련 적용

echo ======================================================================
echo Integrated Replay Learning Workflow
echo 프로게이머 리플레이 학습 ^> 빌드오더 학습 ^> 게임 훈련 적용
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

if "%1"=="" (
    set MAX_REPLAYS=30
) else (
    set MAX_REPLAYS=%1
)

echo [INFO] Starting integrated replay learning workflow...
echo [INFO] Max replays: %MAX_REPLAYS%
echo [INFO] Replay directory: D:\replays\replays
echo.

python tools\integrated_replay_learning_workflow.py --max-replays %MAX_REPLAYS%

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Workflow failed
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo Workflow Complete
echo ======================================================================
echo [INFO] Learned parameters saved to: local_training\scripts\learned_build_orders.json
echo [INFO] These parameters are automatically used in production_resilience.py
echo [INFO] Start game training to apply the learned build orders:
echo        python run_with_training.py
echo.
pause
