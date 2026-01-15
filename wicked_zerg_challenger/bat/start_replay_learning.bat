@echo off
chcp 65001 > nul
REM 由ы뵆?덉씠 ?숈뒿 ?쒖옉 ?ㅽ겕由쏀듃
REM Replay Build Order Learning System

REM CRITICAL: Ensure script runs from project root regardless of current directory
cd /d "%~dp0.."

echo.
echo ================================
echo REPLAY BUILD ORDER LEARNING
echo ================================
echo.

cd /d "%~dp0..\local_training\scripts"

echo [STEP 1] Checking replay directory...
if not exist "D:\replays\replays" (
    echo [WARNING] Replay directory not found: D:\replays\replays
    echo [INFO] Creating directory...
    mkdir "D:\replays\replays" 2>nul
)

echo [STEP 2] Starting replay build order learning...
set AUTO_COMMIT_AFTER_TRAINING=true
python replay_build_order_learner.py

echo.
echo [STEP 3] Auto committing changes to GitHub...
cd /d "%~dp0.."
python tools\auto_commit_after_training.py

echo.
echo ================================
echo REPLAY LEARNING COMPLETE
echo ================================
echo.

pause
