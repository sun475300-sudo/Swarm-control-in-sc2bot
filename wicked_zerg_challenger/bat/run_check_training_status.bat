@echo off
REM Quick script to check training status from any directory
cd /d "%~dp0.."
python wicked_zerg_challenger\tools\check_training_status.py
pause
