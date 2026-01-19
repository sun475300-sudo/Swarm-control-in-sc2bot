@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo ======================================================================
echo ? REPLAY LEARNING DATA COMPARISON ^& LEARNING - 5 ITERATIONS
echo ======================================================================
echo.
echo This workflow will execute:
echo   1. Replay build order learning
echo   2. Replay comparison analysis (pro vs bot)
echo   3. Apply learned data
echo   4. Repeat 5 times
echo.
echo ======================================================================
echo.
python tools\replay_learning_comparison_5x.py
pause
