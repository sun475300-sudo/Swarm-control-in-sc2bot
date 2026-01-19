@echo off
REM Quick script to run complete training workflow from any directory
cd /d "%~dp0.."
python wicked_zerg_challenger\tools\complete_training_workflow_auto.py
pause
