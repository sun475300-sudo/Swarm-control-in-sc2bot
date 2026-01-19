@echo off
chcp 65001 >nul
cd /d "%~dp0\.."
python tools\show_learning_rate.py
pause
