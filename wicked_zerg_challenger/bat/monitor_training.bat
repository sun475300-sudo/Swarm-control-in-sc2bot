@echo off
chcp 65001 >nul
cd /d "%~dp0\.."
python tools\monitor_training_progress.py
pause
