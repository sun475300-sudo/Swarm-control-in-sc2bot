@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo ======================================================================
echo ? COMPREHENSIVE TRAINING WORKFLOW - 5 ITERATIONS
echo ======================================================================
echo.
echo This workflow will execute:
echo   1. Precision check (completed)
echo   2. Start game training
echo   3. Logic check and error fixing after training
echo   4. Full file logic check
echo   5. Start training (python run_with_training.py)
echo   6. Run replay comparison learning and apply data
echo   7. Run replay learning data comparison analysis and learning
echo   8. Repeat 5 times
echo.
echo ======================================================================
echo.
python tools\comprehensive_training_workflow_5x.py
pause
