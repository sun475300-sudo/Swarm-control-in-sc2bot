@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo ======================================================================
echo ? GAME TRAINING - 5 GAMES
echo ======================================================================
python tools\run_training_5x.py
pause
