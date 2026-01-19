@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo ======================================================================
echo ? REPLAY LEARNING DATA COMPARISON ANALYSIS & LEARNING - 5 ITERATIONS
echo ======================================================================
echo.
echo This workflow will execute:
echo   1. Replay comparison analysis (strategy_audit.py)
echo   2. Replay build order learning (replay_build_order_learner.py)
echo   3. Repeat 5 times
echo.
echo ======================================================================
echo.
python tools\replay_learning_analysis_5x.py
pause
