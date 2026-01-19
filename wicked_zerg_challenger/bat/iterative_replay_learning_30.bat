@echo off
chcp 65001 > nul
REM Iterative Replay Learning Workflow - 30 Iterations
REM 프로게이머 리플레이 학습 → 빌드오더 학습 → 게임 훈련 적용 → 개선 (30회 반복)

echo ======================================================================
echo Iterative Replay Learning Workflow
echo 프로게이머 리플레이 학습 ^> 빌드오더 학습 ^> 게임 훈련 적용 ^> 개선 (30회 반복)
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
    set MAX_ITERATIONS=30
) else (
    set MAX_ITERATIONS=%1
)

if "%2"=="" (
    set MAX_REPLAYS=30
) else (
    set MAX_REPLAYS=%2
)

echo [INFO] Starting iterative replay learning workflow...
echo [INFO] Max iterations: %MAX_ITERATIONS%
echo [INFO] Max replays per iteration: %MAX_REPLAYS%
echo [INFO] Replay directory: D:\replays\replays
echo [INFO] This will take a while - please be patient...
echo.

python tools\iterative_replay_learning_workflow.py --max-iterations %MAX_ITERATIONS% --max-replays %MAX_REPLAYS%

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Workflow failed
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo Iterative Learning Complete
echo ======================================================================
echo [INFO] Completed %MAX_ITERATIONS% iterations
echo [INFO] Learned parameters saved to: local_training\scripts\learned_build_orders.json
echo [INFO] Iteration history saved to: local_training\scripts\iterative_learning_history.json
echo [INFO] These parameters are automatically used in production_resilience.py
echo [INFO] Start game training to apply the learned build orders:
echo        python run_with_training.py
echo.
pause
