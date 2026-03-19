@echo off
REM JARVIS Clean Start — called by JARVIS_SILENT_LAUNCHER.vbs on Windows boot
timeout /t 15 /nobreak >nul
cd /d d:\Swarm-contol-in-sc2bot
if not exist logs mkdir logs
echo [%date% %time%] CLEAN_START executing... >> logs\jarvis_autostart.log
.venv\Scripts\python.exe start_jarvis_safe.py >> logs\jarvis_autostart.log 2>&1
echo [%date% %time%] CLEAN_START finished. >> logs\jarvis_autostart.log
