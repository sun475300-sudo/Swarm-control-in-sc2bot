@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo ======================================================================
echo COMPREHENSIVE TRAINING WORKFLOW - 5 ITERATIONS (VERSION 2)
echo ======================================================================
echo.
echo This workflow will execute:
echo   1. Auto error fixing (tools/auto_error_fixer.py)
echo   2. Code quality check (tools/code_quality_improver.py)
echo   3. Game training (run_with_training.py)
echo   4. Replay build order learning (replay_build_order_learner.py)
echo   5. Replay comparison analysis (strategy_audit.py)
echo   6. Repeat 5 times
echo.
echo ======================================================================
echo.
python tools\comprehensive_training_workflow_5x_v2.py
pause
